from collections import defaultdict
from nltk.corpus import cmudict
import random


def generate_partitions(n):
    """
    Recipe by David Eppstein: http://code.activestate.com/recipes/218332/
    """
    partitions = {}
    partitions[0] = [[]]
    for i in range(n):
        new_partitions = []
        for part in partitions[i]:
            new_partitions.append([1] + part)
            if part and (len(part) == 1 or part[1] > part[0]):
                new_partitions.append([part[0] + 1] + part[1:])
        partitions[i + 1] = new_partitions
    return partitions


class Haiku:
    def __init__(self):
        self.load_data()
        self.partitions = generate_partitions(7)

    def load_data(self, f_name='/usr/dict/share/words'):
        self.words = defaultdict(list)
        for word, lists in cmudict.dict().items():
            syll = sum(chunk[-1].isdigit() for chunk in lists[0])
            if syll <= 7:
                self.words[syll].append(word.upper())

    def _get_line(self, syllables):
        part = random.choice(self.partitions[syllables])
        return ' '.join(random.choice(self.words[syl]) for syl in part)

    def generate_haiku(self):
        return '\n'.join(self._get_line(syllables) for syllables in (5, 7, 5))


if __name__ == '__main__':
    h = Haiku()
    print(h.generate_haiku())
