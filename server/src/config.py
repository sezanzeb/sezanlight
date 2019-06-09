from pathlib import Path
import configparser
from logger import logger

config = None

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


def get_config(key, default=None, cast=None):
    """reads from the config file, if key not available,
    will return the value of the default kwarg.
    
    If cast is None, it will be tried to parse it as int,
    and will be a string otherwise. Examples: int, str,
    can also be a function to parse the value.
    
    Will also add the default value to the loaded config
    object, so that future calls to get_config return
    the previously used default."""

    if key in config['root']:
        value = config['root'][key]
        if cast is None:
            try:
                value = int(value)
            except:
                pass
        if isinstance(cast, type):
            value = cast(value)
        return value
    else:
        config.set('root', key, default)
        return default


def config_2_dict():
    """returns a dict of the complete config"""
    return {k: v for (k, v) in config['root'].items()}


def load_config():
    """reads the config file and returns the
    configparser instance"""

    global config, config_path

    config_path = Path(__file__).absolute().parents[1] / 'config'
    if not config_path.exists():
        # create empty config
        with open(str(config_path), 'w+') as f:
            pass

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

    return config
    
config = load_config()