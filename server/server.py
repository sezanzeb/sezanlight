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
import re
import pigpio
import time
from threading import Thread, Semaphore
import logging
from pathlib import Path

staticfiles = str(Path(Path(__file__).parent, 'static'))
logfile = str(Path(Path(__file__).parent, 'log'))
logger = logging.getLogger('sezanlight')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(logfile)
handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
logger.addHandler(handler)

# the fading thread
fader_thread = None

# use a semaphore in order not to update some color variables while some
# fading calculation is in progress
working_on_color = Semaphore()

# current color during fading and statically
r = 0
g = 0
b = 0

# color which is used as the fading starting color
r_start = 0
g_start = 0
b_start = 0

# color to fade into
r_target = 0
g_target = 0
b_target = 0

# how much progress the current fading already has
fade_state = 0

# fading config
frequency = 200 #hz

# going to be overwritten during get request:
checks_per_second = 1
checks = 0

# hardware setup
gpio_r = 17
gpio_g = 22
gpio_b = 24

# 0.0.0.0 works if you send requests from another local machine to the raspberry
# 'localhost' would only allow requests from within the raspberry
raspberry_ip = '0.0.0.0'
raspberry_port = 3546

# higher resolution for color changes
# http://abyz.me.uk/rpi/pigpio/python.html#set_PWM_range
full_on = 20000
pi = pigpio.pi()
pi.set_PWM_range(gpio_r, full_on)
pi.set_PWM_range(gpio_g, full_on)
pi.set_PWM_range(gpio_b, full_on)
pi.set_PWM_frequency(gpio_r, 400)
pi.set_PWM_frequency(gpio_g, 400)
pi.set_PWM_frequency(gpio_b, 400)

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

def fade_loop():

    # going to overwrite those globally
    global r, g, b, fade_state

    while True:
        start = time.time()
        # f will move from 0 to 1
        
        working_on_color.acquire()
        if checks > 1:
            fade_state += 1/checks

            if fade_state < 1:
                # Add old and new color together proportionally
                # so that a fading effect is created.
                # Overwrite globals r, g and b so that when fading restarts,
                # that is going to be the new starting color.
                r = (r_start*(1-fade_state) + r_target*(fade_state))
                g = (g_start*(1-fade_state) + g_target*(fade_state))
                b = (b_start*(1-fade_state) + b_target*(fade_state))
                pi.set_PWM_dutycycle(gpio_r, r)
                pi.set_PWM_dutycycle(gpio_g, g)
                pi.set_PWM_dutycycle(gpio_b, b)  
                # logger.info('{} {} {}'.format(r, g, b))

            else:
                pi.set_PWM_dutycycle(gpio_r, r_target)
                pi.set_PWM_dutycycle(gpio_g, g_target)
                pi.set_PWM_dutycycle(gpio_b, b_target)
                pass
        working_on_color.release()

        delta = time.time()-start
        time.sleep(max(0, 1/checks_per_second/(checks+1)-delta))


def is_screen_color_feed(params):
    return 'id' in params and 'mode' in params and params['mode'] == SCREEN_COLOR

def is_static_color(params):
    return not is_screen_color_feed(params)

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        url = self.path # /?r=128&g=128&b=128

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

            global r, g, b
            global checks_per_second, checks, fade_state
            global r_target, g_target, b_target
            global r_start, g_start, b_start
            global fader_thread
            global stop_client_ids, current_client_id

            params_split = url.split('?')[1].split('&')
            i = 0
            # example: ['r=048', 'g=1024.3', 'b=0', 'cps=1']
            # keep current color by default if one channel is missing in the request:
            params = {'r': r, 'g': g, 'b': b, 'cps': 1}
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
                # first connected client ever?
                if current_client_id == -1:
                    current_client_id = params['id']
                else:
                    # if id in stoplist, then stop and reject
                    if params['id'] in stop_client_ids:
                        logger.info('closing connection to {}'.format(params['id']))
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
            if is_static_color(params):
                if current_client_id != -1:
                    # stop the old client
                    stop_client_ids += [current_client_id]
                    logger.info('received static color {}'.format(current_client_id))

            working_on_color.acquire()
            checks_per_second = max(1, params['cps'])
            checks = max(1, int(frequency/checks_per_second)-1)

            # reset fading state:
            fade_state = 0
            # fader_thread is the thread that just keeps fading forever,
            # whereas the main thread writes the variables from the get request into the
            # processes (shared between threads) memory that are used for fading:
            if fader_thread is None or not fader_thread.is_alive():
                # also check if still alive, restart if not
                logger.info('starting fader')
                fader_thread = Thread(target=fade_loop)
                fader_thread.start()
            # only put valid parameters into rgb_target and _start, as the
            # fade thread might read from them at any point. So no temporary
            # stuff that needs to be maxed afterwards or something.
            r_target = max(0, min(full_on, params['r']))
            g_target = max(0, min(full_on, params['g']))
            b_target = max(0, min(full_on, params['b']))
            # start where fading has just been
            r_start = max(0, min(full_on, r))
            g_start = max(0, min(full_on, g))
            b_start = max(0, min(full_on, b))
            working_on_color.release()

            # send ok
            self.send_response(OK)
            self.end_headers()

        elif url.startswith('/color/get'):
            logger.info('request to read the current LED colors')
            self.send_response(OK)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            # just send what the current color is
            self.wfile.write(bytes('{{"r":{},"g":{},"b":{}}}'.format(int(r*255/full_on),
                                                                     int(g*255/full_on),
                                                                     int(b*255/full_on)),
                                                                     'utf-8'))

        elif url[url.rfind('.'):] in allowed_types:

            filename = staticfiles + url
            filetype = url[url.rfind('.'):]

            logger.info('file request for {}'.format(filename))
            # send css and js files upon request
            
            # make sure the request is not doing weird stuff in the url
            # no subdirectories (because there are none) and no going back
            url = url.replace('/', '').replace('..', '')

            contents = b''

            try:
                with open(filename, 'rb') as f:
                    contents = f.read()
            except FileNotFoundError:
                logger.info('file not found!')
                self.send_response(NOTFOUND)
                self.end_headers()
                return

            # send ok
            self.send_response(OK)
            self.send_header('Content-type', allowed_types[filetype])
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




