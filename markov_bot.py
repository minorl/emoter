from collections import Counter, defaultdict
from itertools import chain
import logging
from pathlib import Path

from markov.markov_chain import MarkovChain
from nltk import word_tokenize
from numpy.random import choice
from pyparsing import CaselessLiteral, Optional, Word, alphanums, StringEnd
from reddit.monitor import get_user_comments, get_user_posts
from slack.bot import SlackBot, register
from slack.command import HistoryCommand, MessageCommand
from slack.parsing import symbols
from util import mention_to_uid


logger = logging.getLogger(__name__)


class MarkovBot(SlackBot):
    def __init__(self, slack=None):
        super().__init__(slack=slack)
        self.markov_name = 'Markov Message Generation'
        self.markov_expr = (CaselessLiteral('simulate') +
                            (symbols.flag_with_arg('reddit', symbols.user_name) |
                            symbols.mention.setResultsName('user'))
                           + StringEnd())
        self.markov_doc = ('Generate a message based on a user\'s messages:\n'
                           '\tsimulate <user>')

        self.custom_name = 'Other markov chains'
        self.custom_expr = CaselessLiteral('markov') + Word(alphanums).setResultsName('chain_name') + StringEnd()
        self.custom_doc = ('Run assorted other markov chains:\n'
                           '\tmarkov <chain name>')

        self.slack_chains = defaultdict(MarkovChain)
        slack.preload_commands((HistoryCommand(callback=self._hist_callback),))

        self.reddit_chains = defaultdict(MarkovChain)
        self.reddit_transition_totals = defaultdict(Counter)
        self.reddit_most_recent_comments = defaultdict(int)
        self.reddit_most_recent_posts = defaultdict(int)

        # Load chains from data directory
        self.chains = {}

    def _get_chain(self, name):
        name = name.lower()
        if name in self.chains:
            return self.chains[name]
        f_path = Path('markov/data/{}.txt'.format(name.lower()))
        if f_path.exists():
            new_chain = MarkovChain()
            with f_path.open() as f:
                for line in f:
                    new_chain.load_string(line)
            self.chains[f_path.stem] = new_chain
            return new_chain
        return None

    def _load_message(self, user, text, reddit=False):
        (self.reddit_chains if reddit else self.slack_chains)[user].load_string(text)

    async def _update_reddit_user(self, user):
        posts = await get_user_posts(user)
        comments = await get_user_comments(user)

        new_posts = posts[self.reddit_most_recent_posts[user]:]
        new_comments = comments[self.reddit_most_recent_comments[user]:]

        self.reddit_most_recent_posts[user] = len(posts)
        self.reddit_most_recent_comments[user] = len(comments)

        for comment in new_comments:
            if comment:
                self._load_message(user, comment, reddit=True)

        for _, post in new_posts:
            if post:
                self._load_message(user, post, reddit=True)

        return bool(posts or comments)

    async def _generate_message(self, user, reddit=False):
        text = (self.reddit_chains if reddit else self.slack_chains)[user].sample()
        return text

    async def _hist_callback(self, hist_list):
        for message in hist_list:
            self._load_message(message.uid, message.text)

    @register(name='markov_name', expr='markov_expr', doc='markov_doc')
    async def command_generate(self, user, in_channel, parsed):
        if 'reddit' in parsed:
            target_user = parsed['reddit']
            user_exists = await self._update_reddit_user(target_user)

            if user_exists:
                out_channel = in_channel
                out_message = await self._generate_message(target_user, reddit=True)
            else:
                out_channel = None
                out_message = 'User {} either does not exist or has no self posts or comments'.format(target_user)
        else:
            target_user = parsed['user']
            target_uid = mention_to_uid(target_user)
            if target_uid in self.slack_chains:
                out_channel = in_channel
                out_message = await self._generate_message(target_uid)
            else:
                out_channel = None
                out_message = 'User {} not found'.format(target_user)
        return MessageCommand(user=user, channel=out_channel, text=out_message)

    @register(name='custom_name', expr='custom_expr', doc='custom_doc')
    async def command_custom_markov(self, user, in_channel, parsed):
        chain_name = parsed['chain_name']
        chain = self._get_chain(chain_name)
        if chain:
            message = chain.sample()
        else:
            message = 'Chain {} does not exist'.format(chain_name)
        return MessageCommand(user=user, channel=in_channel, text=message)

    @register()
    async def markov_monitor(self, user, in_channel, message):
        self._load_message(user, message)

