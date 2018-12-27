# Sezanlight

Reads your **X Window System Linux** screen contents and sends it to a remote raspberry that has single-color
rgb lights, which are controlled using one PWM gpio pin per R, G and B.

Since there is only a single color that needs to be figured out, the whole process can be kept minimalistic.
Therefore It's rather fast. It sparsly checks a few places on the screen (150 pixels by default) and puts
extra weight on those with high saturation and high lightness.

**worked with:**
- manjaro xfce
- manjaro cinnamon

## Dependencies

when using client.cpp:

arch/manjaro:

```
sudo pacman -S curl
```

when using client.py:

```
pip3 install python-xlib Pillow requests
```

## Usage

**1. set up your LEDs**

My RGB-strip setup is this one: https://dordnung.de/raspberrypi-ledstrip/

**2. clone**

Clone this repo on your pc and on your raspberry

```
git clone https://github.com/sezanzeb/sezanlight.git
```

**3. configuration (note that the config file does not work yet)**

In order to setup the config file, find out the ip of your raspberry using (execute on the raspberry):

```
ifconfig
```

It's usually something starting with 192.168.

Open the file called "config" on the client:

- for accurate results, increase lines and columns
- for a fast response, set smoothing to 1 or 0 and increase checks_per_second
- for a lightweight and smooth mode, set lines and columns low, smoothing to 1 and checks_per_second to 1
- for an accurate and smooth mode, increase checks_per_second, smoothing, lines and columns (e.g. 3, 3, 10 and 150)

And also insert the recently figured out ip of your raspberry

Copy the config file over to the raspberry server

**4. Client**

Your htpc/pc/laptop running X11 and on which you watch videos:

```
cd client && make && ./client.o
```

Or, I created a similar python client out of the cpp code:

```
cd client && python3 client.py
```

Use the one that works for you basically. Both seem to be about equally fast

**5. Server**

Your raspberry

```bash
sudo pigpiod
python3 server/server.py
```

**6. (optional) Add to autostart**

Once you know that the stuff is working you can go ahead and add it to autostart
if you want. This depends on your desktop environment and distro and hopefully
you are able to find out how to do this on the internet.

## TODO

docstrings

make config file work

- width and height should default to auto, which does exactly what auto implies
(what if somebody has two screens set up? will it crash when pixels in a dead area are checked)

see what this xshmgetimage stuff is and if it is faster if it does something similar:
- https://stackoverflow.com/questions/43442675/how-to-use-xshmgetimage-and-xshmputimage 
- https://stackoverflow.com/questions/30200689/perfomance-of-xgetimage-xputimage-vs-xcopyarea-vs-xshmgetimage-xshmputima

## Future

**1. single color mode**

Just setting a single color once.

**2. configuration tool**

Web frontend. Do some fancy javascript stuff like selecting a color from a color
wheel. The web frontend has the pro, that it could be opened on the smartphone
in order to change the rooms mood.

**3. visualize sound**

use one of the R, G and B channels for lows, mids and highs or something. Use bandpassing, lowcut and highcut for that.

per channel, use a sliding window and determine max value of abs of the samples in that window. Normalize it to
between 0 and 255. Send it to the raspberry afterwards.

Encode in the get request that the music mode is active so that the raspberry quickly reacts to the request instead of
fading it slowly.

This signal processing stuff I certainly will do in python and not in c++.

