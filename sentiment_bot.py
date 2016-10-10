from functools import partial
import numpy as np
from pyparsing import CaselessLiteral, Optional, StringEnd
from sentiment import lstm
from slack.bot import register, SlackBot
from slack.command import HistoryCommand, MessageCommand
from slack.parsing import symbols
import time


class SentimentBot(SlackBot):
    def __init__(self, session, slack):
        self.name = 'Sentiment Stats'
        self.expr = (CaselessLiteral('feels') +
                     Optional(symbols.flag_with_arg('user', symbols.user_name)) +
                     StringEnd())
        self.doc = ('Show someone\'s feels:\n'
                    '\tfeels [--user <user>]')

        self.extrema_name = 'Emotional Moments'
        self.extrema_expr = ((CaselessLiteral('grumpy') | CaselessLiteral('happy') | CaselessLiteral('meh')).setResultsName('emotion') +
                             Optional(symbols.flag_with_arg('user', symbols.user_name)) +
                             StringEnd())
        self.extrema_doc = ('Show a particularly grumpy, happy or meh quote:\n'
                            '\t(grumpy|happy|meh) [--user <user>]')

        self.model = lstm.load_model(session)
        self.session = session

    @register(name='name', expr='expr', doc='doc')
    async def command_stats(self, user, in_channel, parsed):
        kwargs = {}
        kwargs['callback'] = partial(self._stats_callback, in_channel, user)

        if 'user' in parsed:
            kwargs['user'] = parsed['user']
        return HistoryCommand(**kwargs)

    async def _stats_callback(self, out_channel, user, hist_list):
        if not hist_list:
            return
        softmaxes = [self.model.predict(self.session, q.text) for q in hist_list]
        counts = [0, 0]
        for s in softmaxes:
            # Exclude neutral val
            counts[np.argmax((s[0], s[2]))] += 1
        negative, positive = [100 * c/len(softmaxes) for c in counts]
        return MessageCommand(text='Positive: {:.0f}% Negative: {:.0f}%'.format(positive, negative), user=user, channel=out_channel)

    @register(name='extrema_name', expr='extrema_expr', doc='extrema_doc')
    async def command_extrema(self, user, in_channel, parsed):
        kwargs = {}
        index = {'grumpy': 0, 'meh': 1, 'happy': 2}[parsed['emotion']]
        kwargs['callback'] = partial(self._extrema_callback, index, in_channel, user)
        if 'user' in parsed:
            kwargs['user'] = parsed['user']
        return HistoryCommand(**kwargs)

    async def _extrema_callback(self, index, out_channel, user, hist_list):
        if not hist_list:
            return
        quote = max(hist_list, key=lambda q: self.model.predict(self.session, q.text)[index])
        year = time.strftime('%Y', time.localtime(float(quote.time)))
        return MessageCommand(channel=out_channel, user=user, text='> {}\n-{} {}'.format(quote.text, quote.user, year))
