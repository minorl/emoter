from commandparser import CommandParser
from emoter import Emoter
from pyparsing import ParseException
from slack import Slack


class EmoteBot:
    def __init__(self, token, name, channels):
        self.token = token
        self.emoter = Emoter()
        self.parser = CommandParser(name)
        self.slack = Slack(token)
        self.channels = channels

    async def main_loop(self):
        async with self.slack as slack:
            channel_ids = {self.slack.channels[channel]['id'] for channel in self.channels}
            while True:
                event = await slack.get_event()
                print(event)
                if 'text' in event and 'type' in event and event['type'] == 'message' and\
                    (event['channel'] in channel_ids or event['channel'][0] == 'D'):

                    text = event['text']
                    try:
                        parsed = self.parser.parse(text)
                        emoji = parsed['emoji']
                        message = parsed['message']
                        emotified = self.emoter.make_phrase(' '.join(message).upper(), emoji)
                        await slack.send(emotified, event['channel'])
                    except ParseException:
                        pass
