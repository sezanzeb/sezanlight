#!/usr/bin/env python3

# GTK application for configuration and to start client.cpp

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import subprocess
import sys
import os
from pathlib import Path
import requests
import configparser
from shutil import copyfile

# GTK:
# https://python-gtk-3-tutorial.readthedocs.io/en/latest/introduction.html
# https://www.tutorialspoint.com/pygtk/pygtk_hello_world.htm
# https://python-gtk-3-tutorial.readthedocs.io/en/latest/layout.html
# https://python-gtk-3-tutorial.readthedocs.io/en/latest/button_widgets.html#switch
# https://lazka.github.io/pgi-docs/Gtk-3.0/classes.html

# https://stackoverflow.com/questions/89228/calling-an-external-command-in-python#2251026

class LEDClient(Gtk.Window):

    def __init__(self):
        super(LEDClient, self).__init__()
        self.set_title('LED Client')
        self.set_border_width(10)
        self.set_icon_name('preferences-desktop-display')

        # switch to start and stop the client that reads screen colors
        switch = Gtk.Switch()
        switch.connect('notify::active', self.on_switch_activated)
        switch.set_active(False)
        self.switch = switch
        switch_label = Gtk.Label(label='capture screen colors:')

        # button to xdg-open the config file
        config_button = Gtk.Button(label='edit config')
        config_button.connect('clicked', self.open_config)

        # input for r, g and b
        rgb_box = Gtk.Box(spacing=10)
        static_button = Gtk.Button(label='set static color')
        static_button.connect('clicked', self.set_static_color)

        r_entry = Gtk.Entry()
        r_entry.set_text('0')
        r_label = Gtk.Label(label='r:')
        r_entry.set_width_chars(4)
        rgb_box.add(r_label)
        rgb_box.add(r_entry)
        self.r_entry = r_entry

        g_entry = Gtk.Entry()
        g_entry.set_text('0')
        g_label = Gtk.Label(label='g:')
        g_entry.set_width_chars(4)
        rgb_box.add(g_label)
        rgb_box.add(g_entry)
        self.g_entry = g_entry

        b_entry = Gtk.Entry()
        b_entry.set_text('0')
        b_label = Gtk.Label(label='b:')
        b_entry.set_width_chars(4)
        rgb_box.add(b_label)
        rgb_box.add(b_entry)
        self.b_entry = b_entry

        separator1 = Gtk.HSeparator()
        separator2 = Gtk.HSeparator()

        # beautifully align everything
        grid = Gtk.Grid()
        grid.props.valign = Gtk.Align.CENTER
        grid.props.halign = Gtk.Align.CENTER
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        self.add(grid)
        grid.attach(config_button, 0, 0, 2, 1)
        grid.attach(separator1,    0, 1, 2, 1)
        grid.attach(rgb_box,       0, 2, 2, 1)
        grid.attach(static_button, 0, 3, 2, 1)
        grid.attach(separator2,    0, 4, 2, 1)
        grid.attach(switch_label,  0, 5, 1, 1)
        grid.attach(switch,        1, 5, 1, 1)

        self.client_process = None

        # find files
        # self.config = Path(Path(__file__).resolve().parent, Path('../config')).resolve()
        # self.client = Path(Path(__file__).resolve().parent, Path('client.o'))
        self.config = str(Path.home()) + '/.config/sezanlight/config'
        self.client = 'sezanlight_screen_client' # binary in /usr/bin

        # check if config file exists
        if not Path(self.config).exists():
            # if not, see if the original config file exists and copy it to the user
            systemconfig = '/etc/sezanlight/config'
            if not Path(systemconfig).exists():
                self.alert('Package not properly installed, /etc/sezanlight/config missing!',
                        'Consult the installation instructions here: ' +
                        'https://github.com/sezanzeb/sezanlight/ or copy the config file from ' +
                        'that online github repository to ~/.config/sezanlight/config')
                exit()
            try:
                os.makedirs(str(Path(self.config).parent))
            except FileExistsError:
                # if the folder already exists that's fine
                pass
            # now create config file in home
            copyfile(systemconfig, self.config)


    def alert(self, msg1, msg2):
        dialog = Gtk.MessageDialog(parent=self, flags=0, message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK, text=msg1)
        dialog.format_secondary_text(msg2)
        dialog.run()
        dialog.destroy()


    def check_config(self):
        """
            check if config contains all the values that are absolutely necessary
            which is the ip of the raspberry. Alerts and returns False if not,
            returns True if yes.
        """
        config = self.read_config()
        if 'raspberry_ip' in config and config['raspberry_ip'] != '':
            return True
        else:
            self.alert('Please provide a value for raspberry_ip in the config!',
                    'Find out the raspberries ip using "ifconfig" on the pi or "sudo arp-scan --localnet", ' +
                    'then press "edit config" in the application and insert it like "raspberry_ip=192.168.1.100"')
            return False


    def read_config(self):
        """
            returns a dict containing the values in config
        """ 
        try:
            with open(self.config) as f:
                config = configparser.RawConfigParser()
                config.read_string('[root]\n' + f.read())
                config_dict = {key: config['root'][key] for key in config['root']}
                # default values:
                if not 'raspberry_port' in config_dict or config_dict['raspberry_port'] == '':
                    config_dict['raspberry_port'] = 3546
                return config_dict
        except FileNotFoundError:
            # This error is when the config was not copied from /etc/sezanlight/config to
            # ~/.config/sezanlight/config which should happen at the start of the application.
            # If both are missing, this application should complain at the beginning
            self.alert('Config not found!', 'Please try to restart the application or ' +
                    'download the config file from https://github.com/sezanzeb/sezanlight/blob/master/config ' +
                    'and place it in ~/.config/sezanlight/config')


    def set_static_color(self, button):
        # stop if config is faulty
        if not self.check_config():
            return

        self.switch.set_active(0)
        self.stop_client()
        full_on = 20000

        try:
            r = int(float(self.r_entry.get_text()) * full_on / 255)
            g = int(float(self.g_entry.get_text()) * full_on / 255)
            b = int(float(self.b_entry.get_text()) * full_on / 255)
        except:
            self.alert('Number could not be read!', 'Please re-check your r, g and b input.')
            return

        config = self.read_config()
        raspberry_ip = config['raspberry_ip']
        raspberry_port = config['raspberry_port']
        url = 'http://{}:{}/color/set/?r={}&g={}&b={}'.format(raspberry_ip, raspberry_port, r, g, b)
        try:
            # 1s timeout in a local network is more than enough
            requests.get(url, timeout=1)
        except requests.exceptions.ConnectTimeout:
            self.alert('Cannot reach server!', 'Check if the Raspberries IP in your config is correct, if your PC is able to ping the Raspberry and if yes, restart the server there.')


    def open_config(self, button):
        """
            displays a text-editor to edit the config
        """
        print(self.config)
        subprocess.Popen(['xdg-open', str(self.config)])


    def on_switch_activated(self, switch, gparam):
        """
            the switch controls the screen reading client
        """
        if switch.get_active():
            # stop if config is faulty
            if not self.check_config():
                self.switch.set_active(0)
                return
            self.client_process = subprocess.Popen([str(self.client), str(self.config)])
        else:
            self.stop_client()


    def stop_client(self):
        if not self.client_process is None and self.client_process.poll() is None:
            self.client_process.kill()


    def close(self, window):
        self.stop_client()
        Gtk.main_quit()


win = LEDClient()
win.connect('destroy', win.close)
win.show_all()
Gtk.main()
