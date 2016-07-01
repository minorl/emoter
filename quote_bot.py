from functools import partial
from pyparsing import CaselessLiteral, Optional
import random
from slack.bot import register, SlackBot
from slack.command import HistoryCommand, MessageCommand
from slack.parsing import symbols
import time


class QuoteBot(SlackBot):
    def __init__(self, slack):
        self.name = 'Randomly quote someone.'
        self.expr = (CaselessLiteral('quote') +
                     Optional(symbols.flag_with_arg('channel', symbols.channel_name)) +
                     Optional(symbols.user_name.setResultsName('user'))
                     )
        self.doc = ('Get a random quote:\n'
                    '\tquote [--channel <channel>] [user]')

    @register(name='name', expr='expr', doc='doc')
    async def command_quote(self, user, in_channel, parsed):
        kwargs = {}
        if 'user' in parsed:
            kwargs['user'] = parsed['user']

        if 'channel' in parsed:
            kwargs['channel'] = parsed['channel']

        kwargs['callback'] = partial(self._quoter_callback, in_channel)

        return HistoryCommand(**kwargs)

    async def _quoter_callback(self, out_channel, hist_list):
        quote = random.choice(hist_list)
        year = time.strftime('%Y', time.localtime(float(quote.time)))
        return MessageCommand(channel=out_channel, user=None, text='> {}\n-{} {}'.format(quote.text, quote.user, year))
