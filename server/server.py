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
from threading import Thread

pi = pigpio.pi()

# the fadpything thread
fader = None

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
f = 0

# fading config
frequency = 200 #hz

# going to be overwritten during get request:
checks_per_second = 1
checks = 0

# hardware setup
gpio_r = 17
gpio_g = 22
gpio_b = 24
raspberry_ip = '192.168.2.110'
raspberry_port = 8000

# higher resolution for color changes
# http://abyz.me.uk/rpi/pigpio/python.html#set_PWM_range
full_on = 2048
pi.set_PWM_range(gpio_r, full_on)
pi.set_PWM_range(gpio_g, full_on)
pi.set_PWM_range(gpio_b, full_on)

def fade():

    # going to overwrite those globally
    global r, g, b, f

    while True:
        start = time.time()
        # f will move from 0 to 1
        if checks > 1:
            f += 1/checks

            if f < 1:
                # Add old and new color together proportionally
                # so that a fading effect is created.
                # Overwrite globals r, g and b so that when fading restarts,
                # that is going to be the new starting color.
                r = int(r_start*(1-f) + r_target*(f))
                g = int(g_start*(1-f) + g_target*(f))
                b = int(b_start*(1-f) + b_target*(f))
                pi.set_PWM_dutycycle(gpio_r, r)
                pi.set_PWM_dutycycle(gpio_g, g)
                pi.set_PWM_dutycycle(gpio_b, b)  
                # print(r, g, b)

            else:
                pi.set_PWM_dutycycle(gpio_r, r_target)
                pi.set_PWM_dutycycle(gpio_g, g_target)
                pi.set_PWM_dutycycle(gpio_b, b_target)
                pass

        delta = time.time()-start
        time.sleep(max(0, 1/checks_per_second/(checks+1)-delta))


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        global r, g, b
        global checks_per_second, checks, f
        global r_target, g_target, b_target
        global r_start, g_start, b_start
        global fader

        url = self.path # /?r=128&g=128&b=128

        # quickly send ok, don't block the client
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'1')
        # https://stackoverflow.com/questions/6594418/simplehttprequesthandler-close-connection-before-returning-from-do-post-method
        # self.finish()
        # self.connection.close()
        # doesnt work...
        # (still blocks the client)

        params_split = re.split('[=&]', url[2:])
        # example: ['r', '048', 'g', '1024.3', 'b', '0', 'cps', '1']
        i = 0
        params = {}
        try:
            while i < len(params_split):
                key = params_split[i]
                value = params_split[i+1]
                # interpret as integer, failsafe way
                params[key] = int(float(value))
                i += 2
        except:
            print('could not parse:', url, 'format correct? example: "<ip>:<port>/?r=2048&g=512&b=0&cps=1"')
            return
        # is now: {r: 48, g: 1024, b: 0, cps: 1}

        checks_per_second = max(1, params['cps'])
        checks = max(1, int(frequency/checks_per_second)-1)

        # reset fading state:
        f = 0
        # fader is the thread that just keeps fading forever,
        # whereas the main thread writes the variables from the get request into the
        # processes (shared between threads) memory that are used for fading:
        if fader is None or not fader.is_alive():
            # also check if still alive, restart if not
            print('starting fader')
            fader = Thread(target=fade)
            fader.start()
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

print('listening on', raspberry_ip + ':' + str(raspberry_port))
httpd = HTTPServer((raspberry_ip, raspberry_port), SimpleHTTPRequestHandler)
httpd.serve_forever()




