reads your screen contents and sends it to a remote raspberry that has single-color rgb lights connected to it

# dependencies

TODO, check when I deploy the whole thing onto the htpc

manjaro:

```
sudo pacman -S curl
```

# client

your htpc/pc/laptop running X11 and on which you watch youtube, netflix, amazon, etc., play games

`cd client && make`

# server

your raspberry

my rgb setup is this one: https://dordnung.de/raspberrypi-ledstrip/

```bash
sudo pigpiod
python server/server.py
```

# todo

make config file work

see what this xshmgetimage stuff is and if it is faster if it does something similar:
- https://stackoverflow.com/questions/43442675/how-to-use-xshmgetimage-and-xshmputimage 
- https://stackoverflow.com/questions/30200689/perfomance-of-xgetimage-xputimage-vs-xcopyarea-vs-xshmgetimage-xshmputima

