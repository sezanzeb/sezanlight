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

        print('received get')

        url = self.path # /?r=128&g=128&b=128
        color_strings = re.split('[^\d]+', url)[1:]

        r_new = r
        g_new = g
        b_new = b

        for i in range(59):
            f = i/59
            pi.set_PWM_dutycycle(17, r*(1-f) + r_new*(f))
            pi.set_PWM_dutycycle(22, g*(1-f) + g_new*(f))
            pi.set_PWM_dutycycle(24, b*(1-f) + b_new*(f))
            time.sleep(1/60)

        pi.set_PWM_dutycycle(17, r)
        pi.set_PWM_dutycycle(22, g)
        pi.set_PWM_dutycycle(24, b)

        self.send_response(200)
        self.end_headers()

        print(r, g, b)

        # send ok
        self.wfile.write(b'1')


httpd = HTTPServer(('192.168.2.110', 8000), SimpleHTTPRequestHandler)
httpd.serve_forever()
