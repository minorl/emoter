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

    async def __aenter__(self):
        response = requests.get(Slack.base_url + 'rtm.start', params={'token': self.token})
        body = response.json()
        self.channels = {c['name']: c for c in chain(body['channels'], body['groups'])}
        url = body["url"]

        self.connect = websockets.connect(url)
        self.socket = await self.connect.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.connect.__aexit__(exc_type, exc, tb)
        self.socket = None

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

    def make_message(self, text, channel_id):
        m_id, self.message_id = self.message_id, self.message_id + 1
        return json.dumps({"id": m_id,
                           "type": "message",
                           "channel": channel_id,
                           "text": text})
