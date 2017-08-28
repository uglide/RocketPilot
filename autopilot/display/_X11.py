# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2013 Canonical
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


import autopilot._glib
from autopilot.display import Display as DisplayBase


class Display(DisplayBase):
    def __init__(self):
        # Note: MUST import these here, rather than at the top of the file.
        # Why? Because sphinx imports these modules to build the API
        # documentation, which in turn tries to import Gdk, which in turn
        # fails because there's no DISPLAY environment set in the package
        # builder.
        Gdk = autopilot._glib._import_gdk()
        self._default_screen = Gdk.Screen.get_default()
        if self._default_screen is None:
            raise RuntimeError(
                "Unable to determine default screen information")
        self._blacklisted_drivers = ["NVIDIA"]

    def get_num_screens(self):
        """Get the number of screens attached to the PC.

        :returns: int indicating number of screens attached.

        """
        return self._default_screen.get_n_monitors()

    def get_primary_screen(self):
        """Return an integer of which screen is considered the primary."""
        return self._default_screen.get_primary_monitor()

    def get_screen_width(self, screen_number=0):
        return self.get_screen_geometry(screen_number)[2]

    def get_screen_height(self, screen_number=0):
        return self.get_screen_geometry(screen_number)[3]

    def get_screen_geometry(self, screen_number):
        """Get the geometry for a particular screen.

        :return: Tuple containing (x, y, width, height).

        """
        if screen_number < 0 or screen_number >= self.get_num_screens():
            raise ValueError('Specified screen number is out of range.')
        rect = self._default_screen.get_monitor_geometry(screen_number)
        return (rect.x, rect.y, rect.width, rect.height)
