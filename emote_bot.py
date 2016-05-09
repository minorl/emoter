from collections import defaultdict
from emoter import Emoter
from pyparsing import Optional
from slack.bot import SlackBot, register
from slack.command import MessageCommand
from slack.parsing import symbols
import time


class EmoteBot(SlackBot):
    def __init__(self, channels, delay=60, slack=None):
        self.channels = channels

        self.emoter = Emoter()

        self.emoji_name = 'Emoji Text'
        self.emoji_expr = (Optional(symbols.channel_name) + symbols.emoji + symbols.message)
        self.emoji_doc = "Display text using emojis: [channel] <emoji> <message>"

        self.next_use = defaultdict(float)
        self.delay = delay

    @register(name='emoji_name', expr='emoji_expr', channels='channels', doc='emoji_doc')
    async def command_emoji(self, user, in_channel, parsed):
        emotify = False
        if 'channel' in parsed and parsed['channel'] not in self.channels:
            out_text = "Channel {} not recognized or not permitted.".format(parsed['channel'])
            out_channel = None
        elif 'channel' in parsed:
            curr_time = time.time()
            diff = int(self.next_use[user] - curr_time)
            if diff > 0:
                out_text = "You can send another message in {} seconds.".format(diff)
                out_channel = None
            else:
                self.next_use[user] = curr_time + self.delay
                emotify = True
                out_channel = parsed['channel']
        else:
            out_channel = in_channel
            emotify = True

        if emotify:
            out_text = self.emotify(parsed)

        if out_channel is None:
            return MessageCommand(text=out_text, user=user)
        else:
            return MessageCommand(text=out_text, channel=out_channel)

    def emotify(self, parsed):
        emoji = parsed['emoji']
        message = parsed['message']
        return self.emoter.make_phrase(' '.join(message).upper(), emoji)
