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
        self.config = Path(Path(__file__).resolve().parent, Path('../config')).resolve()
        self.client = Path(Path(__file__).resolve().parent, Path('client.o'))


    def set_static_color(self, button):
        self.switch.set_active(0)
        self.stop_client()
        full_on = 20000

        try:
            r = int(float(self.r_entry.get_text()) * full_on / 255)
            g = int(float(self.g_entry.get_text()) * full_on / 255)
            b = int(float(self.b_entry.get_text()) * full_on / 255)
        except:
            dialog = Gtk.MessageDialog(parent=self, flags=0, message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK, text='number could not be read')
            dialog.format_secondary_text('please re-check your r, g and b input.')
            dialog.run()
            dialog.destroy()
            return

        with open(str(self.config)) as f:
            config = configparser.RawConfigParser()
            config.read_string('[root]\n' + f.read())
            raspberry_ip = config['root']['raspberry_ip']
            raspberry_port = config['root']['raspberry_port']
            url = 'http://{}:{}/color/set/?r={}&g={}&b={}'.format(raspberry_ip, raspberry_port, r, g, b)
            print(url)
            requests.get(url)


    def open_config(self, button):
        subprocess.Popen(['xdg-open', str(self.config)])


    def on_switch_activated(self, switch, gparam):
        if switch.get_active():
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
