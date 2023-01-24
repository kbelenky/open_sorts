# Copyright 2023 Kennet Belenky
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

import json

import tensorflow as tf
import numpy as np

list_ds = tf.data.Dataset.list_files('scans/*.jpg')


def tag_exists(jpeg_file):
    tag_file = tf.strings.regex_replace(jpeg_file, 'jpg$', 'json')
    exists = tf.io.gfile.exists(tag_file.numpy())
    return exists


def load_corners(tag_file, image_shape):
    corners = np.array(json.loads(
        tf.io.read_file(tag_file).numpy().decode("utf-8")),
                       dtype=np.int32)
    scale = np.array([image_shape[1] / 1280, image_shape[0] / 720],
                     dtype=np.float32)
    return np.multiply(corners, scale).astype(np.int32)


def load_jpeg(filename):
    image = tf.io.read_file(filename)
    image = tf.io.decode_jpeg(image)
    image = tf.image.convert_image_dtype(image, tf.float32)
    image = tf.image.resize(image, (192, 320), antialias=True)
    image = tf.image.convert_image_dtype(image, tf.uint8)
    return image


list_ds = list_ds.filter(
    lambda jpeg_file: tf.numpy_function(tag_exists, [jpeg_file], tf.bool))
list_ds = list_ds.map(lambda jpeg_file: (
    jpeg_file, tf.strings.regex_replace(jpeg_file, 'jpg$', 'json')))
list_ds = list_ds.map(lambda jpeg_file, corners:
                      (load_jpeg(jpeg_file), corners, jpeg_file))
list_ds = list_ds.map(lambda jpeg, tag_file, jpeg_file: (
    jpeg, tf.numpy_function(load_corners, [tag_file, tf.shape(jpeg)], tf.int32
                            ), jpeg_file))

tf.data.experimental.save(list_ds, 'datasets/corners.dataset')
