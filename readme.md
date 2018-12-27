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

manjaro:

```
sudo pacman -S curl
```

## Client

your htpc/pc/laptop running X11 and on which you watch videos:

`cd client && make && ./client.o`

or, I created a similar python client out of the cpp code:

`cd client && python3 client.py`

use the one that works for you basically

## Server

your raspberry

my RGB-strip setup is this one: https://dordnung.de/raspberrypi-ledstrip/

```bash
sudo pigpiod
python3 server/server.py
```

in order to setup the config file, find out the ip of your raspberry using (execute on the raspberry):

```
ifconfig
```

it's usually something starting with 192.168.

## TODO

make config file work

see what this xshmgetimage stuff is and if it is faster if it does something similar:
- https://stackoverflow.com/questions/43442675/how-to-use-xshmgetimage-and-xshmputimage 
- https://stackoverflow.com/questions/30200689/perfomance-of-xgetimage-xputimage-vs-xcopyarea-vs-xshmgetimage-xshmputima

**guide: (note that the config file does not work yet)**
- for accurate results, increase lines and columns
- for a fast response, set smoothing to 1 or 0 and increase checks_per_second
- for a lightweight and smooth mode, set lines and columns low, smoothing high and checks_per_second to 1

## Future

visualize sound

use one of the R, G and B channels for lows, mids and highs or something. Use bandpassing, lowcut and highcut for that.

per channel, use a sliding window and determine max value of abs of the samples in that window. Normalize it to
between 0 and 255. Send it to the raspberry afterwards.

Encode in the get request that the music mode is active so that the raspberry quickly reacts to the request instead of
fading it slowly.

This signal processing stuff I certainly will do in python and not in c++.
