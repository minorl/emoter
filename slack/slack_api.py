"""Module for handling interaction with Slack"""
import asyncio
from collections import ChainMap, defaultdict, namedtuple
from functools import partial
from itertools import chain
import json
from pyparsing import ParseException
import requests
from slack.command import Command
from slack.parsing import SlackParser
import time
from util import handle_async_exception, make_request
import websockets

from .command import MessageCommand
from .history import HistoryDoc


Handler = namedtuple('Handler', ['name', 'func', 'doc', 'channels', 'admin'])

UnfilteredHandler = namedtuple('UnfilteredHandler', ['name', 'func', 'doc', 'channels'])

Handlers = namedtuple('Handlers', ['filtered', 'unfiltered'])


SlackConfig = namedtuple('SlackConfig',
    ['token', 'admin_token', 'alert', 'name', 'load_history', 'clear_commands', 'admins'])


def is_message(event, no_channel=False):
    """Check whether an event is a regular message."""
    return ('type' in event and event['type'] == 'message'
           and (no_channel or ('channel' in event and event['channel']))
           and 'text' in event
           and not ('reply_to' in event)
           and 'subtype' not in event
           and event['text'])  # Zero length messages are possible via /giphy command on slack


def is_group_join(event):
    """Check whether an event is the bot joining a group"""
    return 'type' in event and event['type'] == 'group_joined'


def is_team_join(event):
    """Check whether an event is a new user joining the team"""
    return 'type' in event and event['type'] == 'team_join'


class SlackIds:
    """Helper class for holding user, channel and room IDs."""
    def __init__(self, token, channels, users, groups):
        """
        Args:
            token: Slack token. Used to get DM room IDs
            channels: 'channels' from body of response to rtm.start API call
            users: 'users' from body of response to rtm.start API call
            groups: 'groups' from body of response to rtm.start API call
        """
        self._c_name_to_id = {c['name']: c['id'] for c in chain(channels, groups)}
        self._c_id_to_name = {c['id']: c['name'] for c in chain(channels, groups)}
        self._u_name_to_id = {u['name']: u['id'] for u in users}
        self._u_id_to_name = {u['id']: u['name'] for u in users}

        self._u_name_to_dm = {}
        self._dm_to_u_name = {}
        for u_name, u_id in self._u_name_to_id.items():
            response = requests.get(
                Slack.base_url + 'im.open',
                params={'token': token, 'user': u_id})
            body = response.json()
            if body['ok'] is False and body['error'] in {'cannot_dm_bot', 'user_disabled'}:
                pass
            elif body['ok']:
                cid = body['channel']['id']
                self._u_name_to_dm[u_name] = cid
                self._dm_to_u_name[cid] = u_name
            else:
                print(body)
                raise ValueError

    @property
    def channel_ids(self):
        """Use for iterating over all channels"""
        return self._c_id_to_name.keys()

    @property
    def dm_ids(self):
        """Use for iterating over all DM conversations"""
        return self._dm_to_u_name.keys()

    def add_channel(self, cname, cid):
        """Add a channel to ID registry"""
        self._c_name_to_id[cname] = cid
        self._c_id_to_name[cid] = cname

    def add_user(self, uname, uid):
        """Add a channel to ID registry"""
        self._u_name_to_id[uname] = uid
        self._u_id_to_name[uid] = uname

    def uid(self, uname):
        """Translate username to user ID"""
        return self._u_name_to_id[uname]

    def uname(self, uid):
        """Translate user ID to username"""
        return self._u_id_to_name[uid]

    def cid(self, cname):
        """Translate channel name to channel ID"""
        return self._c_name_to_id[cname]

    def cname(self, cid):
        """Translate channel ID to channel name"""
        return self._c_id_to_name[cid]

    def dmid(self, uname):
        """Translate user name to DM room ID"""
        return self._u_name_to_dm[uname]

    def dmname(self, uname):
        """Translate DM room ID to user name"""
        return self._dm_to_u_name[uname]


class Slack:
    """Main class which handles bots and communicates with Slack"""
    base_url = 'https://slack.com/api/'

    def __init__(self, config):
        self._config = config

        self._handlers = Handlers(filtered={}, unfiltered=[])
        self._parser = SlackParser(self._config.alert)
        self._loaded_commands = []
        self._message_id = 0

        self.ids = None
        self.socket = None

    def preload_commands(self, commands):
        """
        Use this to register commands which will run once Slack connects,
        before the connection exists.
        """
        self._loaded_commands.extend(commands)

    async def connect(self):
        """Connects to Slack, loads IDs, and returns the websocket URL."""
        response = requests.get(Slack.base_url + 'rtm.start', params={'token': self._config.token})
        body = response.json()
        self.ids = SlackIds(self._config.token, body['channels'], body['users'], body['groups'])
        if self._config.load_history:
            await self._load_history()
            self._config = SlackConfig(**ChainMap({'load_history': False}, self._config._asdict()))
        if self._config.clear_commands:
            loop = asyncio.get_event_loop()
            loop.create_task(handle_async_exception(self._clear_commands))
            self._config = SlackConfig(**ChainMap({'clear_commands': False}, self._config._asdict()))

        return body['url']

    async def run(self):
        """Main loop"""
        while True:
            websocket_url = await self.connect()
            try:
                async with websockets.connect(websocket_url) as self.socket:
                    print('Running {} preloaded commands'.format(len(self._loaded_commands)))

                    for command in self._loaded_commands:
                        await self._exhaust_command(command, None)
                    self._loaded_commands = []

                    while True:
                        command = None
                        event = await self.get_event()
                        if 'subtype' not in event or event['subtype'] != 'message_deleted':
                            print('Got event', event)
                        if is_message(event):
                            await self._handle_message(event)
                        elif is_group_join(event):
                            cname = event['channel']['name']
                            cid = event['channel']['id']
                            self.ids.add_channel(cname=cname, cid=cid)
                        elif is_team_join(event):
                            uname = event['user']['name']
                            uid = event['user']['id']
                            self.ids.add_user(uname=uname, uid=uid)
            except websockets.exceptions.ConnectionClosed:
                print('Websocket closed')

    async def _handle_message(self, event):
        user = event['user']
        user_name = self.ids.uname(user)
        channel = event['channel']
        is_dm = channel[0] == 'D'
        channel_name = None if is_dm else self.ids.cname(channel)

        if is_dm or event['text'][0] == self._config.alert:
            try:
                parsed = self._parser.parse(event['text'], dm=is_dm)
                name, = parsed.keys()
                handler = self._handlers.filtered[name]
            except ParseException:
                parsed = None
            # Only print help message for DMs
            if is_dm and not (parsed and name in self._handlers.filtered):
                command = (MessageCommand(channel=None,
                                          user=user_name,
                                          text=self._help_message(user_name))
                           if is_dm else None)
            elif (parsed and
                  (is_dm or handler.channels is None or channel_name in handler.channels)):
                if not handler.admin or user_name in self._config.admins:
                    command = await handler.func(user=user_name,
                                                 in_channel=channel_name,
                                                 parsed=parsed[name])
                else:
                    command = MessageCommand(channel=channel_name, user=user_name, text='That command is admin only.')
            else:
                command = None
            await self._exhaust_command(command, event)
        else:
            parsed = None

        if not is_dm and parsed is None:
            for handler in self._handlers.unfiltered:
                if (handler.channels is None
                        or channel_name in handler.channels
                        or is_dm):
                    command = await handler.func(
                        user=user_name,
                        in_channel=channel_name,
                        message=event['text'])
                    await self._exhaust_command(command, event)

            await self.store_message(
                user=user,
                channel=channel,
                text=event['text'],
                timestamp=event['ts'])

    async def _exhaust_command(self, command, event):
        """Run a command, any command that generates and so on until None is returned."""
        while command:
            if isinstance(command, Command):
                command = await command.execute(self, event)
            else:
                for com in command:
                    await self._exhaust_command(com, event)
                command = None

    async def react(self, emoji, event):
        """React to an event"""
        channel = event['channel']
        timestamp = event['ts']
        params = {
            'token': self._config.token,
            'name': emoji,
            'channel': channel,
            'timestamp': timestamp}
        await make_request(Slack.base_url + 'reactions.add', params)

    async def send(self, message, channel):
        """Send a message to a channel"""
        print('[{}] Sending message: {}'.format(channel, message))
        await self.socket.send(self._make_message(message, channel))

    async def get_event(self):
        """Get a JSON event from and convert it to a dict"""
        event = await self.socket.recv()
        return json.loads(event)

    async def _get_history(self, include_dms=False):
        found_messages = 0
        channels = chain(self.ids.channel_ids, self.ids.dm_ids if include_dms else [])
        events = defaultdict(list)
        for channel in channels:
            channel_name = (self.ids.cname if channel[0] in ('C', 'G') else
                            self.ids.dmname)(channel)
            print('Getting history for channel:', channel_name)
            url = Slack.base_url +\
                ('channels.history' if channel[0] == 'C' else 'groups.history' if channel[0] == 'G' else 'im.history')
            latest = float('inf')
            has_more = True
            params={'token': self._config.token,
                    'channel': channel,
                    'inclusive': False}
            while has_more:
                await asyncio.sleep(1)
                data = await make_request(
                    url,
                    params=params
                    )
                if 'has_more' not in data:
                    print(data)
                    print(channel)
                    print(self.ids.cname(channel))
                    exit()
                has_more = data['has_more']
                messages = data['messages']
                largest_timestamp = 0
                for message in messages:
                    if is_message(message, no_channel=True):
                        events[channel].append(message)
                    latest = min(float(message['ts']), latest)
                params['latest'] = latest
                found_messages += len(messages)
                print('Found {} messages'.format(found_messages))
        return events

    async def _load_history(self):
        """Wipe the existing history and load the Slack message archive into the database"""
        HistoryDoc.objects().delete()
        print('History Cleared')
        events = await self._get_history()
        for channel, messages in events.items():
            for message in messages:
                try:
                    await self.store_message(
                        channel=channel,
                        user=message['user'],
                        text=message['text'],
                        timestamp=message['ts'])
                except KeyError:
                    print([k for k in message])
                    exit()

    async def _clear_commands(self):
        to_delete = []
        bot_id = self.ids.uid(self._config.name)
        events = await self._get_history(include_dms=True)
        for channel, messages in events.items():
            for message in messages:
                admin_key = True
                if message['user'] == bot_id:
                    admin_key = False
                elif channel[0] != 'D':
                    try:
                        self._parser.parse(message['text'], dm=channel[0] == 'D')
                    except ParseException:
                        continue
                else:
                    continue
                to_delete.append(((channel, message['user'], message['ts']), admin_key))

        print('Found {} messages to delete'.format(len(to_delete)))
        for i, (args, admin_key) in enumerate(to_delete, 1):
            await asyncio.sleep(1)
            await self.delete_message(*args, admin_key=admin_key)
            if i % 100 == 0:
                print('Deleted {} messages so far'.format(i))

    async def store_message(self, user, channel, text, timestamp):
        """Store a message into the history DB"""
        u_name = self.ids.uname(user)
        c_name = self.ids.cname(channel)
        if u_name != self._config.name and text and text[0] != self._config.alert:
            HistoryDoc(user=u_name, channel=c_name, text=text, time=timestamp).save()

    async def upload_file(self, f_name, channel, user):
        """Upload a file to the specified channel or DM"""
        channel = channel if channel else self.ids.dmid(user)
        with open(f_name, 'rb') as f:
            requests.post(Slack.base_url + 'files.upload',
                          params={'token': self._config.token,
                                  'filetype': f_name.split('.')[-1],
                                  'channels': channel,
                                  'filename': self._config.name + ' upload'
                                  },
                          files={'file': f}
                          )

    async def delete_message(self, channel, user, timestamp, admin_key=True):
        """Delete a message"""
        channel = channel if channel else self.ids.dmid(user)
        token = self._config.admin_token if admin_key else self._config.token
        url = Slack.base_url + 'chat.delete'
        params = {'token': token,
                  'ts': str(timestamp),
                  'channel': channel,
                  'as_user': True}
        await make_request(url, params, request_type='POST')

    def register_handler(self, func, data):
        """
        Registers a function with Slack to be called when certain conditions are matched.
        Args:
            func: The function to call
            data: A HandlerData (namedtuple) containing:
                expr: A pyparsing expression.
                      func will be called when it is matched.
                      If expr is None, all messages will be passed to func.
                name: The name of this handler. This is used as the key to store the handler.
                doc: Help text
                priority: Handlers are checked in order of descending priority.
                admin: Whether or not this handler is only accessible to admins
        """
        name, expr, channels, doc, priority, admin = data
        if expr is None:
            uhandler = UnfilteredHandler(name=name,
                                         func=func,
                                         channels=channels,
                                         doc=doc)
            self._handlers.unfiltered.append(uhandler)
        else:
            self._parser.add_command(expr, name, priority)
            handler = Handler(name=name,
                              func=func,
                              channels=channels,
                              doc=doc,
                              admin=admin)
            self._handlers.filtered[name] = handler

    def _make_message(self, text, channel_id):
        """Build a JSON message"""
        m_id, self._message_id = self._message_id, self._message_id + 1
        return json.dumps({'id': m_id,
                           'type': 'message',
                           'channel': channel_id,
                           'text': text})

    def _help_message(self, user_name):
        """Iterate over all handlers and join their help texts into one message."""
        res = []
        for handler in self._handlers.filtered.values():
            if handler.doc and (not handler.admin or user_name in self._config.admins):
                res.append('{}:'.format(handler.name))
                res.append('\t{}'.format(handler.doc))
                res.append('\tAllowed channels: {}'.format(
                    'All' if handler.channels is None else handler.channels))

        return '\n'.join(res)
