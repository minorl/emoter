#!/usr/bin/env python3
import os
import string
import sys


class Emoter:
    def __init__(self, spaces_per_char=7.34, character_dir=os.path.dirname(os.path.abspath(__file__))):
        self.spaces_per_char = spaces_per_char
        self.character_dir = character_dir
        self.load_chars()

    def load_chars(self):
        self.chars = {' ': [[0 for _ in range(3)] for _ in range(5)]}
        for char in string.ascii_uppercase + '^$':
            self.chars[char] = []
            with open('{}/characters/{}.txt'.format(self.character_dir, char)) as f:
                for line in f:
                    self.chars[char].append([int(i) for i in line.strip()])

    def make_phrase(self, phrase, emoji):
        result = [(['.'], 0, 0) for _ in range(5)]
        for char in phrase:
            for i, line in enumerate(self.chars[char]):
                for c in line:
                    if c:
                        result[i][0].append(emoji)
                    else:
                        chars, needed_spaces, curr_spaces = result[i]
                        needed_spaces += self.spaces_per_char
                        while curr_spaces < round(needed_spaces):
                            chars.append(' ')
                            curr_spaces += 1
                        result[i] = chars, needed_spaces, curr_spaces
                result[i][0].extend(' ' for _ in range(5))

        return '\n'.join(''.join(l) for l, _, _ in result)

if __name__ == '__main__':
    emoji = sys.argv[2] if len(sys.argv) > 2 else ':hatwobble:'
    emoter = Emoter()
    print(emoter.make_phrase(sys.argv[1], emoji))
