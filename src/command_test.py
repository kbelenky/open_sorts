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

import sys
import common
import keyboard

CLEAR_LINE = '\033[K'
BOLD = '\033[1m'
UNBOLD = '\033[0m'

config = common.load_config()
serial_port = common.open_device(config)
print('Starting device command interpreter')
common.send_command(serial_port, 'start')

print('Type a single-letter command and then press enter.')
print(f'{BOLD}q:{UNBOLD} quit')
print(f'{BOLD}f:{UNBOLD} feed next card')
print(f'{BOLD}l:{UNBOLD} send card left')
print(f'{BOLD}r:{UNBOLD} send card right')
print(f'{BOLD}\\:{UNBOLD} reset hopper (after reloading)')

while True:
    command = input()
    if command == 'q':
        print('Quitting.')
        break
    elif command == 'f':
        common.send_command(serial_port, 'next_card')
    elif command == 'l':
        common.send_command(serial_port, 'send_left')
    elif command == 'r':
        common.send_command(serial_port, 'send_right')
    elif command == '\\':
        common.send_command(serial_port, 'reset_hopper')
    else:
        print(f'Unknown command: {command}')

serial_port.close()
