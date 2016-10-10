from copy import copy
import csv
from itertools import chain, repeat
import numpy as np
import random
import re
import string
from unidecode import unidecode

POLARITY_FIELD = 0
TEXT_FIELD = 5
UNK_TOKEN = '<unknown>'
START_TOKEN = '<start>'
END_TOKEN = '<end>'


_filter_reg = re.compile('[' + string.punctuation + ']')


def preprocess(text): return [word.lower() for word in _filter_reg.sub(' ', unidecode(text)).split()]


def get_corpus_words(f_name):
    print('Getting set of known words')
    with open(f_name, encoding='latin-1') as f:
        reader = csv.reader(f)
        words = set()
        for line in reader:
            words |= set(preprocess(line[TEXT_FIELD]))
    return words


class Dataset:
    def __init__(self, f_name, word_map, max_len=None, force_max=100, val_frac=0.10):
        data = []
        labels = []
        lengths = []
        get_max = max_len is None
        if get_max:
            max_len = 0
        with open(f_name, encoding='latin-1') as f:
            reader = csv.reader(f)
            i = 0
            for line in reader:
                # Switch labels from 0, 2, 4 to 0, 1, 2
                vec = [word_map.get(w, word_map[UNK_TOKEN]) for w in chain((START_TOKEN,), preprocess(line[TEXT_FIELD]), (END_TOKEN,))]
                if force_max is not None and len(vec) > force_max:
                    continue
                if get_max:
                    max_len = max(max_len, len(vec))
                if len(vec) > max_len:
                    vec = vec[:max_len]
                data.append(vec)
                labels.append(int(line[POLARITY_FIELD]) / 2)
                lengths.append(len(vec))
                i += 1
                if i % 10000 == 0:
                    print('Loaded {} examples'.format(i))
        for v in data:
            v.extend(repeat(0, max_len - len(v)))
        self._data = np.array(data)
        self._labels = np.array(labels)
        self._lengths = np.array(lengths)
        self._max_len = max_len
        print('Max example len:', max_len)

        indices = list(range(len(self._data)))
        random.shuffle(indices)
        split_point = int(val_frac * len(indices))
        self._val_indices = indices[:split_point]
        self._train_indices = indices[split_point:]

    def batches(self, batch_size, train=True):
        order = copy(self._train_indices if train else self._val_indices)
        random.shuffle(order)
        for indices in (order[i:(i + batch_size)] for i in range(0, len(order), batch_size)):
            if len(indices) == batch_size:
                yield self._data[indices, :], self._labels[indices], self._lengths[indices]

    @property
    def max_len(self):
        return self._max_len
