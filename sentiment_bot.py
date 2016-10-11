from collections import defaultdict
import config
from functools import partial
import numpy as np
from pyparsing import CaselessLiteral, nums, Optional, StringEnd, Word
import random
from sentiment import lstm
from slack.bot import register, SlackBot
from slack.command import HistoryCommand, MessageCommand
from slack.parsing import symbols
import time

COOLDOWN = 50


class SentimentBot(SlackBot):
    def __init__(self, session, slack):
        self.name = 'Sentiment Stats'
        self.expr = (CaselessLiteral('feels') +
                     Optional(symbols.user_name.setResultsName('user')) +
                     StringEnd())
        self.doc = ('Show someone\'s feels:\n'
                    '\tfeels [<user>]')

        self.extrema_name = 'Emotional Moments'
        self.extrema_expr = ((CaselessLiteral('grumpy') | CaselessLiteral('happy') | CaselessLiteral('meh')).setResultsName('emotion') +
                             Optional(symbols.user_name.setResultsName('user')) +
                             StringEnd())
        self.extrema_doc = ('Show a particularly grumpy, happy or meh quote:\n'
                            '\t(grumpy|happy|meh) <user>')

        self.judge_name = 'Measure sentiment'
        self.judge_expr = (CaselessLiteral('lyte') +
                           Optional(symbols.flag_with_arg('decimals', Word(nums))) +
                           symbols.tail.setResultsName('text') + StringEnd())
        self.judge_doc = ('Evaluate the sentiment of a piece of text:\n'
                          '\tlyte [--decimals <decimals>] <message>')

        self.sentiments = defaultdict(list)
        self.cooldowns = defaultdict(int)
        self.monitor_channels = config.SENTIMENT_MONITOR_CHANNELS

        model = lstm.load_model(session)
        self.predict = partial(model.predict, session)

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
        softmaxes = [self.predict(q.text) for q in hist_list]
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
        quote = max(hist_list, key=lambda q: self.predict(q.text)[index])
        year = time.strftime('%Y', time.localtime(float(quote.time)))
        return MessageCommand(channel=out_channel, user=user, text='> {}\n-{} {}'.format(quote.text, quote.user, year))

    @register(name='judge_name', expr='judge_expr', doc='judge_doc')
    async def command_judge(self, user, in_channel, parsed):
        sent = self.predict(parsed['text'])
        sent *= 100
        decimals = parsed['decimals'] if 'decimals' in parsed else '0'
        format_str = 'Positive: {:.' + decimals + 'f}% Negative: {:.' + decimals + 'f}%'
        return MessageCommand(text=format_str.format(sent[2], sent[0]), channel=in_channel, user=user)

    @register(channels='monitor_channels')
    async def sentiment_monitor(self, user, in_channel, message):
        if not in_channel:
            return
        neg, _, pos = self.predict(message)
        channel_sentiment = self.sentiments[in_channel]
        channel_sentiment.append(pos + 0.2 > neg)
        if len(channel_sentiment) > 10:
            channel_sentiment.pop(0)

        self.cooldowns[in_channel] -= 1
        if self.cooldowns[in_channel] <= 0 and channel_sentiment.count(False) >= 7:
            self.cooldowns[in_channel] = COOLDOWN
            return MessageCommand(
                    text='You guys should cheer up. http://placekitten.com/{}/{}'.format(random.randint(300, 500), random.randint(300, 500)),
                    channel=in_channel)
