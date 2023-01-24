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

import tensorflow as tf
import tensorflow.keras.layers as layers
import tensorflow.keras.applications as applications
import numpy as np

import corner_dataset


def adjust_momentum(model):
    # The default version of MobileNetV2 has _really_ high momentum in its
    # BatchNormalization layers. This is fine when training at Google scale,
    # but tends to be a problem with smaller datasets and fewer epochs.
    config = model.to_json()
    config = config.replace('"momentum": 0.99', '"momentum": 0.80')
    return tf.keras.models.model_from_json(config, custom_objects={})


def make_edge_layer(input, size, shape, strides):
    # Collapse one dimension.
    output = layers.Conv2D(128,
                           size,
                           strides=size,
                           padding='same',
                           activation='relu')(input)
    # Upscale 4x in the remaining dimension.
    output = layers.Conv2DTranspose(64,
                                    shape,
                                    strides=strides,
                                    padding='same',
                                    activation='relu')(output)
    output = layers.Conv2DTranspose(32,
                                    shape,
                                    strides=strides,
                                    padding='same',
                                    activation='relu')(output)
    return output


def make_heatmap_layer(input, shape, strides):
    # Finish upscaling back to the original 1d resolution.
    heatmap = layers.Conv2DTranspose(16,
                                     shape,
                                     strides=strides,
                                     padding='same',
                                     activation='relu')(input)
    heatmap = layers.Conv2DTranspose(8,
                                     shape,
                                     strides=strides,
                                     padding='same',
                                     activation='relu')(heatmap)
    heatmap = layers.SpatialDropout2D(0.2)(heatmap)
    # End with a tanh layer to get a nearly binary signal on output.
    heatmap = layers.Conv2D(1, (1, 1),
                            strides=(1, 1),
                            padding='same',
                            activation='tanh')(heatmap)
    heatmap = layers.Flatten()(heatmap)
    return heatmap


def make_heatmap_model():
    # Start with MobileNetV2, but we'll intercept halfway through it.
    model = applications.MobileNetV2(include_top=False,
                                     weights=None,
                                     input_shape=(192, 320, 3),
                                     alpha=1)
    # Adjust the batch normalization momentum to a lower than default value.
    model = adjust_momentum(model)
    # Intercept the outputs of block 12, which is after most of the reduction
    # in image width x height.
    output = model.get_layer('block_12_add').output
    output = layers.SpatialDropout2D(0.2)(output)
    height = output.get_shape()[1]
    width = output.get_shape()[2]

    # Split out the features into 1d horizontal and vertical encodings.
    horizontal = make_edge_layer(output, (height, 1), (1, 3), (1, 2))
    vertical = make_edge_layer(output, (1, width), (3, 1), (2, 1))
    # Upscale back into full-res 1d heatmaps.
    top_heatmap = make_heatmap_layer(horizontal, (1, 3), (1, 2))
    bottom_heatmap = make_heatmap_layer(horizontal, (1, 3), (1, 2))
    left_heatmap = make_heatmap_layer(vertical, (3, 1), (2, 1))
    right_heatmap = make_heatmap_layer(vertical, (3, 1), (2, 1))

    output = layers.Concatenate()(
        [top_heatmap, bottom_heatmap, left_heatmap, right_heatmap])
    model = tf.keras.Model(model.input, output)
    return model


model = make_heatmap_model()
model.compile(optimizer=tf.keras.optimizers.Adam(),
              loss=tf.keras.losses.MeanSquaredError())
print(model.summary())

list_ds = corner_dataset.heatmap_dataset()
list_ds = list_ds.map(
    lambda frame, heatmap, _: (applications.mobilenet_v2.preprocess_input(
        tf.image.convert_image_dtype(frame, tf.float32) * 255), heatmap))
list_ds = list_ds.repeat().shuffle(1000)
list_ds = list_ds.batch(12)

callbacks = []
history = model.fit(list_ds,
                    epochs=15,
                    callbacks=callbacks,
                    steps_per_epoch=300)

model.save('models/corners.model')
converter = tf.lite.TFLiteConverter.from_saved_model('models/corners.model')
tflite_model = converter.convert()
with open('corners.tflite', 'wb') as f:
    f.write(tflite_model)
