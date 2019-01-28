# Sezanlight

Reads your **X Window System Linux** screen contents and sends it to a remote raspberry that has single-color
rgb lights, which are controlled using one PWM gpio pin per R, G and B.

Since there is only a single color that needs to be figured out, the whole process can be kept minimalistic.
Therefore It's rather fast. It sparsly checks a few places on the screen (150 pixels by default) and puts
extra weight on those with high saturation.

When the color on the LEDs doesn't change or is supposed to be static, a higher LED frequency of 2500hz is used to reduce
eye strain https://www.notebookcheck.net/Why-Pulse-Width-Modulation-PWM-is-such-a-headache.270240.0.html otherwise it is
set to 400hz in order to provide smooth fading colors (lower frequency results in higher resolution PWM dutycicle adjustments)

**worked with:**
- manjaro xfce

**somewhat worked with:**
- manjaro cinnamon (colors jumping on static images, xwd dumps also seem to be inconsistent)

<p align="center">
<img src="https://github.com/sezanzeb/sezanlight/blob/master/screenshots/gtk.png">
<img src="https://github.com/sezanzeb/sezanlight/blob/master/screenshots/web.png">
</p>

## Usage

see https://github.com/sezanzeb/sezanlight/blob/master/install.md

## Static Colors (Web Frontend)

Just setting a single color once. Type

```
192.168.2.110:3546
```

into your browser (replace 192.168.2.110:3546 with your raspberries local ip and the port on which the server is running)

and use the web tool

## Future

**configuration tool**

GTK tool for color wheel selection, config editing, mode selection. I want to use GTK because I'm a fan of xfce.

Web Frontend that runs on the raspberry, which can be accessed from any device in order to set the color statically.

**visualize sound**

use one of the R, G and B channels for lows, mids and highs or something. Use bandpassing, lowcut and highcut for that.

per channel, use a sliding window and determine max value of abs of the samples in that window. Normalize it to
between 0 and 255. Send it to the raspberry afterwards.

Encode in the get request that the music mode is active so that the raspberry quickly reacts to the request instead of
fading it slowly.

This signal processing stuff I certainly will do in python and not in c++.

see what this xshmgetimage stuff is and if it is faster if it does something similar:
- https://stackoverflow.com/questions/43442675/how-to-use-xshmgetimage-and-xshmputimage 
- https://stackoverflow.com/questions/30200689/perfomance-of-xgetimage-xputimage-vs-xcopyarea-vs-xshmgetimage-xshmputima
