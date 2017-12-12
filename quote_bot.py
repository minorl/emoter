from functools import partial
import random
import time

from pyparsing import CaselessLiteral, Optional, StringEnd
from slack.bot import register, SlackBot
from slack.command import HistoryCommand, MessageCommand
from slack.parsing import symbols
from util import mention_to_uid, uid_to_mention


class QuoteBot(SlackBot):
    def __init__(self, slack):
        super().__init__(slack=slack)
        self.name = 'Randomly quote someone.'
        self.expr = (CaselessLiteral('quote') +
                     Optional(symbols.flag_with_arg('channel', symbols.channel_name)) +
                     Optional(symbols.mention.setResultsName('user')) +
                     StringEnd())
        self.doc = ('Get a random quote:\n'
                    '\tquote [--channel <channel>] [user]')

    @register(name='name', expr='expr', doc='doc')
    async def command_quote(self, user, in_channel, parsed):
        kwargs = {}
        if 'user' in parsed:
            kwargs['user'] = mention_to_uid(parsed['user'])

        if 'channel' in parsed:
            kwargs['channel'] = parsed['channel']

        kwargs['callback'] = partial(self._quoter_callback, in_channel, user)

        return HistoryCommand(**kwargs)

    async def _quoter_callback(self, out_channel, user, hist_list):
        if not hist_list:
            return None
        quote = random.choice(hist_list)
        year = time.strftime('%Y', time.localtime(float(quote.time)))
        return MessageCommand(channel=out_channel, user=user, text='> {}\n-{} {}'.format(quote.text, uid_to_mention(quote.uid), year))
