from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from logger import logger
from config import change_config, get_config

BADREQUEST = 400

handlers = {
    'get': [],
    'post': []
}


class BaseServer(BaseHTTPRequestHandler):

    def match_and_call(self, method):
        url = self.path  # /?r=128&g=128&b=128
        global handlers
        match = False

        for matcher, handler in handlers[method]:
            if matcher(url):
                handler(self)
                match = True
                break

        if not match:
            # default handler
            logger.info('invalid request!')
            # was not a valid request
            self.send_response(BADREQUEST)
            self.end_headers()

    def do_POST(self):
        self.match_and_call('post')

    def do_GET(self):
        self.match_and_call('get')


class SezanlightRequestHandler:
    def __init__(self):

        raspberry_ip = get_config('raspberry_ip')
        raspberry_port = get_config('raspberry_port')

        logger.info('listening on {}:{}'.format(raspberry_ip, raspberry_port))
        httpserver = HTTPServer((raspberry_ip, raspberry_port), BaseServer)
        httpserver.serve_forever()

    def add_route(self, method, matcher, handler):
        global handlers
        handlers[method.lower()].push((matcher, handler))


server = SezanlightRequestHandler()
