from .command import MessageCommand
from collections import defaultdict
from itertools import chain
import json
import requests
import websockets


'''
Asynchronous Slack class
'''


class Slack:
    base_url = 'https://slack.com/api/'

    def __init__(self, token):
        self.token = token
        self.channels = None
        self.groups = None
        self.message_id = 0
        self.dm_handlers = defaultdict(list)
        self.channel_handlers = defaultdict(lambda: defaultdict(list))

    async def run(self):
        response = requests.get(Slack.base_url + 'rtm.start', params={'token': self.token})
        body = response.json()
        self.c_name_to_id = {c['name']: c['id'] for c in chain(body['channels'], body['groups'])}
        self.c_id_to_name = {v: k for k, v in self.c_name_to_id.items()}
        url = body["url"]

        async with websockets.connect(url) as self.socket:
            while True:
                event = await self.get_event()
                if 'type' in event and 'channel' in event and event['channel']:
                    try:
                        if event['channel'][0] == 'D':
                            for h in self.dm_handlers[event['type']]:
                                command = await h(event)
                                if command:
                                    await self.execute(command)
                        else:
                            for h in self.channel_handlers[self.c_id_to_name[event['channel']]][event['type']]:
                                command = await h(event)
                                if command:
                                    await self.execute(command)

                    except KeyError as e:
                        print("!!!Key error!!!")
                        print(repr(e))
                        print("Event:")
                        print(event)

        del self.socket

    async def execute(self, command):
        if isinstance(command, MessageCommand):
            channel = command.channel if command.channel else self.c_name_to_id[command.channel_name]
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

    def register_handler(self, func, **kwargs):
        channels = kwargs.get('channels', None)
        types = kwargs.get('types', {'message'})
        if channels:
            for c in channels:
                for t in types:
                    self.channel_handlers[c][t].append(func)
        else:
            for t in types:
                self.dm_handlers[t].append(func)


    def make_message(self, text, channel_id):
        m_id, self.message_id = self.message_id, self.message_id + 1
        return json.dumps({"id": m_id,
                           "type": "message",
                           "channel": channel_id,
                           "text": text})
