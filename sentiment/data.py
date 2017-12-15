from collections import Counter
import csv
from itertools import chain, repeat
import logging
from pathlib import Path
import pickle
import random
import string

from nltk.tokenize.casual import casual_tokenize
import numpy as np

from unidecode import unidecode

logger = logging.getLogger(__name__)

TRAIN_FILE = 'training.1600000.processed.noemoticon.csv'
POLARITY_FIELD = 0
TEXT_FIELD = 5

MIN_WORD_OCCURRENCES = 5

EMBEDDING_FILE = 'glove_embedding.txt'
EMBEDDING_PICKLE = 'sentiment/embedding.p'

START_TOKEN = '<start>'
END_TOKEN = '<end>'
UNK_TOKEN = '<unknown>'

EMBEDDING_DIM = 300

def preprocess(sent):
    return casual_tokenize(sent.strip().lower(), strip_handles=True, reduce_len=True)

def _load_corpus(val_frac):
    with open(TRAIN_FILE, encoding='latin-1') as f:
        reader = csv.reader(f)
        all_lines = []
        all_labels = []
        i = 0
        for line in reader:
            all_lines.append(preprocess(line[TEXT_FIELD]))
            all_labels.append(int(line[POLARITY_FIELD]) // 2)
            i += 1
            if i % 10000 == 0:
                logger.info('Processed {} examples'.format(i))
    indices = list(range(len(all_lines)))
    random.seed(44)
    random.shuffle(indices)
    cutoff = int(len(indices) * (1 - val_frac))
    train_lines = [all_lines[i] for i in indices[:cutoff]]
    train_labels = [all_labels[i] for i in indices[:cutoff]]
    val_lines = [all_lines[i] for i in indices[cutoff:]]
    val_labels = [all_labels[i] for i in indices[cutoff:]]
    return train_lines, np.array(train_labels).astype(np.int64), val_lines, np.array(val_labels).astype(np.int64)

def _get_words(sents):
    counts = Counter()
    for line in sents:
        counts.update(line)
    word_set = set(w for w, c in counts.items() if c >= MIN_WORD_OCCURRENCES)
    return word_set

def _convert_data(word_map, train_sents, val_sents):
    max_len = max(len(s) for s in train_sents)
    train_indices = []
    train_lens = np.zeros(len(train_sents), dtype=np.int64)

    val_indices = []
    val_lens = np.zeros(len(val_sents), dtype=np.int64)
    for sents, indices, lens in ((train_sents, train_indices, train_lens), (val_sents, val_indices, val_lens)):
        for i, sent in enumerate(sents):
            lens[i] = len(sent) + 2
            sent_indices = [word_map.get(w, word_map[UNK_TOKEN]) for w in chain([START_TOKEN], sent, [END_TOKEN])]
            indices.append(sent_indices)
            # sent_indices.extend(repeat(0, max_len - len(sent)))
            if (i + 1) % 10000 == 0:
                logger.info('Converted {} examples'.format(i + 1))
    return train_indices, train_lens, val_indices, val_lens

def _load_embeddings(word_set):
    pickle_path = Path(EMBEDDING_PICKLE)
    if pickle_path.exists():
        with pickle_path.open('rb') as f:
            return pickle.load(f)

    word_map = {}
    embeddings = []
    with open(EMBEDDING_FILE) as f:
        for line in f:
            fields = line[:-1].split(' ')
            word = ' '.join(fields[:-EMBEDDING_DIM])
            if word in word_set:
                embed = [float(f) for f in fields[-EMBEDDING_DIM:]]
                word_map[word] = len(word_map)
                embeddings.append(embed)

    for token in (START_TOKEN, END_TOKEN, UNK_TOKEN):
        logger.info('Adding {} token'.format(token))
        word_map[token] = len(word_map)
        embeddings.append(np.zeros(EMBEDDING_DIM))

    embeddings = np.array(embeddings).astype(np.float32)
    with open(EMBEDDING_PICKLE, 'wb') as f:
        pickle.dump((embeddings, word_map), f)
    return embeddings, word_map

def load_dataset(val_frac=0.1):
    logger.info('Loading corpus')
    t_x, t_y, v_x, v_y = _load_corpus(val_frac)
    logger.info('Getting high frequency')
    word_set = _get_words(t_x)
    logger.info('Got {} words'.format(len(word_set)))
    logger.info('Loading embeddings')
    embeddings, word_map = _load_embeddings(word_set)
    logger.info('Converting data to indices')
    t_x, t_lens, v_x, v_lens = _convert_data(word_map, t_x, v_x)
    return embeddings, word_map, t_x, t_y, t_lens, v_x, v_y, v_lens

