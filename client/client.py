#!/usr/bin/env python3

import PIL.Image
import PIL.ImageStat
import Xlib.display # python-xlib

import requests
import time

import sys

# many thanks to:
# https://stackoverflow.com/questions/53688777/how-to-implement-x11return-colour-of-a-screen-pixel-c-code-for-luajits-ffi
# https://kukuruku.co/post/a-cheat-sheet-for-http-libraries-in-c/
# https://stackoverflow.com/questions/9786150/save-curl-content-result-into-a-string-in-c
# https://stackoverflow.com/questions/19555121/how-to-get-current-timestamp-in-milliseconds-since-1970-just-the-way-java-gets
# https://stackoverflow.com/questions/7868936/read-file-line-by-line-using-ifstream-in-c#7868998
# https://stackoverflow.com/questions/216823/whats-the-best-way-to-trim-stdstring

# color modes
SCREEN_COLOR = "continuous"
STATIC = "static"

# error codes
OK = 200
ERROR = 500
CONFLICT = 409

# for how was no answer received from the server?
timeout = 0


def get_us():
    """ this function returns the microseconds since 1970 """
    return time.time() * 1000 * 1000


def sendcolor(r, g, b, ip, port, checks_per_second,
              client_id, mode, max_timeout, last_message_timestamp,
              verbose_level):
    """sends a get request to the LED server using curl
    - r, g and b are the colors between 0 and full_on
    - ip and port those of the raspberry
    - check_per_second is how often this client will (try to) make such reqeusts per seoncds
    - client_id is an identifier for the current "stream" of messages from this client
    - mode should be SCREEN_COLOR
    - max_timeout is read from the config file. it's an integer of seconds. The code will stop when
    no communication is received within that amount of time.
    - last_message_timestamp is a pointer to a get_us() value of the last successful communciation"""
            
    url = "http://{}:{}/color/set/?r={}&g={}&b={}&cps={}&id={}&mode={}".format(
        ip, port, int(r), int(g), int(b), checks_per_second, client_id, mode)

    if verbose_level >= 1:
        print("sending GET pramas: ", url, "\n")

    print("sending GET pramas:", url)
    r = requests.get(url)
    http_code = r.status_code

    if http_code == CONFLICT:
        print("server closed connection with this client to prevent duplicate "
                "connections. Another client started sending to the server!")
        quit(1)

    # check if server is available if for 5 seconds no color reached it
    if http_code != OK:
        # how much time passed since the last successful communication?
        timeout = (float)(get_us() - last_message_timestamp) / 1000000

        if timeout >= max_timeout:
            print("timeout! cannot reach server!")
            quit(1)
        else:
            print("server did not send a response for ", timeout, "s")
    else:
        last_message_timestamp = get_us()


class Color:
    def __init__(self, arr):
        self.red = arr[0]
        self.green = arr[1]
        self.blue = arr[2]


def parse_float_array(strvalue, array):
    """given a string like 1.10,0.88,0.7
    overwrites the values in the array parameter to
    [1.10, 0.88, 0.7]"""
    for i, val in enumerate(strvalue.split(',')):
        array[i] = float(val)


def main(argv):
    # default params:

    # screen
    screen_width = 1920
    screen_height = 1080

    # sampling
    smoothing = 3
    checks_per_second = 2
    columns = 50
    lines = 3

    # hardware
    raspberry_ip = ""
    raspberry_port = 3546

    max_timeout = 10

    # colors
    # if True, will use a window average for smoothing
    # if False, weights the old color by smoothing and averages,
    # creating an "ease out" effect but produces artifacts when fading to black
    # because incremential changes will start to produce jumping hues.
    linear_smoothing = True
    brightness = [1.00, 0.85, 0.5]
    gamma = [1.10, 0.88, 0.7]
    # 0 = no nrmalization, 0.5 = increase lightness, 1 = normalize to full_on
    normalize = 0
    # if False, will normalize the max value to full_on, if True wil normalize the sum to it
    # setting it to True will basically favor saturated colors over grey/white ones during normalization
    normalize_sum = True
    # 0 = no adjustment, 0.5 = increases saturation, 1 = darkest color becomes 0 (prevents gray values alltogether)
    increase_saturation = 0.5

    # some debugging stuff
    verbose_level = 1

    # overwrite default params with params from config file
    with open(argv[1], 'r') as f:
        for line in f:
            config_exists = True
            line = line.strip()

            if len(line) == 0:
                continue

            # skip comments
            if line[0] == '#':
                continue

            # search for equal symbol
            i = line.find('=')
            if i != -1:
                key = line[0: i]
                strvalue = line[i+1:]
                # trim in-place
                key = key.strip()
                strvalue = strvalue.strip()

                # depending on the key, parse the value in different ways
                try:
                    if key == "raspberry_port": raspberry_port = int(strvalue)
                    elif key == "raspberry_ip": raspberry_ip = strvalue
                    elif key == "screen_width": screen_width = int(strvalue)
                    elif key == "screen_height": screen_height = int(strvalue)
                    elif key == "increase_saturation": increase_saturation = float(strvalue)
                    elif key == "normalize": normalize = float(strvalue)
                    elif key == "lines": lines = int(strvalue)
                    elif key == "columns": columns = int(strvalue)
                    elif key == "smoothing": smoothing = int(strvalue)
                    elif key == "checks_per_second": checks_per_second = int(strvalue)
                    elif key == "brightness": parse_float_array(strvalue, brightness)
                    elif key == "gamma": parse_float_array(strvalue, gamma)
                    elif key == "linear_smoothing": linear_smoothing = strvalue == "True" or strvalue == 1
                    elif key == "max_timeout": max_timeout = int(strvalue)
                    elif key == "verbose_level": verbose_level = int(strvalue)
                except:
                    print("could not parse \"", key, "\" with value \"", strvalue, "\"")

    if not config_exists:
        print("error: config file could not be found. You need to specify the path to it as command line argument")
        return 1

    if raspberry_ip == "":
        print("error: you need to set the raspberries ip in the config file like this (example): \"raspberry_ip=192.168.1.100\"")
        return 1

    client_id = int((time.time() * 10000000)%100000)

    # controls the resolution of the color space of the leds
    # default is 256, this is also configured in server.py
    # have this as float, because r, g and b are floats during
    # filtering in order to improve type compatibility stuff.
    full_on = 20000

    # some checking for broken configurations
    if lines == 0:
        lines = 1
    if columns == 0:
        columns = 1
    if checks_per_second == 0:
        checks_per_second = 1
    if linear_smoothing:
        # for linear smoothing it needs to be 1 at least
        # because it uses an array that contains at least
        # the new color
        smoothing = max(1, smoothing)
    else:
        # otherwise, put 0 weight onto the old color
        smoothing = max(0, smoothing)

    c = Color([0, 0, 0])
    root = Xlib.display.Display().screen().root

    image = None # XImage

    # used for non-linear ease-out smoothing
    # and for checking if the color even changed
    # so save raspberry cpu time and network
    # bandwidth
    r_old = 0
    g_old = 0
    b_old = 0

    # used for linear smoothing
    # paranthesis will initialize the array with zeros
    r_window = [0] * smoothing
    g_window = [0] * smoothing
    b_window = [0] * smoothing
    # i is the current po
    i = 0

    # assume a working condition in the beginning,
    # this is passed to sendcolor as a pointer and overwritten there
    # on successful communications
    last_message_timestamp = get_us()

    # loop forever, reading the screen
    while True:

        start = get_us()

        # work on floats in order to prevent rounding errors that add up
        r = 1
        g = 1
        b = 1

        # count three lines on the screen or something
        for i in range(1, lines + 1):
            # to prevent overflows, aggregate color for each line individually
            # EDIT: that was needed when those variables were ints a time ago
            r_line = 0
            g_line = 0
            b_line = 0
            normalizer = 0
            
            # ZPixmap fixes xorg color reading on cinnamon a little bit (as opposed to XYPixmap)
            # some info on XGetImage + XGetPixel speed:
            # asking for the complete screen: very slow
            # asking for lines: relatively fast
            # asking for individual pixels: slow
            y = int(screen_height / (lines + 1) * i)
            # image = XGetImage(d, root, 0, y, screen_width, 1, AllPlanes, ZPixmap)
            image = root.get_image(0, y, screen_width, 1, Xlib.X.ZPixmap, 0xffffffff)
            image_rgb = PIL.Image.frombytes("RGB", (screen_width, 1), image.data, "raw", "BGRX")
            
            # e.g. is columns is 3, it will check the center pixel, and the centers between the center pixel and the two borders
            x = (screen_width % columns) // 2
            while True:
                x += screen_width // columns
                if x >= screen_width:
                    break
                    
                c = Color(image_rgb.im[x])
                c_r = full_on * c.red / 256
                c_g = full_on * c.green / 256
                c_b = full_on * c.blue / 256
                # give saturated colors (like green, purple, blue, orange, ...) more weight
                # over grey colors
                # difference between lowest and highest value should do the trick already
                diff = ((max(max(c_r, c_g), c_b) - min(min(c_r, c_g), c_b)))
                weight = diff * 20 / full_on + 1 # between 1 and 21
                normalizer += weight
                r_line += c_r * weight
                g_line += c_g * weight
                b_line += c_b * weight

            r += r_line / normalizer
            g += g_line / normalizer
            b += b_line / normalizer

        # r g and b are now between 0 and full_on
        r = r / lines
        g = g / lines
        b = b / lines
        if verbose_level >= 2:
            print("observed color : ", r, " ", g, " ", b)

        # only do stuff if the color changed.
        # the server only fades when the new color exceeds a threshold of 2.5% of full_on
        # in the added deltas. to not waste computational power of the pi and network bandwith,
        # do nothing.
        delta_clr = abs(r - r_old) + abs(g - g_old) + abs(b - b_old)
        if delta_clr > 6:
            # don't overreact to sudden changes
            if smoothing > 0:
                if linear_smoothing:
                    # average of the last <smoothing> colors
                    r_window[i%smoothing] = r
                    g_window[i%smoothing] = g
                    b_window[i%smoothing] = b
                    r = 0
                    g = 0
                    b = 0
                    for w in range(smoothing):
                        r += r_window[w]
                        g += g_window[w]
                        b += b_window[w]
                    r = r / smoothing
                    g = g / smoothing
                    b = b / smoothing
                else:
                    # converge on the new color
                    r = (r_old * smoothing + r) / (smoothing + 1)
                    g = (g_old * smoothing + g) / (smoothing + 1)
                    b = (b_old * smoothing + b) / (smoothing + 1)

                if verbose_level >= 2:
                    print("smoothed color : ", r, " ", g, " ", b)

            # make sure to do this directly after the smoothing
            # 1. to not break non-linear smoothing
            # 2. because smoothing should not be stopped when
            # the screen color doesn't change between checks
            r_old = r
            g_old = g
            b_old = b

            # increase distance between darkest
            # and lightest channel in order to
            # increase saturation
            if increase_saturation > 0:
                min_val = min(min(r, g), b)
                old_max = max(max(r, g), b)
                r -= min_val * increase_saturation
                g -= min_val * increase_saturation
                b -= min_val * increase_saturation
                # max with 1 to prevent division by zero
                new_max = max(1, max(max(r, g), b))
                # normalize to old max value
                r = r * old_max / new_max
                g = g * old_max / new_max
                b = b * old_max / new_max
                if verbose_level >= 2:
                    print("saturated color: ", r, " ", g, " ", b)

            if normalize > 0:
                # normalize it so that the lightest value is e.g. full_on
                # max with 1 to prevent division by zero
                old_max
                if normalize_sum:
                    old_max = r + g + b
                else:
                    old_max = max(max(r, g), b)
                old_max = max(0.0, old_max)
                if old_max >= 0:
                    new_max = full_on
                    r = r * (1 - normalize) + r * new_max / old_max * normalize
                    g = g * (1 - normalize) + g * new_max / old_max * normalize
                    b = b * (1 - normalize) + b * new_max / old_max * normalize
                if verbose_level >= 2:
                    print("normalized color: ", r, " ", g, " ", b)

            # correct led color temperature
            # 1. gamma
            if gamma[0] > 0:
                r = pow(r / full_on, 1 / gamma[0]) * full_on
            if gamma[1] > 0:
                g = pow(g / full_on, 1 / gamma[1]) * full_on
            if gamma[2] > 0:
                b = pow(b / full_on, 1 / gamma[2]) * full_on
            # 2. brightness
            r = r * brightness[0]
            g = g * brightness[1]
            b = b * brightness[2]
            # 3. clip into color range
            r = min(full_on, max(0.0, r))
            g = min(full_on, max(0.0, g))
            b = min(full_on, max(0.0, b))
            if verbose_level >= 2:
                print("temperature fix: ", r, " ", g, " ", b)


            # for VERY dark colors, make it more gray to prevent supersaturated colors like (0, 1, 0).
            darkness = ((r_old + g_old + b_old) / 3) / full_on
            greyscaling = max(0.0, min(0.085, darkness) / 0.085)
            if greyscaling < 1:
                # for super dark colors, just use gray
                if darkness < 0.01:
                    greyscaling = 0
                # make dark colors more grey
                mean = (r + g + b) / 3
                r = (greyscaling) * r + (1 - greyscaling) * mean
                g = (greyscaling) * g + (1 - greyscaling) * mean
                b = (greyscaling) * b + (1 - greyscaling) * mean
                if verbose_level >= 2:
                    print("dark color fix : ", r, " ", g, " ", b)

            # send to the server for the illumination of the LEDs
            sendcolor(r, g, b, raspberry_ip, raspberry_port, checks_per_second, client_id, SCREEN_COLOR, max_timeout, last_message_timestamp, verbose_level)
        else:
            if verbose_level >= 1:
                print("color did not change or is too identical; skipping")

        # 1000000 is one second
        # the frequency of checks can require quite a lot of cpu usage,
        # don't only look for the server executable in your cpu usage,
        # also look for /usr/lib/Xorg cpu usage
        delta = get_us() - start
        if verbose_level >= 1:
            print("calculating and sending: ", delta, "us")
        if verbose_level >= 2:
            print("\n")
        # try to check the screen colors once every second (or whatever the checks_per_second param is)
        # so substract the delta or there might be too much waiting time between each check
        time.sleep(max(0, 1 / checks_per_second - delta / 1000000))

        # increment i, used for creating the window of colors for smoothing
        i += 1

    return 0

main(sys.argv)
