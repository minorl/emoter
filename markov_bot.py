from collections import Counter, defaultdict
from itertools import chain

from nltk import word_tokenize
from numpy.random import choice
from pyparsing import CaselessLiteral
from slack.bot import SlackBot, register
from slack.command import HistoryCommand, MessageCommand
from slack.parsing import symbols


class MarkovBot(SlackBot):
    def __init__(self, slack=None):

        self.markov_name = 'Markov Message Generation'
        self.markov_expr = CaselessLiteral('simulate') + symbols.user_name.setResultsName('user')
        self.markov_doc = ('Generate a message based on a user\'s messages:\n'
                           '\tsimulate <user>')

        self.user_transitions = defaultdict(lambda: defaultdict(Counter))
        self.user_transition_totals = defaultdict(Counter)
        slack.preload_commands((HistoryCommand(callback=self._hist_callback),))

    def _load_message(self, user, text):
        last_word = None
        for word in chain(word_tokenize(text), [None]):
            self.user_transitions[user][last_word][word] += 1
            self.user_transition_totals[user][last_word] += 1
            last_word = word

    def _generate_message(self, user):
        last_word = None
        result = []
        transitions = self.user_transitions[user]
        totals = self.user_transition_totals[user]
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
        if target_user in self.user_transitions:
            out_channel = in_channel
            out_message = self._generate_message(target_user)
        else:
            out_channel = None
            out_message = 'User {} not found'.format(target_user)
        return MessageCommand(user=user, channel=out_channel, text=out_message)

    @register()
    async def markov_monitor(self, user, in_channel, message):
        self._load_message(user, message)
