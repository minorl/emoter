from pyparsing import CaselessLiteral, StringEnd
from slack.bot import SlackBot, register
from slack.command import MessageCommand, ReactCommand
from slack.parsing import symbols
from functools import partial 


class PollBot(SlackBot):
    def __init__(self, slack=None):
        self.name = "Simple Poll"
        self.expr = CaselessLiteral('poll') + symbols.comma_list + StringEnd()
        self.doc = "Basic poll (up to 10 options)\n\tpoll <option1>, <option2> [, ... <option10>])"
        self.emoji = [':one:', ':two:', ':three:', ':four:', ':five:', ':six:', ':seven:', ':eight:', ':nine:', ':keycap_ten:']

    @register(name='name', expr='expr', doc='doc')
    async def command_poll(self, user, in_channel, parsed):
        options = parsed['comma_list']
        noptions = len(options)
        if not 2 <= noptions <= 10:
            text = 'Invalid number of options provided. {} received, please provide between 2 and 10.'.format(noptions)
            cb = None
        else:
            text = "Please vote:\n"
            text += "\n".join([a + " " + b for a,b in zip(self.emoji, options)])
            cb = partial(self.response_react, self.emoji[:noptions])
        return MessageCommand(text=text, channel=in_channel, user=user, success_callback=cb)

    def response_react(self, emoji):
        return [ReactCommand(e.strip(':')) for e in emoji]

        
