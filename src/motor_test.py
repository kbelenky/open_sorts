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
