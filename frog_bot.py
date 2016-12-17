import re
from slack.bot import SlackBot, register
from slack.command import MessageCommand


class FrogBot(SlackBot):
    def __init__(self, frog_channels, slack=None):
        self.channels = frog_channels
        self.reg = re.compile('what (are|is) ([^ ]*)', re.IGNORECASE)

    @register(channels='channels')
    async def frog_monitor(self, user, in_channel, message):
        match = self.reg.search(message)
        if match:
            return MessageCommand(text='what _{}_ {}'.format(match.group(1), match.group(2)), channel=in_channel, user=user)
