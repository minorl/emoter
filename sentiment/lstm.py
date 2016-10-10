#!/usr/bin/env python3.5
import sentiment.dataset as dataset
from sentiment.dataset import END_TOKEN, START_TOKEN, UNK_TOKEN
import numpy as np
import os
import pickle
import tensorflow as tf
import time

TRAIN_FILE = 'training.1600000.processed.noemoticon.csv'
TEST_FILE = 'testdata.manual.2009.06.14.csv'
EMBEDDING_FILE = 'glove_embedding.txt'

N_CLASSES = 3


def _load_embeddings(embed_file=EMBEDDING_FILE, train_file=TRAIN_FILE, embedding_pickle='embedding.p'):
    if os.path.exists(embedding_pickle):
        with open(embedding_pickle, 'rb') as f:
            return pickle.load(f)
    corpus_words = dataset.get_corpus_words(TRAIN_FILE) | {dataset.UNK_TOKEN}
    print(len(corpus_words), 'words in training data')
    embeddings = []
    word_map = {}
    print('Loading embeddings')
    with open(embed_file, encoding='latin-1') as f:
        for line in f:
            w, *vec = line[:-1].split(' ')
            if w in corpus_words:
                word_map[w] = len(word_map)
                embeddings.append([float(v) for v in vec])
    for t in (START_TOKEN, END_TOKEN):
        word_map[t] = len(word_map)
        embeddings.append([0.0 for _ in embeddings[0]])
    print('Got {} embeddings'.format(len(embeddings)))
    embedding = np.array(embeddings)
    with open(embedding_pickle, 'wb') as f:
        pickle.dump((word_map, embedding), f)
    return word_map, embedding


class SentimentLSTM:
    def __init__(
            self,
            embedding_shape,
            word_map,
            batch_size=256,
            hidden_units=100,
            initial_embed=None,
            max_len=None,
            is_train=True,
            dropout_prob=0.5,
            n_layers=2,
            save_file='sentiment/saved_models/sentiment',
            param_pickle='sentiment/saved_models/sentiment_params.pkl'):
        self._is_train = is_train
        self._word_map = word_map
        self._batch_size = batch_size if is_train else 1
        self._save_file = save_file
        self._param_pickle = param_pickle
        self._build_model(embedding_shape=embedding_shape,
                          max_len=max_len,
                          hidden_units=hidden_units,
                          dropout_prob=dropout_prob,
                          n_layers=n_layers,
                          initial_embed=initial_embed)

    def _build_model(self, embedding_shape, max_len, hidden_units, dropout_prob, n_layers, initial_embed):
        if initial_embed is not None:
            self._embedding = tf.get_variable('embedding', initializer=tf.constant(initial_embed, dtype=tf.float32))
        else:
            self._embedding = tf.get_variable('embedding', shape=embedding_shape)

        self._input_placeholder = tf.placeholder(
            tf.int32,
            shape=(self._batch_size, max_len),
            name='input_placeholder')

        self._label_placeholder = tf.placeholder(
            tf.int64,
            shape=self._batch_size,
            name='label_placeholder')

        self._length_placeholder = tf.placeholder(
            tf.int32,
            shape=self._batch_size,
            name='length_placeholder')

        inputs = tf.nn.embedding_lookup(self._embedding, self._input_placeholder)

        cell = tf.nn.rnn_cell.LSTMCell(hidden_units, forget_bias=1.0, state_is_tuple=True, use_peepholes=True)
        if self._is_train:
            cell = tf.nn.rnn_cell.DropoutWrapper(cell, output_keep_prob=1 - dropout_prob)
        cell = tf.nn.rnn_cell.MultiRNNCell([cell] * n_layers, state_is_tuple=True)
        initial_state = cell.zero_state(self._batch_size, tf.float32)
        outputs, state = tf.nn.dynamic_rnn(cell, inputs, sequence_length=self._length_placeholder, initial_state=initial_state)
        outputs = tf.reshape(outputs, (-1, hidden_units))
        if self._is_train:
            indices = tf.range(self._batch_size) * max_len + tf.to_int32(self._length_placeholder) - 1
        else:
            indices = self._length_placeholder - 1
        outputs = tf.gather(outputs, indices)

        softmax_w = tf.get_variable('W', shape=(hidden_units, N_CLASSES), dtype=tf.float32)
        softmax_b = tf.get_variable('b', shape=N_CLASSES, dtype=tf.float32)
        logits = tf.matmul(outputs, softmax_w) + softmax_b
        self._softmax_output = tf.nn.softmax(logits)
        self._preds = tf.argmax(logits, 1)
        self._loss = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(logits, self._label_placeholder))
        self._accuracy = tf.contrib.metrics.accuracy(self._preds, self._label_placeholder)

        self._saver = tf.train.Saver()
        if not self._is_train:
            return

        optimizer = tf.train.AdamOptimizer()
        self._train_op = optimizer.minimize(self._loss)

    def _run_epoch(self, session, dataset, epoch_num, train=True):
        total_loss = 0
        total_accuracy = 0
        count = 0
        for i, (data, labels, lengths) in enumerate(dataset.batches(self._batch_size, train=train)):
            batch_start = time.time()
            feed_dict = {
                self._input_placeholder: data,
                self._label_placeholder: labels,
                self._length_placeholder: lengths
            }

            fetches = (self._loss, self._accuracy) + ((self._train_op,) if train else ())
            loss, accuracy, *_ = session.run(fetches, feed_dict=feed_dict)
            total_accuracy += accuracy
            total_loss += loss
            count += 1
            print('{} Epoch: {} Batch: {} Loss: {:.5f} Accuracy: {:.5f} Duration: {:.4f}'.format(
                    'Train' if train else 'Val', epoch_num, i, loss, accuracy, time.time() - batch_start))

        return total_loss/count, total_accuracy/count

    def train(self, session, dataset, max_epochs=50):
        best_acc = 0
        session.run(tf.initialize_all_variables())
        for i in range(max_epochs):
            train_start = time.time()
            train_loss, train_acc = self._run_epoch(session, dataset, epoch_num=i, train=True)
            print('Train Epoch: {} Loss: {:.5f} Accuracy: {:.5f} Duration: {:.2f}'.format(
                    i, train_loss, train_acc, time.time() - train_start))
            val_start = time.time()
            val_loss, val_acc = self._run_epoch(session, dataset, epoch_num=i, train=False)
            print('Val Epoch: {} Loss: {:.5f} Accuracy: {:.5f} Duration: {:.2f}'.format(
                    i, val_loss, val_acc, time.time() - val_start))
            if val_acc > best_acc:
                print('New best accuracy, saving model to', self._save_file)
                best_acc = val_acc
                self._saver.save(session, self._save_file)
                with open(self._param_pickle, 'wb') as f:
                    pickle.dump((self._embedding.get_shape(), self._word_map), f)

    def predict(self, session, text):
        vec = ([self._word_map[START_TOKEN]] +
               [self._word_map[w] if w in self._word_map else self._word_map[UNK_TOKEN] for w in dataset.preprocess(text)] +
               [self._word_map[END_TOKEN]])

        feed_dict = {
            self._input_placeholder: np.expand_dims(vec, 0),
            self._length_placeholder: [len(vec)]
        }
        return session.run(self._softmax_output, feed_dict=feed_dict)[0]

    @property
    def saver(self):
        return self._saver


def load_model(session, save_file='sentiment/saved_models/sentiment', param_pickle='sentiment/saved_models/sentiment_params.pkl'):
    with tf.variable_scope('model', reuse=None):
        with open(param_pickle, 'rb') as f:
            embedding_shape, word_map = pickle.load(f)
        model = SentimentLSTM(embedding_shape=embedding_shape, save_file=save_file, is_train=False, word_map=word_map)
        model.saver.restore(session, save_file)
    return model


def main():
    word_map, embedding = _load_embeddings()
    print('Loading data')
    train_data = dataset.Dataset(TRAIN_FILE, word_map)
    init_scale = 0.08
    with tf.Graph().as_default(), tf.Session() as session:
        with tf.variable_scope('model',
                               reuse=None,
                               initializer=tf.random_uniform_initializer(minval=-init_scale, maxval=init_scale)):
            print('Building model')
            model = SentimentLSTM(embedding_shape=None, initial_embed=embedding, max_len=train_data.max_len, word_map=word_map)
        model.train(session, train_data)

if __name__ == '__main__':
    main()
