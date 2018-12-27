#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
import re
import pigpio
import time
from multiprocessing import Process

pi = pigpio.pi()

# the fading process
proc = None

r = 0
g = 0
b = 0

gpio_r = 17
gpio_g = 22
gpio_b = 24
raspberry_ip = '192.168.2.110'
raspberry_port = 8000

def fade(r, g, b, r_new, g_new, b_new, checks_per_second):

    # smoothly fade. after 1 second this loop should be ended,
    # therefore i end after 59/60th of a second
    checks = int(60/checks_per_second)-1

    for i in range(checks):
        f = i/checks
        r_fade = int(r*(1-f) + r_new*(f))
        g_fade = int(g*(1-f) + g_new*(f))
        b_fade = int(b*(1-f) + b_new*(f))
        pi.set_PWM_dutycycle(17, r_fade)
        pi.set_PWM_dutycycle(22, g_fade)
        pi.set_PWM_dutycycle(24, b_fade)
        time.sleep(1/checks_per_second/(checks+1))

    pi.set_PWM_dutycycle(gpio_r, r_new)
    pi.set_PWM_dutycycle(gpio_g, g_new)
    pi.set_PWM_dutycycle(gpio_b, b_new)

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        global r, g, b, proc

        url = self.path # /?r=128&g=128&b=128

        # quickly send ok, don't block the client
        # (still blocks the client)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'1')

        params = re.split('[^\d]+', url)[1:]

        r_new = int(params[0])
        g_new = int(params[1])
        b_new = int(params[2])
        checks_per_second = int(params[3])

        # fade the color in a new process so that the client is not blocked
        if not proc is None:
            # make sure two fading processes are not overlapping
            if proc.is_alive():
                proc.terminate()
        proc = Process(target=fade, args=(r, g, b, r_new, g_new, b_new, checks_per_second))
        proc.start()

        # overwrite state of server
        r = r_new
        g = g_new
        b = b_new

print('listening on', raspberry_ip + ':' + str(raspberry_port))
httpd = HTTPServer((raspberry_ip, raspberry_port), SimpleHTTPRequestHandler)
httpd.serve_forever()
