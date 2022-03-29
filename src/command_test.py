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
