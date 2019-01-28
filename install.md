
# usage/installation

If this guide for some reason does not seem to be clear to you, if you are stuck or if something doesn't work,
don't hesitate to submit an issue on github.

---

## 1. set up your LEDs

My RGB-strip setup is this one: https://dordnung.de/raspberrypi-ledstrip/

---

## 2. Server

Your raspberry

```bash
sudo pigpiod -s 1
git clone https://github.com/sezanzeb/sezanlight.git
cd sezanlight
python3 server/server.py
```

The server accepts the colors from the most recently seen client and rejects colors
from older clients afterwards. As long as you don't have flatmates that try to mess with your
LEDs, this should be fine. (This also makes development for me easier as I don't have to take
care about stopping old clients anymore that run on a different machine)

---

## 3. Client

on your client (the X11 device you use to watch videos, etc.):

**3.1 clone**

```
git clone https://github.com/sezanzeb/sezanlight.git
```

**3.2 dependencies**

install the xlib, curl and boost development headers

but I assume i'll write my own string trimming function later in order to remove the boost dependency

manjaro/arch:
```
sudo pacman -S curl boost libx11
```

ubuntu/debian (NOT TESTED):
```
sudo apt install libx11-dev libcurl4-openssl-dev libboost-atomic-dev
```

**3.3 configuration**

In order to setup the config file, find out the **ip of your raspberry** using e.g. `ifconfig` while in ssh on the raspberry, or:

```
sudo arp-scan --localnet
```

which gives you something like `192.168.1.100 ab:cd:ef:12:34:56 Raspberry Pi Foundation`

Open the file called "config" on the client (comes with this repository), insert the raspberries ip like this (example):

raspberry_ip=192.168.1.100

**3.4 compilation and running**

then compile the source and run the client. cd to the cloned repository:

```
cd client && make
```

to run either

```
./client.o ../config
```

or

```
python3 gtk.py
```

Note, that the client stops sending when the server cannot be reached anymore, so make
sure to start the server before the client.

---

## 4. (optional) Add to autostart

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