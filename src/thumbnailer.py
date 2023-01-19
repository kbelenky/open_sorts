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
import numpy as np
import tensorflow as tf
import tensorflow_addons as tfa
import transform


def heatmap_to_range(heatmap):
    end = np.argmax(
        np.convolve(heatmap + 1, [-1, -1, -1, -1, -1, 1, 1, 1, 1, 1],
                    mode='same'))
    start = np.argmax(
        np.convolve(heatmap + 1, [1, 1, 1, 1, 1, -1, -1, -1, -1, -1],
                    mode='same'))
    return start, end


def heatmap_to_corners(shape, heatmap):
    width = shape[1]
    height = shape[0]
    tl_x, tr_x = heatmap_to_range(heatmap[0:width])
    bl_x, br_x = heatmap_to_range(heatmap[width:width * 2])
    tl_y, bl_y = heatmap_to_range(heatmap[width * 2:width * 2 + height])
    tr_y, br_y = heatmap_to_range(heatmap[width * 2 + height:width * 2 +
                                          height * 2])
    return np.array([(tl_x, tl_y), (tr_x, tr_y), (br_x, br_y), (bl_x, bl_y)],
                    dtype=np.int32)


class Thumbnailer:

    def __init__(self):
        self.interpreter = tf.lite.Interpreter(model_path='corners.tflite')
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()[0]
        self.output_details = self.interpreter.get_output_details()[0]

    def get_card_corners(self, input_image):
        input_image = cv2.resize(input_image, (320, 192),
                                 interpolation=cv2.INTER_AREA)
        input_image = np.expand_dims(input_image, axis=0).astype(np.single)
        input_image = (input_image * 2 / 255) - 1
        self.interpreter.set_tensor(self.input_details['index'], input_image)
        self.interpreter.invoke()
        heatmap = self.interpreter.get_tensor(self.output_details["index"])[0]
        corners = heatmap_to_corners((192, 320), heatmap)
        corners[0][0] = corners[0][0] * 1280 / 320
        corners[1][0] = corners[1][0] * 1280 / 320
        corners[2][0] = corners[2][0] * 1280 / 320
        corners[3][0] = corners[3][0] * 1280 / 320
        corners[0][1] = corners[0][1] * 720 / 192
        corners[1][1] = corners[1][1] * 720 / 192
        corners[2][1] = corners[2][1] * 720 / 192
        corners[3][1] = corners[3][1] * 720 / 192
        return corners

    def thumbnail(self, input_image):
        corners = self.get_card_corners(input_image)
        # The corner keypoints are in a different order for the recognizer than
        # they are in keypoints_to_transform, so we have to reorder them.
        transform_vector = transform.keypoints_to_transform(
            640, 448, *corners[[0, 1, 3, 2]])
        thumbnail = tfa.image.transform(input_image,
                                        transform_vector,
                                        interpolation='bilinear',
                                        fill_value=255,
                                        output_shape=(448, 640))
        return thumbnail, corners
