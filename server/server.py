#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
import re
import pigpio

pi = pigpio.pi()

r = 0
g = 0
b = 0

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        global r, g, b
        
        print('received get')

        url = self.path # /?r=128&g=128&b=128
        color_strings = re.split('[^\d]+', url)[1:]
        r = (r * 10 + int(color_strings[0]))/11
        g = (g * 10 + int(color_strings[1]))/11
        b = (b * 10 + int(color_strings[2]))/11

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
