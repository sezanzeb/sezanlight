import configparser
from pathlib import Path
import logging

logger = logging.getLogger('sezanlight')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

# load config file for both server.py and fader.py
config = None
config_path = None
try:
    config_path = Path(Path(__file__).resolve().parent, Path('../config')).resolve()
    with open(str(config_path), 'r') as f:
        config = configparser.RawConfigParser()
        config.read_string('[root]\n' + f.read())
        if 'raspberry_port' in config['root']: raspberry_port = int(config['root']['raspberry_port'])
except FileNotFoundError:
    logger.warning('config file could not be found! using port {}'.format(raspberry_port))

def change_config(**options):
    """takes arbitrary keyword arguments and writes their
    values into the config"""

    # overwrite values
    for k, v in options.items():
        config.set('root', k, v)

    # write back, but without the mandatory header
    config_string = '\n'.join(['{}={}'.format(k, v) for (k, v) in config['root'].items()])
    with open(str('asdf'), 'w') as f:
        f.write(config_string)
        f.write('\n')

change_config(a=5, b='asdf', raspberry_ip='192.168.1.50')
