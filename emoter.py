#!/usr/bin/env python3
import os
import string
import sys


class Emoter:
    def __init__(self, character_dir=os.path.dirname(os.path.abspath(__file__))):
        self.character_dir = character_dir
        self.load_chars()
        self.space_emoji = ':s:'

    def load_chars(self):
        self.chars = {' ': [[0 for _ in range(2)] for _ in range(5)]}
        for fname in os.listdir('characters'):
            if fname.endswith('.txt'):
                print(fname)
                char = fname[0]
                self.chars[char] = []
                with open('characters/{}'.format(fname)) as f:
                    for line in f:
                        self.chars[char].append([int(i) for i in line.strip()])

    def make_phrase(self, phrase, emoji):
        result = [[] for _ in range(5)]
        for char in phrase:
            for i, line in enumerate(self.chars[char]):

                for c in line:
                    result[i].append(emoji if c else self.space_emoji)
                result[i].extend(' ' for _ in range(5))

        return '\n'.join(''.join(l) for l in result)

if __name__ == '__main__':
    emoji = sys.argv[2] if len(sys.argv) > 2 else ':hatwobble:'
    emoter = Emoter()
    print(emoter.make_phrase(sys.argv[1], emoji))
