web front-end:
- sets the color of the LEDs
- can restart the server from the web app
- can edit config from the web app
- the sliders jump to the color that is currently set on the screen on load
- previews the LED color set by the sliders

server:
- handles overlapping streams of screen colors by canceling the older one
- provides endpoints for reading and setting colors, both static and as continuous "stream" of data
- provides endpoints for changing the configuration and for restarting
- is a small custom framework to add new endpoints to pythons base http handler
- fades colors in an extra thread, which the server can control. when color
streams send messages in varying intervals, the fader still fades smoothly without
delaying the display of the current target color

gtk client:
- tool to start sending screen color to the server, which also takes care of
correcting the colortemperature
- and can send static colors
- shows timeout problems to the user
