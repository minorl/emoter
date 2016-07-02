from pyparsing import CaselessLiteral, StringEnd
from haiku import Haiku
from slack.bot import SlackBot, register
from slack.command import MessageCommand


class HaikuBot(SlackBot):
    def __init__(self, slack=None):
        self.haiku_name = 'Haiku'
        self.haiku_expr = CaselessLiteral('haiku') + StringEnd()
        self.haiku_doc = "Generate a random haiku."

        self.haiku = Haiku()

    @register(name='haiku_name', expr='haiku_expr', doc='haiku_doc')
    async def command_twitch(self, user, in_channel, parsed):
        print("in_channel:", in_channel)
        return MessageCommand(text=self.haiku.generate_haiku(), channel=in_channel, user=user)
