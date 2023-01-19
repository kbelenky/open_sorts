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
import uuid

import tensorflow as tf
import tensorflow_addons as tfa
import transform

from pygame import display
import corner_dataset
import card_recognizer
import common


def cvimage_to_pygame(image):
    """Convert cvimage into a pygame image"""
    return pygame.image.frombuffer(image.tobytes(), image.shape[1::-1], "RGB")


print('Loading catalog')
catalog, cards_by_id = common.load_catalog()
print('Initializing recognizer.')
recognizer = card_recognizer.Recognizer(catalog)

print('Initializing model.')
interpreter = tf.lite.Interpreter(model_path='corners.tflite')
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()[0]
output_details = interpreter.get_output_details()[0]

pygame.init()

surface = display.set_mode(size=(1280, 720))

print('Creatingcamera.')
vc = cv2.VideoCapture(0, cv2.CAP_DSHOW)
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
    rval, frame = vc.read()
    if not rval:
        print('Error code on frame capture.')
        running = False
        continue
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Model processing
    input_image = frame.copy()
    input_image = cv2.resize(input_image, (320, 192),
                             interpolation=cv2.INTER_AREA)
    input_image = np.expand_dims(input_image, axis=0).astype(np.single)
    input_image = (input_image * 2 / 255) - 1
    interpreter.set_tensor(input_details['index'], input_image)
    interpreter.invoke()
    heatmap = interpreter.get_tensor(output_details["index"])[0]
    corners = corner_dataset.heatmap_to_corners((192, 320), heatmap)
    corners[0][0] = corners[0][0] * 1280 / 320
    corners[1][0] = corners[1][0] * 1280 / 320
    corners[2][0] = corners[2][0] * 1280 / 320
    corners[3][0] = corners[3][0] * 1280 / 320
    corners[0][1] = corners[0][1] * 720 / 192
    corners[1][1] = corners[1][1] * 720 / 192
    corners[2][1] = corners[2][1] * 720 / 192
    corners[3][1] = corners[3][1] * 720 / 192

    transform_vector = transform.keypoints_to_transform(
        640, 448, *corners[[0, 1, 3, 2]])
    cropped = tfa.image.transform(frame,
                                  transform_vector,
                                  interpolation='bilinear',
                                  fill_value=255,
                                  output_shape=(448, 640))
    cropped = tf.image.rot90(cropped, k=1)
    cropped = tf.image.convert_image_dtype(cropped, tf.float32)
    card_id, distance = recognizer.recognize(cropped)
    card_text = f'{cards_by_id[card_id]["name"]}[{cards_by_id[card_id]["set"]}] : {distance:.2f}'
    print(card_text)
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

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_SPACE:
                tf.io.write_file(f'scans/{uuid.uuid1()}_full.jpg',
                                 tf.io.encode_jpeg(frame))

vc.release()
