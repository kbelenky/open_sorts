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
