#!/usr/bin/env python3

"""
    this server consists of two threads:

    the main thread (server.py):
        listens for get requests and decodes the colors from the get params (stored in url)
        then tells the fader thread object about those parameters.

        It also provides the files for the "led controller web app"

        It doesn't touch the PWM hardware at all

    the fader thread object (fader.py):
        the parameters, parsed by the main thread, are those variables
        that control the fading. The fader is in an infinite loop that just fades from the color
        from the state when a request was made to the color of the request. This way, when multiple
        requests are made within a short amount of time, the previous fading task is basically stopped,
        it takes the color that it stopped at and fades to the new color.

        This object is the one in charge for controlling all the gpio PWM settings

"""

from pathlib import Path
from fader import Fader
from server import server
from logger import logger
from config import change_config, get_config, load_config, config_2_dict
from shutil import copyfile
import json
from threading import Thread
import time

# response codes
OK = 200
ERROR = 500
CONFLICT = 409
NOTFOUND = 404
BADREQUEST = 400
# color modes
SCREEN_COLOR = 'continuous'
STATIC_COLOR = 'static'

fader = None

# current client id, used to stop the connection to old
# connections, when a new client starts sending screen info
current_client_id = -1
stop_client_ids = []


# the fading thread
def create_fader_thread():
    fader = Fader()
    fader.start()
    return fader


# static files
allowed_types = {
    '.css': 'text/css',
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.json': 'application/json',
    '.jpg': 'image/jpeg',
    '.png': 'image/png',
    '.ico': 'image/x-icon'
}

def static(handler):
    url = handler.path
    if url == '/':
        url = '/index.html'

    staticfiles = Path(__file__).absolute().parents[1] / 'static'
    filename = str(staticfiles) + url

    if not Path(filename).exists():
        logger.info('file {} not found!'.format(filename))
        handler.send_response(NOTFOUND)
        handler.end_headers()
        return

    # check url using pathlib. It has to be a child of staticfiles
    # prevents going up in the directory tree uring '..' in the url
    if not str(Path(filename).resolve()).startswith(str(staticfiles)):
        # malicious request for a file outside of staticfiles
        logger.warning('malicious request for forbidden paths!')
        # make sure to answer the same way as 404 requests
        # so that the existance of files cannot be checked using get requests
        handler.send_response(NOTFOUND)
        handler.end_headers()
        return

    logger.info('file request for {}'.format(filename))
    # send css and js files upon request

    contents = b''
    with open(filename, 'rb') as f:
        contents = f.read()

    # send ok
    content_type = allowed_types[url[url.rfind('.'):]]
    handler.send_response(OK)
    handler.send_header('Content-type', content_type)
    handler.end_headers()
    # send file
    handler.wfile.write(contents)


def staticmatcher(url):
    if url == '/':
        url = '/index.html'
    return url[url.rfind('.'):] in allowed_types


def readcolor(handler):
    logger.info('request to read the current LED colors')
    handler.send_response(OK)
    handler.send_header('Content-type', 'application/json')
    handler.end_headers()
    # just send what the current color is
    handler.wfile.write(bytes('{{"r":{},"g":{},"b":{}}}'.format(
        *[round(x) for x in fader.get_color()]), 'utf-8'))


def writecolor(handler):
    global fader, stop_client_ids, current_client_id

    url = handler.path

    params_split = url.split('?')[1].split('&')
    i = 0
    # example: ['r=048', 'g=1024.3', 'b=0', 'cps=1']

    # default params:
    # keep current color by default if one channel is missing in the request:
    r, g, b = fader.get_color()
    params = {'r': r, 'g': g, 'b': b, 'cps': 1, 'mode': STATIC_COLOR,
              'id': '{}:{}'.format(*handler.client_address)}

    try:
        while i < len(params_split):
            key, value = params_split[i].split('=')
            # except for those parameter that are supposed to be strings:
            if key in ['mode']:
                # read those params as strings
                params[key] = value
            else:
                # interpret as integer, make sure not to break when there is a dot value
                params[key] = int(float(value))
            i += 1
    except:
        handler.send_response(400)
        handler.end_headers()
        logger.info(
            'could not parse: {} format correct? example: "<ip>:<port>/?r=2048&g=512&b=0&cps=1"'.format(url))
        return
    # is now: {r: 48, g: 1024, b: 0, cps: 1}

    # 1. stop old connections when new connections arrive
    # 2. don't reject new connections because when an old connection is
    # dead some timeout would have to be checked and stuff. Might be even more
    # complex than what I'm doing at the moment.
    if params['mode'] == SCREEN_COLOR:

        # if id in stoplist, then stop and reject
        if params['id'] in stop_client_ids:
            logger.info('closing connection to {} ({})'.format(
                params['id'], handler.client_address[0]))
            # now that it is rejected the client will stop if it
            # is a good client. Remove it from the stop_client_ids list
            # so that a random duplicate id will not be rejected in the future.
            stop_client_ids.remove(params['id'])
            handler.send_response(CONFLICT)
            handler.end_headers()
            return
        else:
            # no conflict with other clients (-1)?
            if current_client_id == -1:
                current_client_id = params['id']
            elif current_client_id != params['id']:
                # if not in stop_client_ids and not the current client?
                # then it's a new client. prepare to accept from the new client
                # and to reject from the old client
                stop_client_ids += [current_client_id]
                current_client_id = params['id']
                logger.info('new connection from {}'.format(current_client_id))

    else:
        # if a static color request was received,
        # stop the client that is currently feeding colors from a screen
        # into the server

        if current_client_id != -1:
            # stop the old client
            stop_client_ids += [current_client_id]
            # no client is actively sending colors anymore:
            current_client_id = -1
            logger.info('received static color')

    # fader is the thread object that just keeps fading forever,
    # whereas the main thread adjusts the members of the fader object
    if fader is None or not fader.is_alive():
        # also check if still alive, restart if not
        logger.error('fader not active anymore! restarting')
        fader = create_fader_thread()

    # now tell the fader what to do
    fader.set_target([params['r'], params['g'], params['b']],
                     params['cps'], params['mode'])

    # send ok
    handler.send_response(OK)
    # otherwise complains about "no root element found":
    handler.send_header('Content-type', 'text/plain')
    handler.end_headers()


def config_endpoint(handler):
    # write the received JSON into the config
    content_len = int(handler.headers.get('Content-Length'))
    body = handler.rfile.read(content_len).decode('utf-8')
    params = json.loads(body)
    if len(params) > 0:
        change_config(**params)
        handler.send_response(OK)
        handler.send_header('Content-type', 'text/plain')
        handler.end_headers()
    else:
        handler.send_response(BADREQUEST)
        handler.send_header('Content-type', 'text/plain')
        handler.end_headers()
        handler.wfile.write(b'no values were provided')


def restart(handler):
    logger.info('server restart requested')

    # stop server and fader
    fader.run_fader = False
    # https://stackoverflow.com/a/19040484
    Thread(target=server.httpserver.shutdown, daemon=True).start()
    server.httpserver.socket.close()

    # restart will be done automatically
    # when the server shuts down


def send_config(handler):
    """sends JSON of the config file to any client
    1. for the frontend config tab
    2. to sync the clr_range setting"""
    logger.info('request for config values')
    handler.send_response(OK)
    handler.send_header('Content-type', 'application/json')
    handler.end_headers()
    # just send what the current color is
    handler.wfile.write(bytes(json.dumps(config_2_dict()), 'utf-8'))


# add all the routes to the server
server.add_route('POST', '/config', config_endpoint)
server.add_route('GET', '/color/set', writecolor)
server.add_route('GET', '/color/get', readcolor)
server.add_route('GET', staticmatcher, static)
server.add_route('GET', '/restart', restart)
server.add_route('GET', '/config', send_config)

# autorestart
while True:
    fader = create_fader_thread()
    server.start()
    # if code reaches this point,
    # server was stopped. wait a short
    # moment before restart so that
    # the raspberry doesn't go crazy
    # while looping forever
    time.sleep(0.1)
