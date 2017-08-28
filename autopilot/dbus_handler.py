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


"""Initialise dbus once using glib mainloop."""

from dbus._dbus import BusConnection
import dbus
from dbus.mainloop.glib import DBusGMainLoop


_glib_loop_set = False

# DBus has an annoying bug where we need to initialise it with the gobject main
# loop *before* it's initialised anywhere else. This module exists so we can
# initialise the dbus module once, and once only.


def _ensure_glib_loop_set():
    global _glib_loop_set
    if not _glib_loop_set:
        DBusGMainLoop(set_as_default=True)
        _glib_loop_set = True


def get_session_bus():
    """Return a session bus that has had the DBus GLib main loop
    initialised.

    """
    _ensure_glib_loop_set()
    return dbus.SessionBus()


def get_system_bus():
    """Return a system bus that has had the DBus GLib main loop
    initialised.

    """
    _ensure_glib_loop_set()
    return dbus.SystemBus()


def get_custom_bus(bus_address):
    """Return a custom bus that has had the DBus GLib main loop
    initialised.

    """
    _ensure_glib_loop_set()
    return BusConnection(bus_address)
