#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
import re
import pigpio
import time

pi = pigpio.pi()

fading = False

r = 0
g = 0
b = 0

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        global r, g, b

        url = self.path # /?r=128&g=128&b=128
        color_strings = re.split('[^\d]+', url)[1:]

        r_new = int(color_strings[0])
        g_new = int(color_strings[1])
        b_new = int(color_strings[2])

        # smoothly fade. after 1 second this loop should be ended,
        # therefore i end after 59/60th of a second
        for i in range(59):
            f = i/59
            r_fade = int(r*(1-f) + r_new*(f))
            g_fade = int(g*(1-f) + g_new*(f))
            b_fade = int(b*(1-f) + b_new*(f))
            pi.set_PWM_dutycycle(17, r_fade)
            pi.set_PWM_dutycycle(22, g_fade)
            pi.set_PWM_dutycycle(24, b_fade)
            time.sleep(1/60)

        r = r_new
        g = g_new
        b = b_new

        pi.set_PWM_dutycycle(17, r)
        pi.set_PWM_dutycycle(22, g)
        pi.set_PWM_dutycycle(24, b)

        self.send_response(200)
        self.end_headers()

        print(r, g, b)

        # send ok
        # makes no sense until I actually deal with various exception cases
        # self.wfile.write(b'1')


httpd = HTTPServer(('192.168.2.110', 8000), SimpleHTTPRequestHandler)
httpd.serve_forever()
