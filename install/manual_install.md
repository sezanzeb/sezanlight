**1. clone**

```
git clone https://github.com/sezanzeb/sezanlight.git
```

**2. dependencies**

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

**3. configuration**

In order to setup the config file, find out the **ip of your raspberry** using e.g. `ifconfig` while in ssh on the raspberry, or:

```
sudo arp-scan --localnet
```

which gives you something like `192.168.1.100 ab:cd:ef:12:34:56 Raspberry Pi Foundation`

Open the file called "config" on the client (comes with this repository), insert the raspberries ip like this (example):

raspberry_ip=192.168.1.100

**4. compilation and running**

then compile the source and run the client. cd to the cloned repository:

```
cd client && make
python3 gtk.py
```

Note, that the client stops sending when the server cannot be reached anymore, so make
sure to start the server before the client.