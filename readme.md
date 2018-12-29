# Sezanlight

Reads your **X Window System Linux** screen contents and sends it to a remote raspberry that has single-color
rgb lights, which are controlled using one PWM gpio pin per R, G and B.

Since there is only a single color that needs to be figured out, the whole process can be kept minimalistic.
Therefore It's rather fast. It sparsly checks a few places on the screen (150 pixels by default) and puts
extra weight on those with high saturation and high lightness.

**worked with:**
- manjaro xfce (using compton)

**somewhat worked with:**
- manjaro cinnamon (colors jumping on static images, xwd dumps also seem to be inconsistent)

## Usage

**1. set up your LEDs**

My RGB-strip setup is this one: https://dordnung.de/raspberrypi-ledstrip/

**2. install**

Clone this repo on your pc and on your raspberry

```
git clone https://github.com/sezanzeb/sezanlight.git
```

on your client (the X11 device you use to watch videos, etc.), install the xlib development headers

```
# arch/manjaro:
sudo pacman -S curl
```
```
# on debian/ubuntu, it probably is:
sudo apt install libcurl-dev
```

**3. configuration**

In order to setup the config file, find out the ip of your raspberry using (execute on the raspberry):

```
ifconfig
```

It's usually something starting with 192.168.

Open the file called "config" on the client, insert the raspberries ip like this (example):

raspberry_ip=192.168.1.100

And also insert the recently figured out ip of your raspberry

Copy the config file over to the raspberry server

**4. Client**

Your htpc/pc/laptop running X11 and on which you watch videos:

```
cd client && make && ./client.o
```

**5. Server**

Your raspberry

```bash
sudo pigpiod
python3 server/server.py
```

**6. (optional) Add to autostart**

Once you know that the stuff is working you can go ahead and add it to autostart
if you want (both server and client). This depends on your desktop environment and
distro and hopefully you are able to find out how to do this on the internet.

Tutorial for raspberry: https://tutorials-raspberrypi.com/raspberry-pi-autostart-start-program-automatically/

```
# see link above for complete contents of file
# part of the contents of /etc/init.d/sezanlight
case "$1" in
    start)
        sudo pigpiod
        python3 /home/pi/sezanlight/server/server.py
```

Set the Raspberries IP to a static one so that it does not have to be reconfigured
later again. I did that in dhcpcd.conf, which has lots of comments and which is rather
straightforward.

(It might be noteworthy that this breaks the internet connection of my pi,
but for some people it doesn't. But I was still able to connect to the local network so with scp I was able to update the pi's server software.)

## Static Colors

Just setting a single color once. At the moment this can be done by typing this:

```
192.168.2.110:3546?r=2048&g=1024&b=0&cps=2
```

into your browser (replace 192.168.2.110:3546 with your raspberries local ip and the port on which the server is running)

## Future

**configuration tool**

GTK tool for color wheel selection, config editing, mode selection. I want to use GTK because I'm a fan of xfce.

Signal to server when another client started fading, so that two clients are not conflicting each other and the old one
can be stopped. For this, assign an id to each client and only fade, when the request comes in from the newest client id.

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

make config file work

- width and height should default to auto, which does exactly what auto implies
(what if somebody has two screens set up? will it crash when pixels in a dead area are checked)

see what this xshmgetimage stuff is and if it is faster if it does something similar:
- https://stackoverflow.com/questions/43442675/how-to-use-xshmgetimage-and-xshmputimage 
- https://stackoverflow.com/questions/30200689/perfomance-of-xgetimage-xputimage-vs-xcopyarea-vs-xshmgetimage-xshmputima