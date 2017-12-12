from collections import Counter, defaultdict
from functools import partial
import random
import time

import config
from mongoengine.errors import NotUniqueError
import numpy as np
from pyparsing import CaselessLiteral, nums, Optional, StringEnd, Word
from sentiment import lstm
from sentiment.history import SentimentDoc
from slack.bot import register, SlackBot
from slack.command import HistoryCommand, MessageCommand
from slack.parsing import symbols
from util import mention_to_uid, uid_to_mention

COOLDOWN = 50


class SentimentBot(SlackBot):
    def __init__(self, session, slack):
        self.name = 'Sentiment Stats'
        self.expr = (CaselessLiteral('feels') +
                     Optional(symbols.mention.setResultsName('user')) +
                     StringEnd())
        self.doc = ('Show someone\'s feels:\n'
                    '\tfeels [<user>]')

        self.extrema_name = 'Emotional Moments'
        self.extrema_expr = ((CaselessLiteral('grumpy') | CaselessLiteral('happy') | CaselessLiteral('meh')).setResultsName('emotion') +
                             Optional(symbols.mention.setResultsName('user')) +
                             StringEnd())
        self.extrema_doc = ('Show a particularly grumpy, happy or meh quote:\n'
                            '\t(grumpy|happy|meh) <user>')

        self.judge_name = 'Measure sentiment'
        self.judge_expr = (CaselessLiteral('lyte') +
                           ((Optional(symbols.flag_with_arg('decimals', Word(nums))) + symbols.tail('text')) |
                           symbols.tail('text')) + StringEnd())
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
        target_uid = mention_to_uid(parsed['user']) if 'user' in parsed else None
        kwargs['callback'] = partial(
            self._stats_callback,
            in_channel,
            user,
            target_user=target_uid if target_uid else None)

        if target_uid:
            kwargs['user'] = target_uid
        return HistoryCommand(**kwargs)

    async def _stats_callback(self, out_channel, user, hist_list, target_user=None):
        if not hist_list:
            return
        softmaxes = [(obj.neg_sent, obj.neut_sent, obj.pos_sent) for obj in self._complete_cache(hist_list, user=target_user)]
        counts = [0, 0]
        for s in softmaxes:
            # Exclude neutral val
            counts[np.argmax((s[0], s[2]))] += 1
        negative, positive = [100 * c / len(softmaxes) for c in counts]
        return MessageCommand(text='Positive: {:.0f}% Negative: {:.0f}%'.format(positive, negative), user=user, channel=out_channel)

    @register(name='extrema_name', expr='extrema_expr', doc='extrema_doc')
    async def command_extrema(self, user, in_channel, parsed):
        kwargs = {}
        emotion = {'grumpy': 'neg_sent', 'meh': 'neut_sent', 'happy': 'pos_sent'}[parsed['emotion']]
        target_uid = mention_to_uid(parsed['user']) if 'user' in parsed else None
        kwargs['callback'] = partial(
            self._extrema_callback,
            emotion,
            in_channel,
            user,
            target_user= target_uid if target_uid in parsed else None)

        if target_uid:
            kwargs['user'] = target_uid
        return HistoryCommand(**kwargs)

    async def _extrema_callback(self, field, out_channel, user, hist_list, target_user=None):
        if not hist_list:
            return
        q_time = max(self._complete_cache(hist_list, user=target_user), key=lambda obj: getattr(obj, field)).time
        quote = next(r for r in hist_list if r.time == q_time)
        year = time.strftime('%Y', time.localtime(float(quote.time)))
        return MessageCommand(channel=out_channel, user=user, text='> {}\n-{} {}'.format(quote.text, uid_to_mention(quote.uid), year))

    @register(name='judge_name', expr='judge_expr', doc='judge_doc')
    async def command_judge(self, user, in_channel, parsed):
        sent = self.predict(parsed['text'][0])
        sent *= 100
        decimals = parsed['decimals'] if 'decimals' in parsed else '0'
        format_str = 'Positive: {:.' + decimals + 'f}% Negative: {:.' + decimals + 'f}%'
        return MessageCommand(text=format_str.format(sent[2], sent[0]), channel=in_channel, user=user)

    @register(channels='monitor_channels', include_timestamp=True)
    async def sentiment_monitor(self, user, in_channel, message, timestamp):
        if not in_channel:
            return
        neg, neut, pos = self.predict(message)
        SentimentDoc(time=timestamp, user=user, channel=in_channel, pos_sent=pos, neut_sent=neut, neg_sent=neg).save()
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

    def _complete_cache(self, complete_hist, user=None, channel=None):
        kwargs = {}
        if user is not None:
            kwargs['user'] = user
        if channel is not None:
            kwargs['channel'] = channel

        sent_hist = SentimentDoc.objects(**kwargs)

        known_timestamps = set(obj.time for obj in sent_hist)
        new_messages = [rec for rec in complete_hist if rec.time not in known_timestamps]

        if new_messages:
            for rec in new_messages:
                neg, neut, pos = self.predict(rec.text)
                try:
                    SentimentDoc(
                        time=rec.time,
                        user=rec.uid,
                        channel=rec.channel,
                        neg_sent=neg,
                        neut_sent=neut,
                        pos_sent=pos).save()
                except NotUniqueError as e:
                    print(Counter(rec.time for rec in new_messages).most_common(5))
                    print('Bad save for user {}'.format(user))
                    print([(o.user, o.channel) for o in SentimentDoc.objects(time=rec.time)])
                    print(rec.uid, rec.channel, rec.text)
                    exit()
            sent_hist = SentimentDoc.objects(**kwargs)
        return sent_hist
