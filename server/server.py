#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
import re
import pigpio
import time

pi = pigpio.pi()

r = 0
g = 0
b = 0

checks_per_second = 1
gpio_r = 17
gpio_g = 22
gpio_b = 24
raspberry_ip = '192.168.2.110'
raspberry_port = 8000

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def __init__(self):
        print(self.close_connection)
        super()

    def do_GET(self):

        url = self.path # /?r=128&g=128&b=128

        # quickly send ok, don't block the client
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'1')
        

        global r, g, b

        color_strings = re.split('[^\d]+', url)[1:]

        r_new = int(color_strings[0])
        g_new = int(color_strings[1])
        b_new = int(color_strings[2])

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
            time.sleep(1/(checks+1))

        r = r_new
        g = g_new
        b = b_new

        pi.set_PWM_dutycycle(gpio_r, r)
        pi.set_PWM_dutycycle(gpio_g, g)
        pi.set_PWM_dutycycle(gpio_b, b)

        print(r, g, b)

print('listening on', raspberry_ip + ':' + str(raspberry_port))
httpd = HTTPServer((raspberry_ip, raspberry_port), SimpleHTTPRequestHandler)
httpd.serve_forever()
