from functools import partial
import numpy as np
from pyparsing import CaselessLiteral, Optional, StringEnd
from sentiment import lstm
from slack.bot import register, SlackBot
from slack.command import HistoryCommand, MessageCommand
from slack.parsing import symbols


class SentimentBot(SlackBot):
    def __init__(self, session, slack):
        self.name = 'Sentiment Stats'
        self.expr = (CaselessLiteral('feels') +
                     Optional(symbols.flag_with_arg('user', symbols.user_name)) +
                     StringEnd())
        self.doc = ('Display some information about how people are feeling.')
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
        counts = [0, 0, 0]
        for s in softmaxes:
            counts[np.argmax(s)] += 1
        fracs = [100 * c/len(softmaxes) for c in counts]
        return MessageCommand(text='{:.0f}%/{:.0f}%/{:.0f}% negative/neutral/positive'.format(*fracs), user=user, channel=out_channel)
