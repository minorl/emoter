#!/usr/bin/env python3
from collections import defaultdict
import os
import sys


spaces_per_char = {':hatwobble:': 7.3, ':broccoli:': 7.35, ':skelni:': 7.35, ':chunk:': 7.35, ':davis:': 7.35, ':skull:': 7.35}
chars = defaultdict(list, {' ': [[0 for _ in range(3)] for _ in range(5)]})
DIR = os.path.dirname(os.path.abspath(__file__))


def get_char(c):
    if c not in chars:
        with open('{}/characters/{}.txt'.format(DIR, c)) as f:
            for line in f:
                chars[c].append([int(i) for i in line.strip()])

    return chars[c]


def make_phrase(phrase, emoji):
    result = [(['.'], 0, 0) for _ in range(5)]
    for char in phrase:
        for i, line in enumerate(get_char(char)):
            for c in line:
                if c:
                    result[i][0].append(emoji)
                else:
                    chars, needed_spaces, curr_spaces = result[i]
                    needed_spaces += spaces_per_char[emoji]
                    while curr_spaces < round(needed_spaces):
                        chars.append(' ')
                        curr_spaces += 1
                    result[i] = chars, needed_spaces, curr_spaces
            result[i][0].extend(' ' for _ in range(5))

    return '\n'.join(''.join(l) for l, _, _ in result)

if __name__ == '__main__':
    emoji = sys.argv[2] if len(sys.argv) > 2 else ':hatwobble:'
    print(make_phrase(sys.argv[1], emoji))
