import sys
import common

CLEAR_LINE = '\033[K'
BOLD = '\033[1m'
UNBOLD = '\033[0m'


def CursorUp(lines):
    return f'\033[{lines}A'


def SensorValue(value):
    if int(value) == 0:
        return 'triggered'
    else:
        return 'empty'


config = common.load_config()
serial_port = common.open_device(config)

print('Press ctrl+C to quit')
for _ in range(5):
    print()

while True:
    try:
        prefix = CursorUp(5)
        line_prefix = CLEAR_LINE
        result, _ = common.send_command(serial_port, 'query_sensors')
        output = '\n'.join([
            f'{line_prefix}{label}: {BOLD}{SensorValue(value)}{UNBOLD}'
            for label, value in [  #
                ('Primary hopper: ', result.primary),  #
                ('Secondary hopper', result.secondary),  #
                ('Motor return', result.motor),  #
                ('Tray 1', result.tray1),  #
                ('Tray 2', result.tray2)
            ]
        ])
        print(f'{prefix}{output}')
    except:
        print('Exiting.')
        break

serial_port.close()
