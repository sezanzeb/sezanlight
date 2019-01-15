# Sezanlight

Reads your **X Window System Linux** screen contents and sends it to a remote raspberry that has single-color
rgb lights, which are controlled using one PWM gpio pin per R, G and B.

Since there is only a single color that needs to be figured out, the whole process can be kept minimalistic.
Therefore It's rather fast. It sparsly checks a few places on the screen (150 pixels by default) and puts
extra weight on those with high saturation and high lightness.

**worked with:**
- manjaro xfce

**somewhat worked with:**
- manjaro cinnamon (colors jumping on static images, xwd dumps also seem to be inconsistent)

## Usage

If this guide for some reason does not seem to be clear to you, if you are stuck or if something doesn't work,
don't hesitate to submit an issue on github.

**1. set up your LEDs**

My RGB-strip setup is this one: https://dordnung.de/raspberrypi-ledstrip/

**2. install**

Clone this repo on your pc and on your raspberry

```
git clone https://github.com/sezanzeb/sezanlight.git
```

on your client (the X11 device you use to watch videos, etc.), install the xlib and boost development headers

but I assume i'll write my own string trimming function later in order to remove the boost dependency

```
# arch/manjaro:
sudo pacman -S curl boost
```

**3. configuration**

In order to setup the config file, find out the ip of your raspberry using (execute on the raspberry):

```
ifconfig
```

It's usually something starting with 192.168.

Open the file called "config" on the client, insert the raspberries ip like this (example):

raspberry_ip=192.168.1.100

**4. Client**

Your htpc/pc/laptop running X11 and on which you watch videos:

```
cd client && make && ./client.o
```

Note, that the client stops sending when the server cannot be reached anymore.

**5. Server**

Your raspberry

```bash
sudo pigpiod
python3 server/server.py
```

The server accepts the colors from the most recently seen client and rejects colors
from older clients afterwards. As long as you don't have flatmates that try to mess with your
LEDs, this should be fine. (This also makes development for me easier as I don't have to take
care about stopping old clients anymore that run on a different machine)

**6. (optional) Add to autostart**

Once you know that the stuff is working you can go ahead and add it to autostart
if you want (both server and client). This depends on your desktop environment and
distro and hopefully you are able to find out how to do this on the internet.

Assuming you are running Raspbian on your pi (Debian based):

```bash
sudo cp initscript /etc/init.d/sezanlight
sudo sudo chmod 755 /etc/init.d/sezanlight
sudo update-rc.d sezanlight defaults
```

To test if the init file works at all:

```bash
sudo service sezanlight start
```

Set the Raspberries IP to a static one so that the client does not have to be reconfigured
later again. I did that in the raspberries dhcpcd.conf, which has lots of comments and
which is rather straightforward.

(It might be noteworthy that this breaks the internet connection of my pi, but for
some people it doesn't. But I was still able to connect to the local network so with
scp and ssh I was able to update the pi's server software.)

## Static Colors (Web Frontend)

Just setting a single color once. Type

```
192.168.2.110:3546
```

into your browser (replace 192.168.2.110:3546 with your raspberries local ip and the port on which the server is running)

and use the web tool

## Future

**configuration tool**

GTK tool for color wheel selection, config editing, mode selection. I want to use GTK because I'm a fan of xfce.

Web Frontend that runs on the raspberry, which can be accessed from any device in order to set the color statically.

**visualize sound**

use one of the R, G and B channels for lows, mids and highs or something. Use bandpassing, lowcut and highcut for that.

per channel, use a sliding window and determine max value of abs of the samples in that window. Normalize it to
between 0 and 255. Send it to the raspberry afterwards.

Encode in the get request that the music mode is active so that the raspberry quickly reacts to the request instead of
fading it slowly.

This signal processing stuff I certainly will do in python and not in c++.

## TODO

docstrings

see what this xshmgetimage stuff is and if it is faster if it does something similar:
- https://stackoverflow.com/questions/43442675/how-to-use-xshmgetimage-and-xshmputimage 
- https://stackoverflow.com/questions/30200689/perfomance-of-xgetimage-xputimage-vs-xcopyarea-vs-xshmgetimage-xshmputima