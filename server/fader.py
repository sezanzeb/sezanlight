#!/usr/bin/env python3

import time
from threading import Thread, Semaphore

import pigpio
pi = pigpio.pi()

import traceback


class Fader(Thread):

    def __init__(self, gpio_r, gpio_g, gpio_b, full_on, logger):

        # the semaphore on order to maintain integrity of
        # smooth fading despite incoming requests
        self.working_on_color = Semaphore()

        self.gpio_r = gpio_r
        self.gpio_g = gpio_g
        self.gpio_b = gpio_b

        # color which is used as the fading starting color
        self.r_start = 0
        self.g_start = 0
        self.b_start = 0

        # color to fade into
        self.r_target = 0
        self.g_target = 0
        self.b_target = 0

        # current color during fading and statically
        self.r = 0
        self.g = 0
        self.b = 0

        # what is the maximum possible color value
        self.full_on = full_on

        # how fast the client reads their screen
        # default to 1 per second
        self.set_fading_speed(1)

        # how much progress the current fading already has
        self.fade_state = 0

        self.constant_since = time.time()

        # setup the PWM
        pi.set_PWM_range(gpio_r, full_on)
        pi.set_PWM_range(gpio_g, full_on)
        pi.set_PWM_range(gpio_b, full_on)
        # higher resolution for color changes
        # https://github.com/fivdi/pigpio/blob/master/doc/gpio.md
        self.gpio_freq_movie = 400 # lower frequencies increase duticycle resolution. 2500 colors
        self.gpio_freq_static = 2500 # 400 colors. Have that frequency higher to protect the eye
        self.current_freq = 0

        self.logger = logger

        # complete thread creation
        Thread.__init__(self)
        
            
    def set_freq(self, freq):
        """
            sets the frequency of the gpio PWM signal.
            Higher frequencies result in smaller resolution
            for color changes.
            https://github.com/fivdi/pigpio/blob/master/doc/gpio.md
        """
        # don't ask for pi.get_PWM_frequency as that might be different
        # from freq depending on the available frequencies
        if freq != self.current_freq:
            pi.set_PWM_frequency(self.gpio_r, freq)
            pi.set_PWM_frequency(self.gpio_g, freq)
            pi.set_PWM_frequency(self.gpio_b, freq)
            self.current_freq = freq
            self.logger.info('set gpio freq to {}hz'.format(pi.get_PWM_frequency(self.gpio_r)))


    def set_pwm_dutycycle(self, pin, value):
        pi.set_PWM_dutycycle(pin, max(1, value))
        # pi.hardware_PWM(pin, 800, int(1000000//(full_on/value)))


    def set_target(self, r, g, b, cps=1, mode='static'):
        """
            sets a new target to fade into. Takes the current color
            and uses it as the new starting point.

            cps is the number of targets that the client will try to
            send approximately per second, or rather, how fast the
            color should fade.

            mode can be 'static' or 'movie'.
        """

        # By how many percent/100 of full_on does the color need to change
        # in order to trigger a change of the LEDs?
        # 'movie': Don't fade when the color delta is not large enough to fade smoothly.
        # 'static': Always change the color on a new static-color request
        threshold = {'movie': 0.015, 'static': 0}[mode]

        thres_r = abs(r - self.r_target) > self.full_on * threshold
        thres_g = abs(g - self.g_target) > self.full_on * threshold
        thres_b = abs(b - self.b_target) > self.full_on * threshold

        if thres_r or thres_g or thres_b:
            self.working_on_color.acquire()
            self.set_fading_speed(cps)
            self.r_target = max(0, min(self.full_on, r))
            self.g_target = max(0, min(self.full_on, g))
            self.b_target = max(0, min(self.full_on, b))
            # start where fading has just been
            self.r_start = self.r
            self.g_start = self.g
            self.b_start = self.b
            self.fade_state = 0

            # Higher frequency for static colors to potentially protect the eye.
            # Lower ones for movies for smoother fading.
            if mode == 'movie':
                self.set_freq(self.gpio_freq_movie)
            elif mode == 'static':
                self.set_freq(self.gpio_freq_static)

            self.constant_since = time.time()
            self.working_on_color.release()
        else:
            self.logger.info('delta color change was <= {}%'.format(threshold * 100))


    def set_fading_speed(self, checks_per_second, fader_frequency=200):
        """
            Changes the smoothness and speed of the fading.
            Will continue to fade into the current target color.
        """
        self.checks_per_second = max(1, checks_per_second)
        # how often the fader will iterate in order to
        # fade from start to target color
        self.checks = max(1, int(fader_frequency / self.checks_per_second) - 1)
        # self.fade_state = 0
        self.r_start = self.r
        self.g_start = self.g
        self.b_start = self.b


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

                    # Add old and new color together proportionally
                    # so that a fading effect is created.
                    # Overwrite globals r, g and b so that when fading restarts,
                    # that is going to be the new starting color.
                    self.r = (self.r_start * (1 - self.fade_state) + self.r_target * self.fade_state)
                    self.g = (self.g_start * (1 - self.fade_state) + self.g_target * self.fade_state)
                    self.b = (self.b_start * (1 - self.fade_state) + self.b_target * self.fade_state)
                    self.set_pwm_dutycycle(self.gpio_r, self.r)
                    self.set_pwm_dutycycle(self.gpio_g, self.g)
                    self.set_pwm_dutycycle(self.gpio_b, self.b)
                    # logger.info('{} {} {}'.format(r, g, b))

                else:
                    # after 3 minutes increase the LED frequency
                    # in order to protect the eye
                    if time.time() - self.constant_since > 180:
                        # reduces resolution, so the color will
                        # make a visible jump if it is a dark one
                        self.set_freq(self.gpio_freq_static)
                    # the server will take care of setting the
                    # frequency back to gpio_freq_movie

                    # self.set_pwm_dutycycle(self.gpio_r, self.r_target)
                    # self.set_pwm_dutycycle(self.gpio_g, self.g_target)
                    # self.set_pwm_dutycycle(self.gpio_b, self.b_target)

            self.working_on_color.release()

            delta = time.time() - start
            time.sleep(max(0, 1 / self.checks_per_second / (self.checks + 1) - delta))
