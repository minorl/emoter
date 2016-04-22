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
        text = event['text']
        try:
            parsed = self.pm_parser.parse(text)
        except ParseException:
            return MessageCommand(text="Invalid command. Command should be: <channel> <emoji> <message>", channel=event['channel'])
        if 'command_emoji' in parsed:
            user = event['user']
            curr_time = time.time()
            diff = int(self.next_use[user] - curr_time)
            if diff > 0:
                return MessageCommand(text="You can send another message in {} seconds.".format(diff), channel=event['channel'])
            self.next_use[user] = curr_time + self.delay
            channel = parsed['channel']
            if channel in self.channels:
                emotified = self.emotify(parsed['command_emoji'])
                return MessageCommand(text=emotified, channel_name=channel)
            else:
                return MessageCommand(text="Channel {} not permitted".format(channel), channel=event['channel'])

    def emotify(self, parsed):
        emoji = parsed['emoji']
        message = parsed['message']
        return self.emoter.make_phrase(' '.join(message).upper(), emoji)
