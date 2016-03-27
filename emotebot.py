from commandparser import CommandParser
from emoter import Emoter
from pyparsing import ParseException
from slack import Slack


class EmoteBot:
    def __init__(self, token, channel):
        self.token = token
        self.emoter = Emoter()
        self.parser = CommandParser()
        self.slack = Slack(token)
        self.channel = channel

    async def main_loop(self):
        async with self.slack as slack:
            channel_id = self.slack.channels[self.channel]['id']
            while True:
                event = await slack.get_event()
                print(event)
                if 'text' in event and 'type' in event and event['type'] == 'message' and\
                    (event['channel'] == channel_id or event['channel'][0] == 'D'):

                    text = event['text']
                    try:
                        parsed = self.parser.parse(text)
                        emoji = parsed['emoji']
                        message = parsed['message']
                        emotified = self.emoter.make_phrase(' '.join(message).upper(), emoji)
                        await slack.send(emotified, event['channel'])
                    except ParseException:
                        pass
