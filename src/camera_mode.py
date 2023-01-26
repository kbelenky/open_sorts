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
import pygame
import numpy as np
import sys
import platform
import uuid

import tensorflow as tf
import tensorflow_addons as tfa
import transform

from pygame import display
import card_recognizer
import common
import thumbnailer


def cvimage_to_pygame(image):
    """Convert cvimage into a pygame image"""
    return pygame.image.frombuffer(image.tobytes(), image.shape[1::-1], "RGB")


print('Loading config')
config = common.load_config()
print('Loading catalog')
catalog, cards_by_id = common.load_catalog()
print('Initializing recognizer.')
recognizer = card_recognizer.Recognizer(catalog)

print('Initializing Corner Detector.')
corner_detector = thumbnailer.Thumbnailer()

pygame.init()

surface = display.set_mode(size=(1280, 720))

print('Creating camera.')
if platform.system() == 'Windows':
    # On Windows, the DirectShow interface seems to be faster and
    # more reliable
    print('Using DirectShow')
    vc = cv2.VideoCapture(config.camera_id, cv2.CAP_DSHOW)
else:
    vc = cv2.VideoCapture(config.camera_id)
vc.set(cv2.CAP_PROP_BUFFERSIZE, 1)
vc.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
vc.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
print('Opening camera.')
if not vc.isOpened():
    print('Failed to open camera.')
    sys.exit()

font = pygame.font.Font(pygame.font.get_default_font(), 32)

running = True
while running:
    # Grab the next frame.
    rval, frame = vc.read()
    if not rval:
        print('Error code on frame capture.')
        running = False
        continue
    # Convert the frame to the RGB color space.
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Model processing
    cropped, corners = corner_detector.thumbnail(frame)

    cropped = tf.image.rot90(cropped, k=1)
    cropped = tf.image.convert_image_dtype(cropped, tf.float32)
    card_id, distance = recognizer.recognize(cropped)
    card_text = (
        f'{cards_by_id[card_id]["name"]}[{cards_by_id[card_id]["set"]}]' +
        f' : {distance:.2f}')
    print(card_text)

    # Render the bounding quad and recognition info.
    text_surface = font.render(card_text, True, (255, 255, 255))
    text_rect = text_surface.get_rect()
    text_rect.center = (
        (corners[0][0] + corners[1][0] + corners[2][0] + corners[3][0]) / 4,
        (corners[0][1] + corners[1][1] + corners[2][1] + corners[3][1]) / 4)

    surface.blit(cvimage_to_pygame(frame), (0, 0))
    surface.blit(text_surface, text_rect)
    pygame.draw.line(surface, (0, 255, 0), (corners[0][0], corners[0][1]),
                     (corners[1][0], corners[1][1]), 3)
    pygame.draw.line(surface, (0, 255, 0), (corners[1][0], corners[1][1]),
                     (corners[2][0], corners[2][1]), 3)
    pygame.draw.line(surface, (0, 255, 0), (corners[2][0], corners[2][1]),
                     (corners[3][0], corners[3][1]), 3)
    pygame.draw.line(surface, (0, 255, 0), (corners[3][0], corners[3][1]),
                     (corners[0][0], corners[0][1]), 3)

    display.update()

    # If the space bar was hit, then save the frame to the "scans"
    # directory for later tagging.
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_SPACE:
                tf.io.write_file(f'scans/{uuid.uuid1()}_full.jpg',
                                 tf.io.encode_jpeg(frame))

vc.release()
