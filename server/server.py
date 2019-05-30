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

        for key, handler in handlers[method]:
            matcher = key
            if matcher == '*':
                matcher = lambda: True
            elif method.lower() == 'get':
                matcher = lambda url: url.startswith(key)
            elif method.lower() == 'post':
                matcher = lambda url: url == key
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
    def add_route(self, method, matcher, handler):
        """matcher can be a lambda function that receives
        the url and that returns true or false, a string,
        or a single wildcard to match any url for the given
        method"""

        msg = 'a matcher function'
        if type(matcher) == str:
            msg = matcher
            if matcher == '*':
                msg = 'any url'

        global handlers
        handlers[method.lower()].append((matcher, handler))
        print('adding {} route for {}'.format(method, msg))

    def start(self):

        raspberry_ip = get_config('raspberry_ip', '0.0.0.0')
        raspberry_port = int(get_config('raspberry_port', 3546))

        logger.info('listening on {}:{}'.format(raspberry_ip, raspberry_port))
        httpserver = HTTPServer((raspberry_ip, raspberry_port), BaseServer)
        httpserver.serve_forever()


server = SezanlightRequestHandler()
