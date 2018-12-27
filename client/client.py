# this is a child of client.cpp

import PIL.Image # python-imaging
import PIL.ImageStat # python-imaging
import Xlib.display # python-xlib

import requests
import time

def sendcolor(r, g, b, ip, port, checks_per_second):
    url = "http://{}:{}?r={}&g={}&b={}&cps={}".format(ip, port, int(r), int(g), int(b), checks_per_second)
    print("sending GET pramas:", url)
    requests.get(url)


def main():

    # configuration
    width = 1920
    height = 1080
    normalize = False
    increase_saturation = True
    smoothing = 4
    checks_per_second = 3
    columns = 50
    lines = 3
    raspberry_ip = "192.168.2.110"
    raspberry_port = 8000

    # controls the resolution of the color space of the leds
    # default is 256, this is also configured in server.py
    full_on = 2048;

    # some checking for broken configurations
    if lines == 0:
        lines = 1
    if columns == 0:
        columns = 1
    if checks_per_second == 0:
        checks_per_second = 1

    root = Xlib.display.Display().screen().root

    r_old = 0
    g_old = 0
    b_old = 0

    while True:
    
        # XGetImage in c++ is the fastest solution i have come across
        
        # to make it even faster, ask for a single lines instead of a lot of points to reduce number of calls.
        # asking for lines also makes it quite flexible in where to place lines for color checks.
        # Asking for the whole screen is slow again. At least it seemed like that

        start = time.time()

        r = 1
        g = 1
        b = 1

        # count three lines on the screen or something
        for i in range(lines):
        
            # to prevent overflows, aggregate color for each line individually
            r_line = 0
            g_line = 0
            b_line = 0
            normalizer = 0
            
            x = 0
            y = int(height/(lines+1)*i)
            # note that ZPixmap works on cinnamon whereas XYPixmap does not
            image = root.get_image(x, y, width, 1, Xlib.X.ZPixmap, 0xffffffff)
            image_rgb = PIL.Image.frombytes("RGB", (width, 1), image.data, "raw", "BGRX")

            # e.g. is columns is 3, it will check the center pixel, and the centers between the center pixel and the two borders
            for x in range(0, width, width//columns):
                val = image_rgb.im[x]
                # lf_colour = PIL.ImageStat.Stat(image_rgb).mean
                # val = tuple(map(int, lf_colour))
                # scale color space according to full_on
                c_r = val[0] * (full_on/256)
                c_g = val[1] * (full_on/256)
                c_b = val[2] * (full_on/256)
                # give saturated colors (like green, purple, blue, orange, ...) more weight
                # over grey colors
                # difference between lowest and highest value should do the trick already
                diff = ((max(max(c_r, c_g), c_b) - min(min(c_r, c_g), c_b))) + 1
                # and also favor light ones over dark ones
                lightness = c_r + c_g + c_b + 1
                weight = diff * lightness
                normalizer += weight
                r_line += c_r * weight
                g_line += c_g * weight
                b_line += c_b * weight
            

            r += r_line / normalizer
            g += g_line / normalizer
            b += b_line / normalizer
        

        # r g and b are now between 0 and full_on
        r = int(r/lines)
        g = int(g/lines)
        b = int(b/lines)

        print("observed color  :", r, g, b)

        if increase_saturation:
        
            # increase distance between darkest
            # and lightest channel
            min_val = min(min(r, g), b)
            old_max = max(max(r, g), b)
            r -= min_val * 2 / 3
            g -= min_val * 2 / 3
            b -= min_val * 2 / 3
            # max with 1 to prevent division by zero
            new_max = max(1, max(max(r, g), b))
            # normalize to old max value
            r = r*old_max//new_max
            g = g*old_max//new_max
            b = b*old_max//new_max
            print("saturated color :", r, g, b)
        

        if normalize:
        
            # normalize it so that the lightest value is full_on
            # the leds are quite cold, so make the color warm
            # max with 1 to prevent division by zero
            max_val = max(1, max(max(r, g), b))
            r = r*full_on//max_val
            g = g*full_on//max_val
            b = b*full_on//max_val
            print("normalized color:", r, g, b)
        

        # don't overreact to sudden changes
        r = (r_old * smoothing + r)//(smoothing + 1)
        g = (g_old * smoothing + g)//(smoothing + 1)
        b = (b_old * smoothing + b)//(smoothing + 1)
        r_old = r
        g_old = g
        b_old = b

        # last step: correct led color temperature
        # 1. gamma
        g = int(pow(g/full_on, 1.2)*full_on)
        b = int(pow(b/full_on, 1.3)*full_on)
        # 2. lightness
        g = g * 10 // 13
        b = b * 10 // 17
        # red remains the same
        print("warmer color    :", r, g, b)

        # send to the server for display
        sendcolor(r, g, b, raspberry_ip, raspberry_port, checks_per_second)

        # 1000000 is one second
        # this of course greatly affects performance
        # don't only look for the server executable in your cpu usage,
        # also look for /usr/lib/Xorg cpu usage
        end = time.time()
        delta = end - start
        print("calculating and sending:", int(delta*1000000), "us", "\n")
        # try to check the screen colors once every second (or whatever the checks_per_second param is)
        # so substract the delta or there might be too much waiting time between each check
        time.sleep(max(0, 1/checks_per_second - delta))

    return 0

main()
