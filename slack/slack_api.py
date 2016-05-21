from .command import MessageCommand
from .history import HistoryDoc
import asyncio
from collections import defaultdict, namedtuple
from functools import partial
from itertools import chain
import json
from pyparsing import ParseException
import requests
from slack.parsing import SlackParser
import websockets


'''
Asynchronous Slack class
'''

Handler = namedtuple('Handler', ['name', 'func', 'doc', 'all_channels', 'channels', 'accept_dm'])


class Slack:
    base_url = 'https://slack.com/api/'

    def __init__(self, token, alert='!', name='', load_history=False):
        self.token = token
        self.alert = alert
        self.name = name
        self.do_load_history = load_history

        self.channels = None
        self.users = None
        self.message_id = 0
        self.handlers = {}
        self.reactions = defaultdict(lambda: defaultdict(set))
        self.parser = SlackParser(self.alert)
        self.get_emojis()
        self.loaded_commands = []

    def get_emojis(self):
        res = requests.get(Slack.base_url + 'emoji.list', params={'token': self.token}).json()
        self.emojis = set(':{}:'.format(name) for name in res['emoji'])

    def get_dm_rooms(self):
        self.u_name_to_dm = {}
        for u_name, u_id in self.u_name_to_id.items():
            response = requests.get(Slack.base_url + 'im.open', params={'token': self.token, 'user': u_id})
            body = response.json()
            if body['ok'] is False and body['error'] in {'cannot_dm_bot', 'user_disabled'}:
                pass
            elif body['ok']:
                self.u_name_to_dm[u_name] = body['channel']['id']
            else:
                print(body)
                raise ValueError

    def preload_commands(self, commands):
        self.loaded_commands.extend(commands)

    async def run(self):
        response = requests.get(Slack.base_url + 'rtm.start', params={'token': self.token})
        body = response.json()
        self.c_name_to_id = {c['name']: c['id'] for c in chain(body['channels'], body['groups'])}
        self.c_id_to_name = {v: k for k, v in self.c_name_to_id.items()}
        self.u_id_to_name = {u['id']: u['name'] for u in body['users']}
        self.u_name_to_id = {u['name']: u['id'] for u in body['users']}
        self.get_dm_rooms()
        if self.do_load_history:
            await self.load_history()
            self.do_load_history = False

        url = body["url"]

        async with websockets.connect(url) as self.socket:
            print("Running {} preloaded commands".format(len(self.loaded_commands)))

            for c in self.loaded_commands:
                await c.execute(self)

            while True:
                command = None
                event = await self.get_event()
                print("Got event", event)
                if Slack.is_group_join(event):
                    name = event['channel']['name']
                    i = event['channel']['id']
                    self.c_name_to_id[name] = i
                    self.c_id_to_name[i] = name
                elif Slack.is_message(event):
                    user = event['user']
                    channel = event['channel']
                    is_dm = channel[0] == 'D'

                    if not is_dm:
                        await self.react(event)

                    if not (is_dm or event['text'][0] == self.alert):
                        await self.store_message(user=user, channel=channel, text=event['text'], ts=event['ts'])
                        continue
                    try:
                        parsed = self.parser.parse(event['text'], dm=is_dm)
                        name, = parsed.keys()
                        handler = self.handlers[name]
                    except ParseException:
                        parsed = None
                    if not (parsed and name in self.handlers):
                        command = MessageCommand(channel=None, user=self.u_id_to_name[user], text=self.help_message()) if is_dm else None
                    elif parsed and is_dm or (handler.channels is None or self.c_id_to_name[channel] in handler.channels):
                        command = await handler.func(user=self.u_id_to_name[user],
                                                     in_channel=None if is_dm else self.c_id_to_name[channel],
                                                     parsed=parsed[name])
                while command:
                    # Commands may return another command to be executed
                    command = await command.execute(self)

        del self.socket
        del self.c_name_to_id
        del self.c_id_to_name
        del self.u_name_to_id
        del self.u_id_to_name
        del self.u_name_to_dm

    async def react(self, event):
        loop = asyncio.get_event_loop()
        futures = []
        for u, reacts in self.reactions[event['channel']].items():
            for reg, emoji in reacts:
                if reg.search(event['text']):
                    channel = event['channel']
                    timestamp = event['ts']
                    params = {'token': self.token, 'name': emoji, 'channel': channel, 'timestamp': timestamp}
                    get = partial(requests.get, params=params)

                    futures.append(loop.run_in_executor(None, get, Slack.base_url + 'reactions.add'))

        for future in futures:
            res = (await future).json()
            if res['ok'] is not True:
                print("Bad return:", res)

    async def get_event(self):
        if self.socket is None:
            raise ValueError("Must be connected to listen")
        event = await self.socket.recv()
        return json.loads(event)

    async def send(self, message, channel):
        if self.socket is None:
            raise ValueError("Must be connected to send")
        print("[{}] Sending message: {}".format(channel, message))
        await self.socket.send(self.make_message(message, channel))

    async def load_history(self):
        HistoryDoc.objects().delete()
        print("History Cleared")
        found_messages = 0
        for channel in self.c_id_to_name:
            url = Slack.base_url + ('channels.history' if channel[0] == 'C' else 'groups.history')
            oldest = 0
            has_more = True
            while has_more:
                res = requests.get(url,
                                   params={'token': self.token,
                                           'channel': channel,
                                           'oldest': oldest,
                                           'inclusive': False})
                data = res.json()
                if not 'has_more' in data:
                    print(data)
                    print(channel)
                    print(self.c_id_to_name[channel])
                    exit()
                has_more = data['has_more']
                messages = data['messages']
                largest_ts = 0
                for m in messages:
                    if Slack.is_message(m, no_channel=True):
                        try:
                            await self.store_message(channel=channel, user=m['user'], text=m['text'], ts=m['ts'])
                        except KeyError:
                            print([k for k in m])
                            exit()
                    ts = float(m['ts'])
                    if ts > largest_ts:
                        largest_ts = ts

                oldest = largest_ts
                found_messages += len(messages)
                print("Have {} messages".format(found_messages))

    async def store_message(self, user, channel, text, ts):
        u_name = self.u_id_to_name[user]
        c_name = self.c_id_to_name[channel]
        if u_name != self.name and text and text[0] != self.alert:
            HistoryDoc(user=u_name, channel=c_name, text=text, time=ts).save()

    async def upload_file(self, f_name, channel, user):
        channel = channel if channel else self.u_name_to_dm[user]
        with open(f_name, 'rb') as f:
            requests.post(Slack.base_url + 'files.upload',
                          params={'token': self.token,
                                  'filetype': f_name.split('.')[-1],
                                  'channels': channel,
                                  'filename': f_name
                                  },
                          files={'file': f}
                          )

    def register_handler(self, expr, name, func, all_channels=False, channels=set(), accept_dm=False, doc=None, priority=0):
        self.parser.add_command(expr, name, priority)
        handler = Handler(name=name,
                          func=func,
                          all_channels=all_channels,
                          channels=channels,
                          accept_dm=accept_dm,
                          doc=doc)
        self.handlers[name] = handler

    def make_message(self, text, channel_id):
        m_id, self.message_id = self.message_id, self.message_id + 1
        return json.dumps({"id": m_id,
                           "type": "message",
                           "channel": channel_id,
                           "text": text})

    def help_message(self):
        res = []
        for handler in self.handlers.values():
            if handler.doc:
                res.append("{}:".format(handler.name))
                res.append("\t{}".format(handler.doc))
                res.append("\tAllowed channels: {}".format("All" if handler.all_channels else handler.channels))

        return '\n'.join(res)

    @staticmethod
    def is_message(event, no_channel=False):
        return 'type' in event and event['type'] == 'message'\
               and (no_channel or ('channel' in event and event['channel']))\
               and 'text' in event\
               and not ('reply_to' in event)\
               and not ('subtype' in event and (event['subtype'] == 'bot_message' or event['subtype'] == 'file_comment'))

    @staticmethod
    def is_group_join(event):
        return 'type' in event and event['type'] == 'group_joined'
