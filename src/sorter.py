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

import json
import pickle
import sys
import time

import arduino_device
import sort_cards
import prof_timer
import common


def sort_cards(device, sorter):
    card_count = 0
    while not device.is_hopper_empty():
        card_id = device.identify_next()
        card = cards_by_id[card_id]
        card_name = card['name']
        set_code = card['set']
        direction = sorter.decide_direction(card_id)
        card_count = card_count + 1
        print(f'Recognized: {cards_by_id[card_id]["name"]} ' +
              f'[{cards_by_id[card_id]["set"]}] -> {direction}')
        if direction == 'left':
            device.send_left()
        else:
            device.send_right()
    return card_count


config = common.load_config()

print('Loading catalog')
catalog, cards_by_id = common.load_catalog()
print('Connecting to device')
device = arduino_device.Sorter(config, catalog, cards_by_id)
device.print()

sorter = sort_cards.FirstPassSorter(cards_by_id)
card_count = sort_cards(device, sorter)
device.print()
print(f'Total cards: {card_count}')

sorter = sort_cards.SubsequentPassSorter(cards_by_id, sorter.get_results())
sorter.print_pivots()
while not sorter.is_sorted():
    device.reload()
    sorter.print_pivots()
    sort_cards(device, sorter)
    device.print()
    sorter.reload_hopper()

print('=============== FINAL DEVICE =================')
device.print()
print('Shutting down.')
del device
