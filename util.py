#!/usr/bin/env python
import tensorflow as tf
import random
import tables
import numpy as np
import matplotlib.pyplot as plt
import os
from math import sqrt

try:
    import cPickle as pickle
except ImportError:
    import pickle

def graves_rmsprop_optimizer(loss, learning_rate, rmsprop_decay, rmsprop_constant, gradient_clip):
    """
    src:https://raw.githubusercontent.com/cgel/DRL/master/agents/commonOps.py
    """
    with tf.name_scope('rmsprop'):
        optimizer = None
        optimizer = tf.train.GradientDescentOptimizer(learning_rate)

        grads_and_vars = optimizer.compute_gradients(loss)

        grads = []
        params = []
        for p in grads_and_vars:
            if p[0] == None:
                continue
            grads.append(p[0])
            params.append(p[1])
        #grads = [gv[0] for gv in grads_and_vars]
        #params = [gv[1] for gv in grads_and_vars]
        if gradient_clip > 0:
            grads = tf.clip_by_global_norm(grads, gradient_clip)[0]

        square_grads = [tf.square(grad) for grad in grads]

        avg_grads = [tf.Variable(tf.zeros(var.get_shape()))
                     for var in params]
        avg_square_grads = [tf.Variable(
            tf.zeros(var.get_shape())) for var in params]

        update_avg_grads = [grad_pair[0].assign((rmsprop_decay * grad_pair[0]) + tf.scalar_mul((1 - rmsprop_decay), grad_pair[1]))
                            for grad_pair in zip(avg_grads, grads)]
        update_avg_square_grads = [grad_pair[0].assign((rmsprop_decay * grad_pair[0]) + ((1 - rmsprop_decay) * tf.square(grad_pair[1])))
                                   for grad_pair in zip(avg_square_grads, grads)]
        avg_grad_updates = update_avg_grads + update_avg_square_grads

        rms = [tf.sqrt(avg_grad_pair[1] - tf.square(avg_grad_pair[0]) + rmsprop_constant)
               for avg_grad_pair in zip(avg_grads, avg_square_grads)]

        rms_updates = [grad_rms_pair[0] / grad_rms_pair[1]
                       for grad_rms_pair in zip(grads, rms)]
        train = optimizer.apply_gradients(zip(rms_updates, params))

        return tf.group(train, tf.group(*avg_grad_updates)), grads_and_vars

def egreedy(readout_t, n_actions=-1):
    assert n_actions > 1
    best_indices = [0]
    max_action = readout_t[0]
    for index in range(1, n_actions):
        if readout_t[index] > max_action:
            best_indices = [index]
            max_action = readout_t[index]
        elif readout_t[index] == max_action:
            best_indices.append(index)
    action_index = random.choice(best_indices)
    return action_index

def get_action_index(readout_t, is_random=False, n_actions=-1):
    assert n_actions > 1
    action_index = 0
    if is_random:
        action_index = random.randrange(n_actions)
    else:
        action_index = egreedy(readout_t, n_actions)
    return action_index

def plot_conv_weights(weights, name, channels_all=True, folder=''):
    """
    Plots convolutional filters
    :param weights: numpy array of rank 4
    :param name: string, name of convolutional layer
    :param channels_all: boolean, optional
    :return: nothing, plots are saved on the disk
    :src: https://github.com/grishasergei/conviz/blob/master/conviz.py
    """
    if folder != '':
        folder = folder + "/plots"
    else:
        folder = "./plots"
    # make path to output folder
    plot_dir = os.path.join(folder, 'conv_weights')
    plot_dir = os.path.join(plot_dir, name)

    # create directory if does not exist, otherwise empty it
    prepare_dir(plot_dir, empty=True)

    w_min = np.min(weights)
    w_max = np.max(weights)

    channels = [0]
    # make a list of channels if all are plotted
    if channels_all:
        channels = range(weights.shape[2])

    # get number of convolutional filters
    num_filters = weights.shape[3]

    # get number of grid rows and columns
    grid_r, grid_c = get_grid_dim(num_filters)

    # create figure and axes
    #fig, axes = plt.subplots(min([grid_r, grid_c]),
    #                         max([grid_r, grid_c]))

    # iterate channels
    for channel in channels:
        # create figure and axes
        fig, axes = plt.subplots(min([grid_r, grid_c]),
                                 max([grid_r, grid_c]))
        # iterate filters inside every channel
        for l, ax in enumerate(axes.flat):
            # get a single filter
            img = weights[:, :, channel, l]
            # put it on the grid
            ax.imshow(img, vmin=w_min, vmax=w_max, interpolation='nearest', cmap='seismic')
            # remove any labels from the axes
            ax.set_xticks([])
            ax.set_yticks([])
        # save figure
        fig.savefig(os.path.join(plot_dir, '{}-{}.png'.format(name, channel)), bbox_inches='tight')
        plt.close(fig)

def plot_conv_output(conv_img, name, folder=''):
    """
    Makes plots of results of performing convolution
    :param conv_img: numpy array of rank 4
    :param name: string, name of convolutional layer
    :return: nothing, plots are saved on the disk
    :src: https://github.com/grishasergei/conviz/blob/master/conviz.py
    """
    if folder != '':
        folder = folder + "/plots"
    else:
        folder = "./plots"
    # make path to output folder
    plot_dir = os.path.join(folder, 'conv_output')
    plot_dir = os.path.join(plot_dir, name)

    # create directory if does not exist, otherwise empty it
    prepare_dir(plot_dir, empty=True)

    w_min = np.min(conv_img)
    w_max = np.max(conv_img)

    # get number of convolutional filters
    num_filters = conv_img.shape[3]

    # get number of grid rows and columns
    grid_r, grid_c = get_grid_dim(num_filters)

    # create figure and axes
    fig, axes = plt.subplots(min([grid_r, grid_c]),
                             max([grid_r, grid_c]))

    # iterate filters
    for l, ax in enumerate(axes.flat):
        # get a single image
        img = conv_img[0, :, :,  l]
        # put it on the grid
        ax.imshow(img, vmin=w_min, vmax=w_max, interpolation='bicubic', cmap='Greys')
        # remove any labels from the axes
        ax.set_xticks([])
        ax.set_yticks([])
    # save figure
    plt.savefig(os.path.join(plot_dir, '{}.png'.format(name)), bbox_inches='tight')

def get_grid_dim(x):
    """
    Transforms x into product of two integers
    :param x: int
    :return: two ints
    :src: https://github.com/grishasergei/conviz/blob/master/utils.py
    """
    factors = prime_powers(x)
    if len(factors) % 2 == 0:
        i = int(len(factors) / 2)
        return factors[i], factors[i - 1]

    i = len(factors) // 2
    return factors[i], factors[i]


def prime_powers(n):
    """
    Compute the factors of a positive integer
    Algorithm from https://rosettacode.org/wiki/Factors_of_an_integer#Python
    :param n: int
    :return: set
    :src: https://github.com/grishasergei/conviz/blob/master/utils.py
    """
    factors = set()
    for x in range(1, int(sqrt(n)) + 1):
        if n % x == 0:
            factors.add(int(x))
            factors.add(int(n // x))
    return sorted(factors)


def empty_dir(path):
    """
    Delete all files and folders in a directory
    :param path: string, path to directory
    :return: nothing
    :src: https://github.com/grishasergei/conviz/blob/master/utils.py
    """
    for the_file in os.listdir(path):
        file_path = os.path.join(path, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print ('Warning: {}'.format(e))


def create_dir(path):
    """
    Creates a directory
    :param path: string
    :return: nothing
    :src: https://github.com/grishasergei/conviz/blob/master/utils.py
    """
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise


def prepare_dir(path, empty=False):
    """
    Creates a directory if it soes not exist
    :param path: string, path to desired directory
    :param empty: boolean, delete all directory content if it exists
    :return: nothing
    :src: https://github.com/grishasergei/conviz/blob/master/utils.py
    """
    if not os.path.exists(path):
        create_dir(path)

    if empty:
        empty_dir(path)
