from itertools import chain
import logging
import pickle
import time

import sentiment.data as data

import numpy as np
import tensorflow as tf
from tensorflow.python.client import timeline

N_CLASSES = 3

logger = logging.getLogger(__name__)

def make_iterator(x, y, lens, batch_size, is_train):
    def data_gen():
        for row in x:
            yield np.array(row)

    seq_dataset = tf.data.Dataset.from_generator(data_gen, tf.int64, output_shapes=[None])
    y_dataset = tf.data.Dataset.from_tensor_slices(y)

    dataset = tf.data.Dataset.zip((seq_dataset, y_dataset))

    def mask(ex):
        return tf.ones_like(ex, dtype=tf.int64)
    dataset = dataset.map(lambda ex, y: {'sent': ex, 'mask': mask(ex), 'label': y}).prefetch(batch_size * 100)

    if is_train:
        dataset = dataset.shuffle(buffer_size=100000)
    dataset = dataset.padded_batch(batch_size, padded_shapes=({'sent': [None], 'mask': [None], 'label': ()}))
    data_iter = dataset.make_initializable_iterator()
    return data_iter

def dan(word_vecs, masks, is_train, layers=3, hidden_units=300, dropout_keep_prob=0.5):
    with tf.variable_scope('dan'):
        casted_mask = tf.cast(masks, tf.float32)
        layer_out = tf.reduce_sum(word_vecs * tf.expand_dims(casted_mask, 2), axis=1) / tf.expand_dims(tf.reduce_sum(casted_mask, axis=1), 1)
        for l in range(layers):
            if is_train:
                layer_out = tf.nn.dropout(layer_out, dropout_keep_prob)
            next_shape = hidden_units if l < layers - 1 else N_CLASSES
            W = tf.get_variable(
                name='W{}'.format(l),
                shape=(layer_out.get_shape()[-1], next_shape),
                dtype=tf.float32)

            b = tf.get_variable(
                name='b{}'.format(l),
                shape=(next_shape),
                dtype=tf.float32,
                initializer=tf.zeros_initializer())
            layer_out = layer_out @ W + b
            if l < layers - 1:
                layer_out = tf.nn.relu(layer_out)

    return layer_out

def make_model(data_iter=None, init_embeddings=None, embedding_shape=None, is_train=True, is_test=False, use_dan=True):
    model = {}
    with tf.variable_scope('input'):
        if not is_test:
            inputs = data_iter.get_next()
            sent_in = inputs['sent']
            masks = inputs['mask']
            model['labels'] = inputs['label']
        else:
            sent_in = tf.placeholder(tf.int64, shape=(None, None), name='input_placeholder')
            model['input'] = sent_in
            masks = tf.ones_like(sent_in, dtype=tf.int64)

        embeddings = tf.get_variable(
            name='embedding_matrix',
            initializer=init_embeddings if not is_test else None,
            dtype=tf.float32,
            shape=None if not is_test else embedding_shape)

        vecs = tf.nn.embedding_lookup(params=embeddings, ids=sent_in)

    with tf.variable_scope('net', initializer=tf.contrib.layers.xavier_initializer()):
        if use_dan:
            logits = dan(vecs, masks, is_train=is_train)
            model['logits'] = logits

    with tf.variable_scope('output'):
        model['softmax'] = tf.nn.softmax(logits=logits, dim=1)
        model['predictions'] = tf.argmax(logits, axis=1)
        if not is_test:
            loss = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(labels=inputs['label'], logits=logits))
            if is_train:
                model['train'] = tf.train.AdamOptimizer(learning_rate=3e-4).minimize(loss)

    return model

def accuracy(predictions, labels):
    return np.mean(predictions == labels)

def load_model(session):
    with open(data.EMBEDDING_PICKLE, 'rb') as f:
        embeddings, word_map = pickle.load(f)
    with tf.variable_scope('model'):
        model = make_model(is_test=True, embedding_shape=embeddings.shape, is_train=False)
    saver = tf.train.Saver(tf.trainable_variables())
    session.run(tf.global_variables_initializer())
    saver.restore(session, 'sentiment/saved_models/model.ckpt')
    return model, word_map

def predict(model, session, word_map, text):
    sent = data.preprocess(text)
    indices = np.array([word_map.get(w, word_map[data.UNK_TOKEN]) for w in chain([data.START_TOKEN], sent, [data.END_TOKEN])]).astype(np.int64)
    return session.run(model['softmax'], feed_dict={model['input']: np.expand_dims(indices, 0)})[0]

def main():
    rootLogger = logging.getLogger('')
    rootLogger.setLevel(logging.INFO)
    handler = logging.FileHandler('output/log.txt')
    handler.setLevel(logging.INFO)
    rootLogger.addHandler(handler)

    batch_size = 256
    max_epochs = 60
    patience = 15

    logger.info('Loading data')
    init_embeddings, word_map, train_x, train_y, train_lens, val_x, val_y, val_lens = data.load_dataset()
    with tf.Graph().as_default():
        train_iter = make_iterator(train_x, train_y, train_lens, batch_size=batch_size, is_train=True)
        val_iter = make_iterator(val_x, val_y, val_lens, batch_size=128, is_train=False)

        with tf.variable_scope('model'):
            train_model = make_model(train_iter, init_embeddings)
        train_fetches = {k: train_model[k] for k in ['predictions', 'labels', 'train']}
        saver = tf.train.Saver(tf.trainable_variables())

        with tf.variable_scope('model', reuse=True):
            val_model = make_model(val_iter, is_train=False)

        best_val_accuracy = 0
        last_improvement = -1

        with tf.Session() as sess:
            sess.run(tf.global_variables_initializer())

            for epoch in range(max_epochs):
                start = time.time()
                accs = []
                sess.run(train_iter.initializer)
                logger.info('%0.2f seconds to initialize train_iter', time.time() - start)
                batches = 0
                while True:
                    try:
                        results = sess.run(train_fetches)
                        accs.append(accuracy(results['predictions'], results['labels']))
                        batches += 1
                    except tf.errors.OutOfRangeError:
                        break

                logger.info('Epoch {}- Accuracy: {:0.4f} {} batches in {:0.2f} seconds'.format(epoch, np.mean(accs), batches, time.time() - start))

                sess.run(val_iter.initializer)
                accs = []
                while True:
                    try:
                        results = sess.run(val_model)
                        accs.append(accuracy(results['predictions'], results['labels']))
                    except tf.errors.OutOfRangeError:
                        break
                val_acc = np.mean(accs)
                logger.info('Epoch {} - Val Accuracy: {:0.4f}'.format(epoch, val_acc))
                if val_acc > best_val_accuracy:
                    best_val_accuracy = val_acc
                    last_improvement = epoch
                    logger.info('Improved accuracy, saving.')
                    saver.save(sess, 'sentiment/saved_models/model.ckpt')

                elif epoch - last_improvement > patience:
                    logger.info('Patience exceeded, halting')

if __name__ == '__main__':
    main()
