Reads your screen contents and sends it to a remote raspberry that has single-color rgb lights, which are controlled using one PWM gpio pin per R, G and B.

Using Xlib in c++ was the fastest way to read screen pixels I have come across. Since there is only a single color that needs to be figured out,
the whole process can be kept minimalistic. Therefore It's rather fast.

# dependencies

TODO, check when I deploy the whole thing onto the htpc

manjaro:

```
sudo pacman -S curl
```

# client

your htpc/pc/laptop running X11 and on which you watch youtube, netflix, amazon, etc., play games

`cd client && make && ./client.o`

the config file is only relevant for the client

# server

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

# todo

make config file work

see what this xshmgetimage stuff is and if it is faster if it does something similar:
- https://stackoverflow.com/questions/43442675/how-to-use-xshmgetimage-and-xshmputimage 
- https://stackoverflow.com/questions/30200689/perfomance-of-xgetimage-xputimage-vs-xcopyarea-vs-xshmgetimage-xshmputima

