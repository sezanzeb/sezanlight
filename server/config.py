from pathlib import Path
import configparser
from logger import logger


def change_config(**options):
    """takes arbitrary keyword arguments and
    writes their values into the config"""

    # overwrite values
    for k, v in options.items():
        config.set('root', k, v)

    # write back, but without the mandatory header
    config_string = '\n'.join(['{}={}'.format(k, v)
                               for (k, v) in config['root'].items()])
    with open(str(config_path), 'w') as f:
        f.write(config_string)
        f.write('\n')


def get_config(key, default=None):
    if key in config['root']:
        return config['root'][key]
    else:
        return default


# load config file for both server.py and fader.py
config = None
config_path = None
try:
    config_path = Path(Path(__file__).resolve().parent,
                       Path('serverconfig')).resolve()

    with open(str(config_path), 'r') as f:
        config = configparser.RawConfigParser()
        config.read_string('[root]\n' + f.read())

        if not 'raspberry_port' in config['root']:
            # for the port I just went with some random unassigned port from this list:
            # https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml?search=Unassigned
            change_config(raspberry_port=3546)

        if not 'raspberry_ip' in config['root']:
            # 0.0.0.0 works if you send requests from another local machine to the raspberry
            # 'localhost' would only allow requests from within the raspberry
            change_config(raspberry_ip='0.0.0.0')

except FileNotFoundError:
    logger.warning(
        'config file could not be found! using port {}'.format(raspberry_port))
