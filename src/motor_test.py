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

CLEAR_LINE = '\033[K'
BOLD = '\033[1m'
UNBOLD = '\033[0m'

config = common.load_config()
serial_port = common.open_device(config)

input('Press `Enter` to run the primary hopper motor forward.')
common.send_command(serial_port, 'primary_motor')

input('Press `Enter` to run the secondary hopper motor forward.')
common.send_command(serial_port, 'secondary_motor')

input('Press `Enter` to run the tray motor to feed left.')
common.send_command(serial_port, 'tray_motor')

print('Motor test is complete.')
print('If any motors ran in the wrong direction, ' +
      'change the motor\'s `direction` value (0 or 1) in config.json ' +
      'and run this test again.')

serial_port.close()
