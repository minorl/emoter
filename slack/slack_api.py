from .command import MessageCommand
from .command import ChannelParser, PMParser
from collections import defaultdict, namedtuple
from itertools import chain
import json
from pyparsing import ParseException
import requests
import websockets


'''
Asynchronous Slack class
'''

Handler = namedtuple('Handler', ['name', 'func', 'doc', 'all_channels', 'channels', 'accept_dm'])

class Slack:
    base_url = 'https://slack.com/api/'

    def __init__(self, token, name):
        self.token = token
        self.channels = None
        self.users = None
        self.message_id = 0
        self.handlers = {}
        self.parser = SlackParser(name)
        self.get_emojis()

    def get_emojis(self):
        res = requests.get(Slack.base_url + 'emoji.list', params={'token': self.token}).json()
        self.emojis = set(':{}:'.format(name) for name in res['emoji'])

    async def run(self):
        response = requests.get(Slack.base_url + 'rtm.start', params={'token': self.token})
        body = response.json()
        self.c_name_to_id = {c['name']: c['id'] for c in chain(body['channels'], body['groups'])}
        self.c_id_to_name = {v: k for k, v in self.c_name_to_id.items()}
        self.u_id_to_name = {u['id']: u['name'] for u in body['users']}
        self.u_name_to_id = {u['name']: u['id'] for u in body['users']}
        self.u_name_to_dm = {}

        # Get mapping from users -> DM room ID
        for u_name, u_id in self.u_name_to_id.items():
            response = requests.get(Slack.base_url + 'im.open', params={'token': self.token, 'user': u_id})
            body = response.json()
            assert body['okay'] is True
            self.u_name_to_dm[u_name] = body['channel']['id']

        url = body["url"]

        async with websockets.connect(url) as self.socket:
            while True:
                command = None
                event = await self.get_event()
                if 'type' in event and event['type'] == 'message'\
                   and 'channel' in event and event['channel']
                   and 'text' in event:
                    try:
                        user = event['user']
                        channel = event['channel']
                        is_dm = channel == 'D'
                        try:
                            parsed = self.parser.parse(event['text'], dm=is_dm)
                            name, = parsed.keys()
                            handler = self.handlers[name]
                        except ParseException:
                            parsed = None
                        if not (parsed and name in self.handlers):
                            command = MessageCommand(channel=None, 
                            continue
                        elif (handler.accept_dm or not is_dm) and
                             (handler.all_channels or channel in handler.channels):
                            command = await handler.func(user=user, channel=self.c_id_to_name[channel], parsed[name])
                    except KeyError as e:
                        print("!!!Key error!!!")
                        print(repr(e))
                        print("Event:")
                        print(event)
                        print()
                if command:
                    await self.execute(command)

        del self.socket
        del self.c_name_to_id
        del self.c_id_to_name
        del self.u_name_to_id
        del self.u_id_to_name
        del self.u_name_to_dm

    async def execute(self, command):
        if isinstance(command, MessageCommand):
            channel = command.channel if command.channel else self.u_name_to_dm[command.user]
            if len(command.text) < 4000:
                await self.send(command.text, channel)

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

    def register_handler(self, expr, name, func, all_channels=False, channels=set(), accept_dm=False, doc=None):
        expr = expr.setResultsName(name)
        self.parser.add_command(expr)
        handler = Handler(name=name,
                          func=func,
                          doc=doc,
                          all_channels=all_channels,
                          channels={self.c_name_to_id[n] for n in channels},
                          accept_dm=accept_dm,
                          doc=doc)
        self.handlers[name].append(handler)

    def make_message(self, text, channel_id):
        m_id, self.message_id = self.message_id, self.message_id + 1
        return json.dumps({"id": m_id,
                           "type": "message",
                           "channel": channel_id,
                           "text": text})
