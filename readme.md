# Sezanlight

Reads your **X Window System Linux** screen contents and sends it to a remote raspberry that has single-color
rgb lights, which are controlled using one PWM gpio pin per R, G and B.

It sparsly checks a few places on the screen (150 pixels by default) and puts extra weight on those with high saturation.

When the color on the LEDs doesn't change or is supposed to be static, a higher LED frequency of 2500hz is used to reduce
eye strain https://www.notebookcheck.net/Why-Pulse-Width-Modulation-PWM-is-such-a-headache.270240.0.html otherwise it is
set to 400hz in order to provide smooth fading colors (lower frequency results in higher resolution PWM dutycicle adjustments)

**worked with:**
- manjaro xfce

**somewhat worked with:**
- manjaro cinnamon (colors jumping on static images, xwd dumps also seem to be inconsistent)

<p align="center">
  <img src="https://github.com/sezanzeb/sezanlight/blob/master/screenshots/gtk.png">
</p>
<p align="center">
  <img src="https://github.com/sezanzeb/sezanlight/blob/master/screenshots/photo.jpg">
</p>
<p align="center">
  <img src="https://github.com/sezanzeb/sezanlight/blob/master/screenshots/web.png">
</p>

## Usage

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
