from collections import Counter, defaultdict
from itertools import chain
import logging

from nltk import word_tokenize
from numpy.random import choice
from pyparsing import CaselessLiteral, Optional
from reddit.monitor import get_user_comments, get_user_posts
from slack.bot import SlackBot, register
from slack.command import HistoryCommand, MessageCommand
from slack.parsing import symbols


logger = logging.getLogger(__name__)


class MarkovBot(SlackBot):
    def __init__(self, slack=None):
        super().__init__(slack=slack)
        self.markov_name = 'Markov Message Generation'
        self.markov_expr = (CaselessLiteral('simulate') +
                            Optional(symbols.flag('reddit')) +
                            symbols.user_name.setResultsName('user'))
        self.markov_doc = ('Generate a message based on a user\'s messages:\n'
                           '\tsimulate <user>')

        self.user_transitions = defaultdict(lambda: defaultdict(Counter))
        self.user_transition_totals = defaultdict(Counter)
        slack.preload_commands((HistoryCommand(callback=self._hist_callback),))

        self.reddit_transitions = defaultdict(lambda: defaultdict(Counter))
        self.reddit_transition_totals = defaultdict(Counter)
        self.reddit_most_recent_comments = defaultdict(int)
        self.reddit_most_recent_posts = defaultdict(int)

    def _load_message(self, user, text, reddit=False):
        last_word = None
        for word in chain(word_tokenize(text), [None]):
            (self.reddit_transitions if reddit else self.user_transitions)[user][last_word][word] += 1
            (self.reddit_transition_totals if reddit else self.user_transition_totals)[user][last_word] += 1
            last_word = word

    async def _update_reddit_user(self, user):
        posts = await get_user_posts(user)
        comments = await get_user_comments(user)

        new_posts = posts[self.reddit_most_recent_posts[user]:]
        new_comments = comments[self.reddit_most_recent_comments[user]:]

        self.reddit_most_recent_posts[user] = len(posts)
        self.reddit_most_recent_comments[user] = len(comments)

        for comment in new_comments:
            self._load_message(user, comment, reddit=True)

        for title, post in new_posts:
            self._load_message(user, title, reddit=True)
            self._load_message(user, post, reddit=True)

        return bool(posts or comments)

    async def _generate_message(self, user, reddit=False):
        last_word = None
        result = []
        transitions = (self.reddit_transitions if reddit else self.user_transitions)[user]
        totals = (self.reddit_transition_totals if reddit else self.user_transition_totals)[user]
        while last_word is not None or not result:
            total = totals[last_word]
            probs = []
            candidates = []
            for candidate, count in transitions[last_word].items():
                probs.append(count / total)
                candidates.append(candidate)
            last_word = choice(candidates, p=probs)
            result.append(last_word)

        return ' '.join(result[:-1])

    async def _hist_callback(self, hist_list):
        for message in hist_list:
            self._load_message(message.user, message.text)

    @register(name='markov_name', expr='markov_expr', doc='markov_doc')
    async def command_generate(self, user, in_channel, parsed):
        target_user = parsed['user']
        if 'reddit' in parsed:
            user_exists = await self._update_reddit_user(target_user)

            if user_exists:
                out_channel = in_channel
                out_message = await self._generate_message(target_user, reddit=True)
            else:
                out_channel = None
                out_message = 'User {} either does not exist or has no self posts or comments'.format(target_user)
        else:
            if target_user in self.user_transitions:
                out_channel = in_channel
                out_message = await self._generate_message(target_user)
            else:
                out_channel = None
                out_message = 'User {} not found'.format(target_user)
        return MessageCommand(user=user, channel=out_channel, text=out_message)

    @register()
    async def markov_monitor(self, user, in_channel, message):
        self._load_message(user, message)

