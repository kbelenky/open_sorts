# Copyright 2022 Kennet Belenky
#
# This file is part of OpenSorts.
#
# OpenSorts is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# OpenSorts is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# OpenSorts. If not, see <https://www.gnu.org/licenses/>.

import cv2
import tensorflow as tf
import numpy as np
import tensorflow_addons as tfa


def single_heatmap(length, start, stop, jpeg_file):
    # Provides a 1d heatmap for a single edge.
    # The resulting heatmap will be of size 1 x length.
    # Elements between `start` and `stop` inclusive will be 1.0
    # All other elements will be -1.0
    tf.debugging.assert_greater_equal(start, 0, message=jpeg_file)
    tf.debugging.assert_greater_equal(stop - start, 0, message=jpeg_file)
    tf.debugging.assert_greater_equal(length - stop, 0, message=jpeg_file)
    return tf.concat([
        -1 * tf.ones(start),
        tf.ones(stop - start), -1 * tf.ones(length - stop)
    ],
                     axis=0)


def build_heatmap(jpeg, corners, jpeg_file):
    # Takes a jpeg, a corners array, and the name of jpeg file, and
    # maps the corners array into a heatmap that is the concatenation
    # of the four individual heatmaps (top edge, bottom edge, left edge
    # right edge).
    #
    # The jpeg and jpeg_file name are passed through unmodified.
    shape = tf.shape(jpeg)
    width = shape[1]
    height = shape[0]
    return tf.concat(
        [
            # top edge heatmap
            single_heatmap(width, corners[0][0], corners[1][0], jpeg_file),
            # bottom edge heatmap
            single_heatmap(width, corners[3][0], corners[2][0], jpeg_file),
            # left edge heatmap
            single_heatmap(height, corners[0][1], corners[3][1], jpeg_file),
            # right edge heatmap
            single_heatmap(height, corners[1][1], corners[2][1], jpeg_file)
        ],
        axis=0)


def valid_corners(jpeg, corners):
    # Tests if the corners of the corners array are organized clockwise
    # from the top left.
    shape = tf.shape(jpeg)
    width = shape[1]
    height = shape[0]

    def is_valid(value, limit):
        return tf.math.logical_and(tf.math.greater_equal(value, 0),
                                   tf.math.less(value, limit))

    def point_is_valid(point, w, h):
        return tf.math.logical_and(is_valid(point[0], w),
                                   is_valid(point[1], h))

    rows = tf.unstack(corners, num=4)
    return tf.math.logical_and(
        tf.math.logical_and(point_is_valid(rows[0], width, height),
                            point_is_valid(rows[1], width, height)),
        tf.math.logical_and(point_is_valid(rows[2], width, height),
                            point_is_valid(rows[3], width, height)))


def heatmap_to_range(heatmap):
    # Converts a 1d heatmap back into an index range.
    end = np.argmax(
        np.convolve(heatmap + 1, [-1, -1, -1, -1, -1, 1, 1, 1, 1, 1],
                    mode='same'))
    start = np.argmax(
        np.convolve(heatmap + 1, [1, 1, 1, 1, 1, -1, -1, -1, -1, -1],
                    mode='same'))
    return start, end


def heatmap_to_corners(shape, heatmap):
    # Converts the four concatenated heatmaps back into corner coordinates.
    width = shape[1]
    height = shape[0]
    tl_x, tr_x = heatmap_to_range(heatmap[0:width])
    bl_x, br_x = heatmap_to_range(heatmap[width:width * 2])
    tl_y, bl_y = heatmap_to_range(heatmap[width * 2:width * 2 + height])
    tr_y, br_y = heatmap_to_range(heatmap[width * 2 + height:width * 2 +
                                          height * 2])
    return np.array([(tl_x, tl_y), (tr_x, tr_y), (br_x, br_y), (bl_x, bl_y)],
                    dtype=np.int32)


def draw_outline(frame, corners):
    # Draws the outlines of the corners on a numpy array in green lines.
    cv2.line(frame, (corners[0][0], corners[0][1]),
             (corners[1][0], corners[1][1]), (0, 255, 0),
             thickness=3)
    cv2.line(frame, (corners[1][0], corners[1][1]),
             (corners[2][0], corners[2][1]), (0, 255, 0),
             thickness=3)
    cv2.line(frame, (corners[2][0], corners[2][1]),
             (corners[3][0], corners[3][1]), (0, 255, 0),
             thickness=3)
    cv2.line(frame, (corners[3][0], corners[3][1]),
             (corners[0][0], corners[0][1]), (0, 255, 0),
             thickness=3)
    return frame


def random_flip_x(frame, corners, jpeg_file):
    # Randomly flips the x-axis of the image.
    # If the image is flipped, the corners array will be rearranged to match.
    shape = tf.shape(frame)
    width = shape[1] - 1
    invert = tf.concat(
        (-1 * tf.ones([4, 1], dtype=tf.int32), tf.ones([4, 1],
                                                       dtype=tf.int32)), 1)
    addition = tf.concat((width * tf.ones([4, 1], dtype=tf.int32),
                          tf.zeros([4, 1], dtype=tf.int32)), 1)
    rows = tf.unstack(tf.math.multiply(corners, invert) + addition, num=4)
    inverted_corners = tf.stack((rows[1], rows[0], rows[3], rows[2]))
    return tf.cond(
        tf.random.uniform(shape=[], minval=0, maxval=1) > 0.5, lambda:
        (tf.image.flip_left_right(frame), inverted_corners, jpeg_file), lambda:
        (frame, corners, jpeg_file))


def random_flip_y(frame, corners, jpeg_file):
    # Randomly flips the y-axis of the image.
    # If the image is flipped, the corners array will be rearranged to match.
    shape = tf.shape(frame)
    height = shape[0] - 1
    invert = tf.concat((tf.ones(
        [4, 1], dtype=tf.int32), -1 * tf.ones([4, 1], dtype=tf.int32)), 1)
    addition = tf.concat((tf.zeros(
        [4, 1], dtype=tf.int32), height * tf.ones([4, 1], dtype=tf.int32)), 1)
    rows = tf.unstack(tf.math.multiply(corners, invert) + addition, num=4)
    inverted_corners = tf.stack((rows[3], rows[2], rows[1], rows[0]))
    return tf.cond(
        tf.random.uniform(shape=[], minval=0, maxval=1) > 0.5, lambda:
        (tf.image.flip_up_down(frame), inverted_corners, jpeg_file), lambda:
        (frame, corners, jpeg_file))


def heatmap_dataset():
    # Loads the heatmap dataset and applies the augmentation and filters
    # and converts the corners into a heatmap.
    list_ds = tf.data.experimental.load('datasets/corners.dataset')
    list_ds = list_ds.map(random_flip_x)
    list_ds = list_ds.map(random_flip_y)
    list_ds = list_ds.filter(
        lambda frame, corners, jpeg_file: valid_corners(frame, corners))
    list_ds = list_ds.map(lambda frame, corners, jpeg_file: (
        frame, build_heatmap(frame, corners, jpeg_file), jpeg_file))
    return list_ds
