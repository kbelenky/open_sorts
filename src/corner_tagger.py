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

import os

import json
import pygame
import random
from pygame import display
from pygame import mouse


# Provides a list of all jpg files in the scans directory that don't have
# associated json ground truth annotations.
def files_to_tag():
    result = []
    existing_tags = set([
        file.path for file in os.scandir('scans')
        if file.is_file() and file.name.endswith('.json')
    ])
    for file in os.scandir('scans'):
        if not file.is_file():
            continue
        if not file.name.endswith('.jpg'):
            continue

        tag_file = file.path.replace('.jpg', '.json')
        if tag_file not in existing_tags:
            result.append((file.path, tag_file))
    return result


# Flattens the pygame event stream into a single iterable.
def event_stream():
    while True:
        for event in pygame.event.get():
            yield event


pygame.init()

surface = display.set_mode(size=(1280, 720))

running = True
file_list = files_to_tag()
random.shuffle(file_list)
print(f'Files to tag: {len(file_list)}')
print('Click on the four corners, clockwise, ' +
      'starting from the top-left on screen.')
print()
print('Press <SPACE> when four corners are tagged to save and move on.')
print('Press <ESC> to discard the current corners.')
for file, tag_file in file_list:
    if not running:
        break
    img = pygame.image.load(file)
    display.set_caption(file)
    surface.blit(img, (0, 0))
    display.update()

    corners = []
    for event in event_stream():
        if event.type == pygame.QUIT:
            running = False
            break
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # A corner was tagged. Draw it, and append it to the list.
            x, y = mouse.get_pos()
            print(f'{x}, {y}')
            pygame.draw.rect(surface, (0, 255, 0),
                             pygame.Rect(x - 2, y - 2, 5, 5))
            display.update()
            corners.append((x, y))
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_SPACE:
                # Save the corners and move on to the next file.
                if len(corners) == 4:
                    print(corners)
                    with open(tag_file, 'w') as tag_output:
                        json.dump(corners,
                                  tag_output,
                                  indent=4,
                                  sort_keys=True)
                    break
                else:
                    print('You must have 4 corners tagged to save.')
            elif event.key == pygame.K_ESCAPE:
                # Discard the corners and refresh the display.
                corners = []
                surface.blit(img, (0, 0))
                display.update()
