from collections import defaultdict
import config
from emoter import Emoter
from parsing import ChannelParser, PMParser
from pyparsing import ParseException
from slack.command import MessageCommand
import time


class EmoteBot:
    def __init__(self, channels, name, delay=60):
        self.channels = channels

        self.emoter = Emoter()

        self.channel_parser = ChannelParser(name)
        self.pm_parser = PMParser(name)

        self.next_use = defaultdict(float)
        self.delay = delay

    async def channel_command(self, event):
        text = event['text']
        channel = event['channel']
        try:
            parsed = self.channel_parser.parse(text)
        except ParseException:
            return
        if 'command_emoji' in parsed:
            return MessageCommand(text=self.emotify(parsed), channel=channel)

    async def pm_command(self, event):
        print("Got PM")
        text = event['text']
        print(text)
        try:
            parsed = self.pm_parser.parse(text)
            if 'command_emoji' in parsed:
                if 'channel' in parsed and parsed['channel'] not in self.channels:
                    out_text = "Channel {} not recognized or not permitted.".format(channel)
                    channel = None
                elif 'channel' in parsed:
                    user = event['user']
                    curr_time = time.time()
                    diff = int(self.next_use[user] - curr_time)
                    if diff > 0:
                        out_text = "You can send another message in {} seconds.".format(diff)
                        channel = None
                    else:
                        self.next_use[user] = curr_time + self.delay
                        out_text =  self.emotify(parsed['command_emoji'])
                        channel = parsed['channel']
                        # If no channel is specified, send it back to the user
                else:
                    channel = None
                    out_text =  self.emotify(parsed['command_emoji'])
        except ParseException:
            out_text="Invalid command. Command should be: [channel] emoji message"
            channel = None

        if channel is None:
            return MessageCommand(text=out_text, channel=event['channel'])
        else:
            return MessageCommand(text=out_text, channel_name=channel)

    def emotify(self, parsed):
        emoji = parsed['emoji']
        message = parsed['message']
        return self.emoter.make_phrase(' '.join(message).upper(), emoji)
