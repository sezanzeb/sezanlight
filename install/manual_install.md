# Manually Installing the Client on Ubuntu

## 1. Installation

```Bash
sudo apt install git g++ make libx11-dev libcurl4-openssl-dev libboost-dev
git clone https://github.com/sezanzeb/sezanlight.git
cd sezanlight
sudo install -D client/gtk.py /usr/bin/sezanlight
sudo install -D client/client.py /usr/bin/sezanlight_screen_client
install -D --owner=$USER config $HOME/.config/sezanlight/config
sudo install -D install/sezanlight.desktop /usr/share/applications/sezanlight.desktop
cd ../
sudo rm sezanlight -r
```

Type

```
sezanlight
```

Into your console to see if the window pops up. Also see if there is a startmenu entry available for "sezanlight"

**You still need to install the server on the raspberry!** see install.md for that.

## 2. Configuration

In order to setup the config file, find out the **ip of your raspberry** using e.g. `ifconfig` while in ssh on the raspberry, or:

```Bash
sudo arp-scan --localnet
```

which might give you something like `192.168.1.100 ab:cd:ef:12:34:56 Raspberry Pi Foundation`. Then, run:

```Bash
sezanlight
```

and click on 'edit config'

insert the raspberries ip like this (example): `raspberry_ip=192.168.1.100`

## 3. Uninstall

```Bash
sudo rm /usr/bin/sezanlight /usr/bin/sezanlight_screen_client /usr/share/applications/sezanlight.desktop ~/.config/sezanlight -r
```