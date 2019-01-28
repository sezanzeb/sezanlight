
# usage/installation

If this guide for some reason does not seem to be clear to you, if you are stuck or if something doesn't work,
don't hesitate to submit an issue on github.

## 1. set up your LEDs

My RGB-strip setup is this one: https://dordnung.de/raspberrypi-ledstrip/

## 2. Server

Your raspberry

```bash
sudo pigpiod -s 1
git clone https://github.com/sezanzeb/sezanlight.git
cd sezanlight
python3 server/server.py
```

Edit the config file in the repositories root if you are using gpios different from 1. or
some port other than 3546.

The server accepts the colors from the most recently seen client and rejects colors
from older clients afterwards. As long as you don't have flatmates that try to mess with your
LEDs, this should be fine. (This also makes development for me easier as I don't have to take
care about stopping old clients anymore that run on a different machine)

## 3. Client

on your client (the X11 device you use to watch videos, etc.):

for arch/manjaro:

```
cd install
makepkg --install
```

if you are using something different, take a look at manual_install.md

to **uninstall**, use `pacman -R sezanlight`

## 4. (optional) Add server to raspberries autostart

Once you know that the stuff is working you can go ahead and add it to autostart
if you want on the pi.

**4.1 init.d service**

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

And try to set some color from the client using the web or the gtk tool

**4.2 static local raspberry ip**

Set the Raspberries IP to a static one so that the client does not have to be reconfigured
later again. I did that in the raspberries dhcpcd.conf, which has lots of comments and
which is rather straightforward.

(This broke the internet connection of my pi until I set up the routers IP address in dhcpcd.conf)

like so (insert your ips):

```
interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
```