#!/usr/bin/env python3

import traceback
import time
from threading import Thread, Semaphore
from logger import logger

import pigpio
pi = pigpio.pi()


HW_CHANNEL1 = 13  # shared with 19
HW_CHANNEL2 = 12  # shared with 18


# ideas and notes for configuration:
# - upon starting the server, the logger will print an info message about
#   the resolution of the gpios. It should definitely be >= 2000. Increase it
#   by lowering the frequency. Very low frequencies cause stroboscope effects.
# - I tried to set it up in such a way that:
#       B has the highest resolution, so that dark (blue) night sceneries don't make
#         the color fades choppy
#       G has the highest frequency, as humans are very sensitive to green, so that
#         the eye strain caused by PWM is as low as possible (i'm not an eye doctor,
#         idk if that actually makes sense)
#       R uses normal non-hardware gpio, because there are only two hardware channels.
#         trying a nice setup with an ok resolution and an ok PWM frequency
# - set static colors to higher pwm frequencies to reduce eye strain if you
#   illuminate your room for a long period of time
# - feel free to set hardware gpio frequencies much higher, they still have a
#   fairly high resolution
# - since non-hardware gpios have a lower resolution, the threshold should
#   be higher for color changes to be visible, otherwise the color starts jumping
#   when it becomes dark

# pin layout: https://siminnovations.com/wiki/index.php?title=General_Raspberry_Pi_I/O_pin_explanation
# there are only 2 hardware channels and 2 pins per channel or something. so red
# has to use non-hardware controlled gpios in this setup
# https://raspberrypi.stackexchange.com/a/64257
# https://github.com/fivdi/pigpio/blob/master/doc/gpio.md

config = {
    'r': {
        'pin': 17,
        'freqs': {
            'continuous': 500,
            'static': 2000
        },
        'threshold': 0.025
    },
    'g': {
        'pin': HW_CHANNEL1,
        'freqs': {
            'continuous': 3000,
            'static': 4000
        },
        'threshold': 0.005
    },
    'b': {
        'pin': HW_CHANNEL2,
        'freqs': {
            'continuous': 1500,
            'static': 4000
        },
        'threshold': 0.005
    }
}


class Fader(Thread):

    def __init__(self):

        self.logger = logger

        # the semaphore on order to maintain integrity of
        # smooth fading despite incoming requests
        self.working_on_color = Semaphore()

        # color to fade into
        self.target_color = [0, 0, 0]

        # current color during fading and statically
        self.current_color = [0, 0, 0]

        # color which is used as the fading starting color. Changes
        # to current at that moment.
        self.start_color = [0, 0, 0]

        # what is the maximum possible color value
        # http://abyz.me.uk/rpi/pigpio/python.html#set_PWM_range
        # (I think this has really absolutely no effect, it's just
        # for convenience so you don't have to convert between ranges
        # i guess. If you set it too low you limit the resolution though)
        # Make sure to set this to the same value as in the clients code.
        # I don't think hardware PWMs are affected by this. They always
        # use a value of 1000000 instead.
        self.range = 20000

        # how fast the client reads their screen
        # default to 1 per second
        self.set_fading_speed(1)

        # how much progress the current fading already has
        self.fade_state = 0

        self.constant_since = time.time()

        self.current_color_mode = None

        # setup the PWM
        pi.set_PWM_range(config['r']['pin'], self.range)
        pi.set_PWM_range(config['g']['pin'], self.range)
        pi.set_PWM_range(config['b']['pin'], self.range)
        self.set_freq('continuous')
        self.set_pwm_dutycycle([0, 0, 0])

        logger.info('resolutions of channels in continuous mode:')
        logger.info('- r: {}'.format(pi.get_PWM_real_range(config['r']['pin'])))
        logger.info('- g: {}'.format(pi.get_PWM_real_range(config['g']['pin'])))
        logger.info('- b: {}'.format(pi.get_PWM_real_range(config['b']['pin'])))

        # complete thread creation
        Thread.__init__(self)

    def get_color(self, normalize=255):
        return [self.current_color[c] * normalize / self.range for c in range(3)]

    def set_freq(self, mode):
        """
            sets the frequency of the gpio PWM signal.
            Higher frequencies result in smaller resolution
            for color changes.
            https://github.com/fivdi/pigpio/blob/master/doc/gpio.md

            mode: one of 'static' or 'continuous'
        """
        # don't ask for pi.get_PWM_frequency as that might be different
        # from freq depending on the available frequencies
        if mode != self.current_color_mode:
            pi.set_PWM_frequency(
                config['r']['pin'], config['r']['freqs'][mode])
            pi.set_PWM_frequency(
                config['g']['pin'], config['g']['freqs'][mode])
            pi.set_PWM_frequency(
                config['b']['pin'], config['b']['freqs'][mode])
            self.current_color_mode = mode
            self.logger.info('switching to {} mode'.format(mode))

    def set_pwm_dutycycle(self, values):
        """
            values is an array of floats for [r, g, b]
            between 0 and self.range

            changes the color of the LEDs instantly
        """
        hardware_pins = [12, 18, 13, 19]

        for c, color in enumerate(['r', 'g', 'b']):
            pin = config[color]['pin']
            freq = config[color]['freqs'][self.current_color_mode]
            value = values[c]

            if pin in hardware_pins:
                # 1000000 is fully on
                pi.hardware_PWM(pin, freq, int(1000000 * value / self.range))
            else:
                pi.set_PWM_dutycycle(pin, max(1, value))

    def set_target(self, values, cps=1, mode='static'):
        """
            sets a new target to fade into. Takes the current color
            and uses it as the new starting point.

            values is an array of floats for [r, g, b]
            between 0 and self.range

            cps is the number of targets that the client will try to
            send approximately per second, or rather, how fast the
            color should fade.

            mode can be 'static' or 'continuous'.
        """

        # By how many percent of range does the color need to change
        # in order to trigger a change of the LEDs?
        # 'continuous': Don't fade when the color delta is not large enough to fade smoothly.
        # 'static': Always change the color on a new static-color request

        self.working_on_color.acquire()

        change_happened = False

        for c, color in enumerate(['r', 'g', 'b']):
            delta = abs(values[c] - self.target_color[c])
            if delta > config[color]['threshold']:
                self.target_color[c] = max(0, min(self.range, values[c]))
                change_happened = True

        if change_happened:
            self.set_fading_speed(cps)
            self.set_freq(mode)
            self.constant_since = time.time()
            # start where fading has just been
            self.start_color = self.current_color.copy()
            self.fade_state = 0
        else:
            self.logger.info(
                'delta color change was below the threshold')

        self.working_on_color.release()

    def set_fading_speed(self, checks_per_second, fader_frequency=60):
        """
            Changes the smoothness and speed of the fading.
            Will continue to fade into the current target color.
        """
        self.checks_per_second = max(1, checks_per_second)
        # how often the fader will iterate in order to
        # fade from start to target color
        self.checks = max(1, int(fader_frequency / self.checks_per_second) - 1)
        # self.fade_state = 0
        self.start_color = self.current_color.copy()

    def run(self):
        """
            This loop iterates like crazy in the specified frequency.
            It just takes the members of this object and fades from
            start to target colors
        """

        while True:

            start = time.time()
            # f will move from 0 to 1

            self.working_on_color.acquire()

            if self.checks >= 1:

                if self.fade_state < 1:

                    self.fade_state += 1 / self.checks
                    if self.fade_state > 1:
                        # the fade_state might have been something like 0.99999
                        # when it should be 1. Avoid this problem by another check for > 1
                        # after increasing the fade_state. Also make sure fade_state is in
                        # consistent state when finished, hence min(1, ...) it
                        self.fade_state = min(1, self.fade_state)
                    else:
                        # Add old and new color together proportionally
                        # so that a fading effect is created.
                        # Overwrite globals r, g and b so that when fading restarts,
                        # that is going to be the new starting color.
                        self.current_color = [
                            self.start_color[c] * (1 - self.fade_state) +
                            self.target_color[c] * self.fade_state
                            for c in range(3)
                        ]
                        # print(self.fade_state, self.r_target, self.g_target, self.b_target)
                        self.set_pwm_dutycycle(self.current_color)
                        # logger.info('{} {} {}'.format(r, g, b))

                else:
                    # after 3 minutes increase the LED frequency
                    # in order to protect the eye
                    if time.time() - self.constant_since > 180:
                        # reduces resolution, so the color will
                        # make a visible jump if it is a dark one
                        self.set_freq('static')
                    # the server will take care of setting the
                    # frequency back to gpio_freq_continuous

            self.working_on_color.release()

            delta = time.time() - start
            time.sleep(max(0, 1 / self.checks_per_second /
                           (self.checks + 1) - delta))
