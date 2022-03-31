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
import re
import serial
import time

from dataclasses import dataclass
from types import SimpleNamespace


def load_config():
    with open("config.json", "r") as config_file:
        return json.load(config_file,
                         object_hook=lambda x: SimpleNamespace(**x))


def save_config(config):
    with open("config.json", "w") as config_file:
        return json.dump(config, config_file, indent=4, sort_keys=True)


def send_command(serial_port, command):
    @dataclass
    class SensorValues:
        primary: int
        secondary: int
        motor: int
        tray1: int
        tray2: int

    # The device handles commands synchronously. Don't send a new command until
    # the device has responded to the last one.
    # The device may send 'done', 'empty', 'not_empty', or 'query: ...' as
    # responses.
    #
    # Anything else is a log statement that may be informative, but can also
    # be safely ignored.
    log = []
    serial_port.write((command + '\n').encode('utf-8'))
    while True:
        line_in = serial_port.readline()
        decoded_line = line_in[0:len(line_in) - 2].decode('utf-8')
        if len(decoded_line) == 0:
            pass
        elif decoded_line in ['done', 'empty', 'not_empty']:
            return decoded_line, log
        elif decoded_line.startswith('query:'):
            match_dict = re.fullmatch(
                'query: (?P<primary>[0-9]+), (?P<secondary>[0-9]+), ' +
                '(?P<motor>[0-9]+), (?P<tray1>[0-9]+), (?P<tray2>[0-9]+)',
                decoded_line).groupdict()
            return SensorValues(match_dict['primary'], match_dict['secondary'],
                                match_dict['motor'], match_dict['tray1'],
                                match_dict['tray2']), log
        else:
            log.append(decoded_line)


# Converts a nested set of simple namespace JSON back into nested dictionaries.
def to_dictionary(obj):
    if hasattr(obj, "__dict__"):
        return {k: to_dictionary(v) for k, v in obj.__dict__.items()}
    else:
        return obj


def open_device(config):
    port = config.serial_port
    print(f'Opening serial port: {port}')
    serial_port = serial.Serial(port, timeout=1)
    print('Port open. Waiting for device to boot.')
    time.sleep(5)
    print('Sending device config.')
    device_config = json.dumps(to_dictionary(config.device_config))
    result, log = send_command(serial_port, f'initialize\n{device_config}\n')
    for entry in log:
        print(entry)
    print(result)
    return serial_port


def load_catalog():
    # The 'catalog' is just a flat array of card information.
    # cards_by_id is a dictionary mapping cards by their id.
    # I use the format '{scryfall id}_{face_index}' for all cards.
    # Single-faced cards have only one face_index (0).
    with open("card_catalog.json", "r", encoding="utf-8") as json_file:
        catalog = json.load(json_file)
    cards_by_id = dict()
    for card in catalog:
        id = card['id']
        face_index = card['face_index']
        card_id = f'{id}_{face_index}'
        cards_by_id[card_id] = card
    return catalog, cards_by_id
