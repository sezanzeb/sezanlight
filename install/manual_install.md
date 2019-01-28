# Manually Installing the Client on Ubuntu (NOT TESTED)

**1. installation**

```
sudo apt install libx11-dev libcurl4-openssl-dev libboost-atomic-dev
git clone https://github.com/sezanzeb/sezanlight.git
cd sezanlight/client
make
cd ../
install -D client/gtk.py /usr/bin/sezanlight
install -D client/client.o /usr/bin/sezanlight_screen_client
install -D --owner=$USER config $HOME/.config/sezanlight/config
install -D install/sezanlight.desktop /usr/share/applications/sezanlight.desktop
```

Type

```
sezanlight
```

Into your console to see if the window pops up. Also see if there is a startmenu entry available for "sezanlight"

**You still need to install the server on the raspberry!** see install.md for that.

**2. configuration**

In order to setup the config file, find out the **ip of your raspberry** using e.g. `ifconfig` while in ssh on the raspberry, or:

```
sudo arp-scan --localnet
```

which might give you something like `192.168.1.100 ab:cd:ef:12:34:56 Raspberry Pi Foundation`. Then, run:

```
sezanlight
```

and click on 'edit config'

insert the raspberries ip like this (example): `raspberry_ip=192.168.1.100`