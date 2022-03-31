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

import platform
import sys
import time

import tensorflow as tf
import tensorflow_addons as tfa
import cv2

import card_recognizer
import transform
import prof_timer
import common


class Sorter:
    """Provides an interface to the Arduino and camera hardware."""
    def __init__(self, config, catalog, card_lookup):
        config = config
        # Generate the vector used for the perspective transform.
        self.transform_vector = transform.keypoints_to_transform(
            640, 448, *config.camera_keypoints)
        self.card_lookup = card_lookup
        print('Initializing recognizer.')
        self.recognizer = card_recognizer.Recognizer(catalog)

        print('Creating camera.')
        if platform.system() == 'Windows':
            # On Windows, the DirectShow interface seems to be faster and
            # more reliable
            print('Using DirectShow')
            self.vc = cv2.VideoCapture(config.camera_id, cv2.CAP_DSHOW)
        else:
            self.vc = cv2.VideoCapture(config.camera_id)
        self.vc.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.vc.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        print('Opening camera.')
        if not self.vc.isOpened():
            print('Failed to open camera.')
            sys.exit()

        self.serial_port = common.open_device(config)
        common.send_command(self.serial_port, 'start')

    def __del__(self):
        self.vc.release()
        self.serial_port.close()

    def get_camera_image(self):
        # For reasons I haven't diagnosed, the camera seems to lag very far
        # behind reality. Through experimentation I've found that I have to
        # wait for the 6th frame for things to have settled down.
        for i in range(6):
            rval, frame = self.vc.read()
            if not rval:
                print('Error code on frame capture.')
                sys.exit()

        # The image comes from the camera in BGR byte order and we need it
        # in RGB.
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Perform the perspective transform.
        image = tfa.image.transform(frame,
                                    self.transform_vector,
                                    interpolation='bilinear',
                                    fill_value=255,
                                    output_shape=(448, 640))
        # I'm not sure if brightness and contrast adjustment is needed.
        # Further experiments are needed to determine if this helps recognition
        # accuracy.
        image, _, _ = transform.automatic_brightness_and_contrast(
            tf.image.convert_image_dtype(image, tf.uint8).numpy())
        image = tf.image.convert_image_dtype(image, tf.float32)
        # The camera is mounted so the images come in sideways. Rotate them 90
        # degrees.
        image = tf.image.rot90(image, k=1)
        return image

    def identify_next(self):
        common.send_command(self.serial_port, 'next_card')
        # The Arduino sends its "done" reply when the tray sensors have been
        # triggered, but the card will still be in motion for a little while.
        time.sleep(.3)
        image = self.get_camera_image()
        with prof_timer.PerfTimer('recognize'):
            card_id, distance = self.recognizer.recognize(image)
        return card_id

    def send_left(self):
        common.send_command(self.serial_port, 'send_left')

    def send_right(self):
        common.send_command(self.serial_port, 'send_right')

    def reload(self):
        while not self.is_hopper_reloaded():
            input('Reload the hopper and press Enter...')
        common.send_command(self.serial_port, 'reset_hopper')

    def is_hopper_empty(self):
        result, _ = common.send_command(self.serial_port, 'is_hopper_empty')
        return result == 'empty'

    def is_hopper_reloaded(self):
        result, _ = common.send_command(self.serial_port, 'is_hopper_reloaded')
        print(f'Reload result: {result}')
        return result == 'not_empty'

    def print(self):
        pass
