# Sezanlight

Reads your **X Window System Linux** screen contents and sends it to a remote raspberry
that has single-color rgb lights, which are controlled using one PWM gpio pin per R, G and B.

It sparsly checks a few places on the screen (250 pixels by default) and puts extra weight
on those with high saturation.

**worked with:**
- manjaro xfce
- xubuntu

**somewhat worked with:**
- manjaro cinnamon (colors jumping on static images, xwd dumps also seem to be inconsistent)

<p align="center">
  <img src="https://github.com/sezanzeb/sezanlight/blob/master/screenshots/gtk.png">
</p>
<p align="center">
  <img src="https://github.com/sezanzeb/sezanlight/blob/master/screenshots/web.png">
</p>
<p align="center">
  <img src="https://github.com/sezanzeb/sezanlight/blob/master/screenshots/photo.jpg">
</p>

## Usage, Installation, Setup

see https://github.com/sezanzeb/sezanlight/blob/master/install/install.md

## Static Colors (Web Frontend)

Just setting a single color once. Type

```
192.168.1.100:3546
```

into your browser (replace 192.168.1.100:3546 with your raspberries local ip and the port on which the server is running)

and use the web tool. You can also use this to check if the server works, as no configuration on the client is needed for that.

## Future

see what this xshmgetimage stuff is and if it is faster if it does something similar:
- https://stackoverflow.com/questions/43442675/how-to-use-xshmgetimage-and-xshmputimage 
- https://stackoverflow.com/questions/30200689/perfomance-of-xgetimage-xputimage-vs-xcopyarea-vs-xshmgetimage-xshmputima

## Problems

**If you don't want to use the two hardware controlled gpio channels** (as currently done in server/fader.py since their
resolution is super high and hence they fade super smooth even for dark colors):

Dark colors are difficult if you have a lot of LEDs. They enable you to make bright static
colors but on movies too bright LEDs are undesired. So the gamma and/or brightness needs to
be reduced, which reduces the size of the space of available colors. Hence the fading becomes
more jaggy, which is very noticable on dark colors. Even though I have done my best to provide
an experience as pleasing as possible for dark colors, you might want to consider to only have
half as many LEDs as I have (I have 150 SMD 5050 12v LEDs) if you only want to watch movies
and not illuminate your room.

I would love to have a high PWM frequency to eliminate all the potential eye strain, however, this would
also reduce the resolution of duty cicles that can be set. A possible setup would be:
- 400hz for movies/computer screens to provide higher resolution color fades
- 2000hz for static colors to reduce potential eye strain. The server automatically switches to 2000hz if the color doesn't change for a long enough period of time

The colors flicker when the Raspberry is under (network?) load (noticable when e.g. sending long terminal outputs over ssh via cat or similar). The flickers become more noticable on high PWM frequencies. Hence I needed to try to reduce the network traffic as much as possible (which also saves computational time in the server code) and also I cannot set the static frequency any higher.