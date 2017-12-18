from collections import defaultdict, Counter
from enum import Enum
from itertools import chain

from nltk import word_tokenize
from nltk.tokenize.moses import MosesDetokenizer
import numpy as np

class Modes(Enum):
    DEFAULT, QUOTE, PAREN = range(3)

OPEN = {'(': Modes.PAREN, '``': Modes.QUOTE}
MODE_TO_OPEN = {m: o for o, m in OPEN.items()}
CLOSE = {Modes.PAREN: ')', Modes.QUOTE: "''", Modes.DEFAULT: None}

class MarkovChain:
    def __init__(self):
        self.transitions = {mode: defaultdict(Counter) for mode in Modes}
        self.transition_totals = {mode: Counter() for mode in Modes}

    def load_string(self, text):
        last_word = None
        mode = Modes.DEFAULT
        stack = [mode]
        tokens = word_tokenize(text.strip())
        if not tokens:
            return
        for word in chain(tokens, [None]):
            mode = stack[-1]
            if word in OPEN:
                self.transitions[mode][last_word][OPEN[word]] += 1
                self.transition_totals[mode][last_word] += 1
                last_word = None
                stack.append(OPEN[word])
            elif word == CLOSE[mode]:
                self.transitions[mode][last_word][CLOSE[mode]] += 1
                self.transition_totals[mode][last_word] += 1
                stack.pop()
                last_word = word
            elif word != None: # Ignore Nones while not in Modes.DEFAULT
                self.transitions[mode][last_word][word] += 1
                self.transition_totals[mode][last_word] += 1
                last_word = word

        while stack:
            mode = stack.pop()
            close = CLOSE[mode]
            self.transitions[mode][last_word][close] += 1
            self.transition_totals[mode][last_word] += 1
            last_word = close

    def sample(self):
        last_word = None
        mode_stack = [Modes.DEFAULT]
        result = []

        while mode_stack:
            mode = mode_stack[-1]
            probs = []
            candidates = []
            total = self.transition_totals[mode][last_word]
            for word, t_count in self.transitions[mode][last_word].items():
                probs.append(t_count / total)
                candidates.append(word)
            last_word = np.random.choice(candidates, p=probs)
            if last_word == CLOSE[mode]:
                result.append(last_word)
                mode_stack.pop()
            elif isinstance(last_word, Modes):
                mode = last_word
                mode_stack.append(mode)
                result.append(MODE_TO_OPEN[mode])
                last_word = None
            else:
                result.append(last_word)
        i = 0
        while i < len(result):
            if result[i] == '``' or result[i] == "''":
                result[i] = '"'
            if result[i] == '(' and i < len(result) - 1:
                result[i] = '(' + result[i + 1]
                del result[i + 1]
            i += 1
        return MosesDetokenizer().detokenize(result[:-1], return_str=True)
