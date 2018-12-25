reads your screen contents and sends it to a remote raspberry that has single-color rgb lights connected to it

# dependencies

TODO, check when I deploy the whole thing onto the htpc

manjaro:

```
sudo pacman -S curl
```

# client

your htpc/pc/laptop running X11 and on which you watch youtube, netflix, amazon, etc., play games

TODO:

add setup file to add ip of raspberry

send data to server

`cd client && make`

# server

your raspberry

my rgb setup is this one: https://dordnung.de/raspberrypi-ledstrip/

```bash
sudo pigpiod
python server/server.py
```

TODO:

not yet implemented

add config file for which gpio pins should be used