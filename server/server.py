#!/usr/bin/env python3

"""
    this server consists of two threads:

    the main thread:
        listens for get requests and decodes the colors from the get params (stored in url)
        then tells the fader thread object about those parameters.

        It also provides the files for the "led controller web app"

    the fader thread object:
        the parameters, parsed by the main thread, are those variables
        that control the fading. The fader is in an infinite loop that just fades from the color
        from the state when a request was made to the color of the request. This way, when multiple
        requests are made within a short amount of time, the previous fading task is basically stopped,
        it takes the color that it stopped at and fades to the new color.

        This object is the one in charge for controlling all the gpio PWM settings

"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import logging
from pathlib import Path
from fader import Fader
import configparser

staticfiles = Path(Path(__file__).parent, 'static').absolute()
logfile = Path(Path(__file__).parent, 'log')
logger = logging.getLogger('sezanlight')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(str(logfile))
handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
logger.addHandler(handler)
# also enable console output:
logger.addHandler(logging.StreamHandler())

# 0.0.0.0 works if you send requests from another local machine to the raspberry
# 'localhost' would only allow requests from within the raspberry
raspberry_ip = '0.0.0.0'

# for the port I just went with some random unassigned port from this list:
# https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml?search=Unassigned
raspberry_port = 3546

# hardware setup (those are the pins used in https://dordnung.de/raspberrypi-ledstrip/)
gpio_r = 17
gpio_g = 22
gpio_b = 24

# read gpio pins and port from config file
try:
    config_path = Path(Path(__file__).resolve().parent, Path('../config')).resolve()
    with open(str(config_path)) as f:
        config = configparser.RawConfigParser()
        config.read_string('[root]\n' + f.read())
        if 'gpio_r' in config['root']: gpio_r = int(config['root']['gpio_r'])
        if 'gpio_g' in config['root']: gpio_g = int(config['root']['gpio_g'])
        if 'gpio_b' in config['root']: gpio_b = int(config['root']['gpio_b'])
        if 'raspberry_port' in config['root']: raspberry_port = int(config['root']['raspberry_port'])
except FileNotFoundError:
    logger.warning('config file could not be found! using pins {}, {} and {} and port {}'.format(gpio_r, gpio_g, gpio_b, raspberry_port))


# http://abyz.me.uk/rpi/pigpio/python.html#set_PWM_range
full_on = 20000

# the fading thread
fader = None

# current client id, used to stop the connection to old
# connections, when a new client starts sending screen info
current_client_id = -1
stop_client_ids = []

# response codes
OK = 200
ERROR = 500
CONFLICT = 409
NOTFOUND = 404
BADREQUEST = 400

# color modes
SCREEN_COLOR = 'movie'
STATIC = 'static'


def create_fader_thread():
    fader = Fader(gpio_r, gpio_g, gpio_b, full_on, logger)
    fader.start()
    return fader

fader = create_fader_thread()


def is_screen_color_feed(params):
    return 'id' in params and 'mode' in params and params['mode'] == SCREEN_COLOR


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        url = self.path # /?r=128&g=128&b=128

        print(' ')
        logger.info('request for {}'.format(url))

        if url == '/':
            url = '/index.html'

        allowed_types = {'.css':'text/css',
                         '.html':'text/html',
                         '.js':'text/javascript',
                         '.jpg':'image/jpeg',
                         '.png':'image/png',
                         '.ico':'image/x-icon'}

        # if not a file request
        if url.startswith('/color/set/'):

            global fader
            global stop_client_ids, current_client_id

            params_split = url.split('?')[1].split('&')
            i = 0
            # example: ['r=048', 'g=1024.3', 'b=0', 'cps=1']

            # default params:
            # keep current color by default if one channel is missing in the request:
            params = {'r': fader.r, 'g': fader.g, 'b': fader.b, 'cps': 1, 'mode': 'static'}

            try:
                while i < len(params_split):
                    key, value = params_split[i].split('=')
                    # interpret as integer, failsafe way
                    # except for those parameter that are supposed to be strings:
                    if key in ['mode']:
                        params[key] = value
                    else:
                        params[key] = int(float(value))
                    i += 1
            except:
                self.send_response(400)
                self.end_headers()
                logger.info('could not parse: {} format correct? example: "<ip>:<port>/?r=2048&g=512&b=0&cps=1"'.format(url))
                return
            # is now: {r: 48, g: 1024, b: 0, cps: 1}

            # 1. stop old connections when new connections arrive
            # 2. don't reject new connections because when an old connection is
            # dead some timeout would have to be checked and stuff. Might be even more
            # complex than what I'm doing at the moment.
            if params['mode'] == 'movie':

                # if id in stoplist, then stop and reject
                if params['id'] in stop_client_ids:
                    logger.info('closing connection to {} ({})'.format(params['id'], self.client_address[0]))
                    # now that it is rejected the client will stop if it
                    # is a good client. Remove it from the stop_client_ids list
                    # so that a random duplicate id will not be rejected in the future.
                    stop_client_ids.remove(params['id'])
                    self.send_response(CONFLICT)
                    self.end_headers()
                    return
                else:
                    # no conflict with other clients (-1)?
                    if current_client_id == -1:
                        current_client_id = params['id']
                    elif current_client_id != params['id']:
                        # if not in stop_client_ids and not the current client?
                        # then it's a new client. prepare to accept from the new client
                        # and to reject from the old client
                        stop_client_ids += [current_client_id]
                        current_client_id = params['id']
                        logger.info('new connection from {}'.format(current_client_id))

            else:
                # if a static color request was received,
                # stop the client that is currently feeding colors from a screen
                # into the server

                if current_client_id != -1:
                    # stop the old client
                    stop_client_ids += [current_client_id]
                    # no client is actively sending colors anymore:
                    current_client_id = -1
                    logger.info('received static color')

            # fader is the thread object that just keeps fading forever,
            # whereas the main thread adjusts the members of the fader object
            if fader is None or not fader.is_alive():
                # also check if still alive, restart if not
                logger.error('fader not active anymore! restarting')
                fader = create_fader_thread()
                
            # now tell the fader what to do
            fader.set_target(params['r'], params['g'], params['b'], params['cps'], params['mode'])

            # send ok
            self.send_response(OK)
            self.end_headers()

        elif url.startswith('/color/get'):
            logger.info('request to read the current LED colors')
            self.send_response(OK)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            # just send what the current color is
            self.wfile.write(bytes('{{"r":{},"g":{},"b":{}}}'.format(int(fader.r * 255 / full_on),
                                                                     int(fader.g * 255 / full_on),
                                                                     int(fader.b * 255 / full_on)),
                                                                     'utf-8'))

        elif url[url.rfind('.'):] in allowed_types:

            filename = str(staticfiles) + url

            if not Path(filename).exists():
                logger.info('file not found!')
                self.send_response(NOTFOUND)
                self.end_headers()
                return

            # check url using pathlib. It has to be a child of staticfiles
            # prevents going up in the directory tree uring '..' in the url
            if not str(Path(filename).resolve()).startswith(str(staticfiles)):
                # malicious request for a file outside of staticfiles
                logger.warning('malicious request!')
                # make sure to answer the same way as 404 requests
                # so that the existance of files cannot be checked using get requests
                self.send_response(NOTFOUND)
                self.end_headers()
                return

            logger.info('file request for {}'.format(filename))
            # send css and js files upon request

            contents = b''
            with open(filename, 'rb') as f:
                contents = f.read()

            # send ok
            content_type = allowed_types[url[url.rfind('.'):]]
            self.send_response(OK)
            self.send_header('Content-type', content_type)
            self.end_headers()
            # send file
            self.wfile.write(contents)

        else:
            logger.info('invalid request!')
            # was not a valid request
            self.send_response(BADREQUEST)
            self.end_headers()

logger.info('listening on {}:{}'.format(raspberry_ip, raspberry_port))
httpd = HTTPServer((raspberry_ip, raspberry_port), SimpleHTTPRequestHandler)
httpd.serve_forever()




