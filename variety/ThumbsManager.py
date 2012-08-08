# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Peter Levi <peterlevi@peterlevi.com>
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

from gi.repository import Gtk, Gdk, GdkPixbuf, GObject
from configobj import ConfigObj
import os

import threading
import logging
from variety.ThumbsWindow import ThumbsWindow

logger = logging.getLogger('variety')

class ThumbsManager():
    POSITIONS = {
        "bottom": ThumbsWindow.BOTTOM,
        "top": ThumbsWindow.TOP,
        "left": ThumbsWindow.LEFT,
        "right": ThumbsWindow.RIGHT
    }

    R_POSITIONS = dict((v, k) for (k,v) in POSITIONS.items())

    SIZES = [x*30 for x in xrange(2, 11)]

    class Options():
        def __init__(self):
            self.position = ThumbsWindow.BOTTOM
            self.breadth = 120

    def __init__(self, parent):
        self.parent = parent
        self.thumbs_window = None
        self.show_thumbs_lock = threading.Lock()

        self.menu = Gtk.Menu()

        def close(widget): self.hide(gdk_thread=True, force=True)
        close_item = Gtk.MenuItem("Close")
        close_item.connect("activate", close)

        pin_item = Gtk.MenuItem("Pin")
        pin_item.connect("activate", self.pin)

        position_menu = Gtk.Menu()
        for p in ThumbsManager.POSITIONS.keys():
            item = Gtk.MenuItem(p[0].upper() + p[1:])
            def _set_position(widget, pos=p): self.set_position(pos)
            item.connect("activate", _set_position)
            position_menu.append(item)

        size_menu = Gtk.Menu()
        for size in ThumbsManager.SIZES:
            item = Gtk.MenuItem(str(size))
            def _set_size(widget, size=size): self.set_size(size)
            item.connect("activate", _set_size)
            size_menu.append(item)

        self.menu.append(close_item)
        self.menu.append(pin_item)

        position_item = Gtk.MenuItem("Position")
        position_item.set_submenu(position_menu)
        self.menu.append(position_item)

        size_item = Gtk.MenuItem("Size")
        size_item.set_submenu(size_menu)
        self.menu.append(size_item)

        self.menu.show_all()

        self.pinned = False
        self.images = None
        self.screen = None

        self.type = None

    def repaint(self):
        self.hide(gdk_thread=True)
        if self.images:
            self.show(self.images, gdk_thread=True, screen=self.screen)

    def set_position(self, p):
        logger.info("Setting thumbs position " + str(p))
        options = self.load_options()
        options.position = ThumbsManager.POSITIONS[p]
        self.save_options(options)
        self.repaint()

    def set_size(self, size):
        logger.info("Setting thumbs position " + str(size))
        options = self.load_options()
        options.breadth = size
        self.save_options(options)
        self.repaint()

    def pin(self, widget=None):
        self.pinned = True

    def on_click(self, thumbs_window, file, widget, event):
        if event.button == 1:
            self.parent.set_wallpaper(file, False)
        else:
            self.menu.popup(
                None,
                widget,
                None,#lambda x, y: (event.get_root_coords()[0], event.get_root_coords()[1] - self.menu.get_height(), True),
                None,
                event.button,
                event.time)

    def show(self, images, gdk_thread=False, screen=None, type=None):
        with self.show_thumbs_lock:
            self.type = type
            self.images = images
            self.screen = screen

            try:
                if self.thumbs_window:
                    if not gdk_thread:
                        Gdk.threads_enter()
                    self.thumbs_window.destroy()
                    self.thumbs_window = None
                    if not gdk_thread:
                        Gdk.threads_leave()

                if len(images) > 0:
                    if not gdk_thread:
                        Gdk.threads_enter()
                    options = self.load_options()
                    self.thumbs_window = ThumbsWindow(
                        screen=screen, position=options.position, breadth=options.breadth)
                    self.thumbs_window.connect("clicked", self.on_click)
                    self.thumbs_window.start(images)
                    if not gdk_thread:
                        Gdk.threads_leave()
            except Exception:
                logger.exception("Could not create thumbs window:")

    def load_options(self):
        options = ThumbsManager.Options()
        options.position = ThumbsWindow.BOTTOM
        options.breadth = 120
        try:
            config = ConfigObj(os.path.join(self.parent.config_folder, "ui.conf"))
            try:
                s = config["thumbs_position"].lower()
                options.position = ThumbsManager.POSITIONS[s]
            except Exception:
                logger.exception("Missing or bad thumbs_position option in ui.conf")

            try:
                options.breadth = int(config["thumbs_size"])
            except Exception:
                logger.exception("Missing or bad thumbs_size option in ui.conf")
        except Exception:
            logger.exception("Could not read ui.conf")

        return options

    def save_options(self, options):
        try:
            config = ConfigObj(os.path.join(self.parent.config_folder, "ui.conf"))
            try:
                config["thumbs_position"] = ThumbsManager.R_POSITIONS[options.position]
                config["thumbs_size"] = options.breadth
                config.write()
            except Exception:
                logger.exception("Missing or bad thumbs_position option in ui.conf")
        except Exception:
            logger.exception("Could not save ui.conf")


    def hide(self, gdk_thread=False, force=True):
        if force: self.pinned = False
        if self.thumbs_window and not self.pinned:
            try:
                if not gdk_thread:
                    Gdk.threads_enter()
                self.thumbs_window.destroy()
                self.thumbs_window = None
                self.parent.update_indicator(is_gtk_thread=True)
                if not gdk_thread:
                    Gdk.threads_leave()
            except Exception:
                pass

