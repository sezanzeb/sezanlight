#!/usr/bin/env python3

"""
    this server consists of two threads:
    the main thread:
        listens for get requests and decodes the colors from the get params (stored in url)
        then overwrites the global variables
    the fader thread:
        the overwritten global variables, overwritten by the main thread, are those variables
        that control the fading. The fader is in an infinite loop that just fades from the color
        from the state when a request was made to the color of the request. This way, when multiple
        requests are made within a short amount of time, the previous fading task is basically stopped,
        it takes the color that it stopped at and fades to the new color.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import logging
from pathlib import Path
from fader import Fader

import pigpio
pi = pigpio.pi()

staticfiles = Path(Path(__file__).parent, 'static').absolute()
logfile = Path(Path(__file__).parent, 'log')
logger = logging.getLogger('sezanlight')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(str(logfile))
handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
logger.addHandler(handler)
# also enable console output:
logger.addHandler(logging.StreamHandler())

# hardware setup
gpio_r = 17
gpio_g = 22
gpio_b = 24

# 0.0.0.0 works if you send requests from another local machine to the raspberry
# 'localhost' would only allow requests from within the raspberry
raspberry_ip = '0.0.0.0'
raspberry_port = 3546

# http://abyz.me.uk/rpi/pigpio/python.html#set_PWM_range
full_on = 20000

# higher resolution for color changes
# https://github.com/fivdi/pigpio/blob/master/doc/gpio.md
gpio_freq_movie = 400 # 2500 colors
gpio_freq_static = 2500 # 400 colors. Have that frequency higher to protect the eye

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
SCREEN_COLOR = 1
STATIC = 2


def create_fader_thread():
    fader = Fader(gpio_r, gpio_g, gpio_b, full_on)
    fader.start()
    return fader

fader = create_fader_thread()


def set_freq(freq):
    """
        sets the frequency of the gpio PWM signal.
        Higher frequencies result in smaller resolution
        for color changes.
        https://github.com/fivdi/pigpio/blob/master/doc/gpio.md
    """

    if freq != pi.get_PWM_frequency(gpio_r):
        pi.set_PWM_frequency(gpio_r, freq)
        pi.set_PWM_frequency(gpio_g, freq)
        pi.set_PWM_frequency(gpio_b, freq)


def is_screen_color_feed(params):
    return 'id' in params and 'mode' in params and params['mode'] == SCREEN_COLOR


def is_static_color(params):
    return not is_screen_color_feed(params)


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        url = self.path # /?r=128&g=128&b=128

        logger.info('\nrequest for {}'.format(url))

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
            # keep current color by default if one channel is missing in the request:
            params = {'r': fader.r, 'g': fader.g, 'b': fader.b, 'cps': 1}
            try:
                while i < len(params_split):
                    key, value = params_split[i].split('=')
                    # interpret as integer, failsafe way
                    params[key] = int(float(value))
                    i += 1
            except:
                self.send_response(CONFLICT)
                self.end_headers()
                logger.info('could not parse: {} format correct? example: "<ip>:<port>/?r=2048&g=512&b=0&cps=1"'.format(url))
                return
            # is now: {r: 48, g: 1024, b: 0, cps: 1}

            # 1. stop old connections when new connections arrive
            # 2. don't reject new connections because when an old connection is
            # dead some timeout would have to be checked and stuff. Might be even more
            # complex than what I'm doing at the moment.
            if is_screen_color_feed(params):

                set_freq(gpio_freq_movie)

                # first connected client ever?
                if current_client_id == -1:
                    current_client_id = params['id']
                else:
                    # if id in stoplist, then stop and reject
                    if params['id'] in stop_client_ids:
                        logger.info('closing connection to {}'.format(params['id']))
                        # now that it is rejected the client will stop if it
                        # is a good client. Remove it from the stop_client_ids list
                        # so that a random duplicate id will not be rejected in the future.
                        stop_client_ids.remove(params['id'])
                        self.send_response(CONFLICT)
                        self.end_headers()
                        return
                    # if not in stop_client_ids and not the current client?
                    # then it's a new client. prepare to accept from the new client
                    elif current_client_id != params['id']:
                        # stop the old client
                        stop_client_ids += [current_client_id]
                        current_client_id = params['id']
                        logger.info('new connection from {}'.format(current_client_id))

            # if a static color request was received,
            # stop the client that is currently feeding colors from a screen
            # into the server
            elif is_static_color(params):

                # higher frequency for eye health
                # for static colors that are active
                # for a longer period of time
                set_freq(gpio_freq_static)

                if current_client_id != -1:
                    # stop the old client
                    stop_client_ids += [current_client_id]
                    logger.info('received static color {}'.format(current_client_id))

            """# if dark color, reduce frequency to obtain higher dutycicle resolution
            # for more fine-grained settings
            value = (params['r'] + params['g'] + params['b'])/3
            exp = max(1, math.log(value/full_on, 0.5))
            freq = max(200, int(2 * 800 / exp))
            # dutycicle of 75% -> half the frequency
            # 87.25% -> quarter of the frequency
            # this causes some flickering, so don't switch frequencies often
            # print(freq, value, math.log(value/full_on, 0.5), gpio_freq / math.log(value/full_on, 0.5))
            # print("exp", exp, "value", value, "gpio_freq", gpio_freq, "freq", freq, "arsch", 4*gpio_freq, 4*gpio_freq/exp)
            if gpio_freq/freq >= 1.5 or freq/gpio_freq >= 1.5:
                print("setting gpio freq to", freq)
                pi.set_PWM_frequency(gpio_r, freq)
                pi.set_PWM_frequency(gpio_g, freq)
                pi.set_PWM_frequency(gpio_b, freq)
                gpio_freq = freq"""

            fader.set_fading_speed(params['cps'])

            # fader is the thread that just keeps fading forever,
            # whereas the main thread writes the variables from the get request into the
            # processes (shared between threads) memory that are used for fading:
            if fader is None or not fader.is_alive():
                # also check if still alive, restart if not
                logger.error('fader not active anymore! restarting')
                fader = create_fader_thread()
                fader.start()
            # only put valid parameters into rgb_target and _start, as the
            # fade thread might read from them at any point. So no temporary
            # stuff that needs to be maxed afterwards or something.
            fader.set_target(params['r'], params['g'], params['b'])

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

pi.set_PWM_range(gpio_r, full_on)
pi.set_PWM_range(gpio_g, full_on)
pi.set_PWM_range(gpio_b, full_on)

logger.info('listening on {}:{}'.format(raspberry_ip, raspberry_port))
httpd = HTTPServer((raspberry_ip, raspberry_port), SimpleHTTPRequestHandler)
httpd.serve_forever()




