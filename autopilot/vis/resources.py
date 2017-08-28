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


import os.path
import dbus

from PyQt5 import QtGui


def get_qt_icon():
    return QtGui.QIcon(":/trolltech/qmessagebox/images/qtlogo-64.png")


def get_filter_icon():
    return QtGui.QIcon("/usr/share/icons/gnome/32x32/actions/search.png")


def get_overlay_icon():
    name = "autopilot-toggle-overlay.svg"
    possible_locations = [
        "/usr/share/icons/hicolor/scalable/actions/",
        os.path.join(os.path.dirname(__file__), '../../icons'),
        "icons",
    ]
    for location in possible_locations:
        path = os.path.join(location, name)
        if os.path.exists(path):
            return QtGui.QIcon(path)
    return QtGui.QIcon()


def dbus_string_rep(dbus_type):
    """Get a string representation of various dbus types."""
    if isinstance(dbus_type, dbus.Boolean):
        return repr(bool(dbus_type))
    if isinstance(dbus_type, dbus.String):
        return dbus_type.encode('utf-8', errors='ignore').decode('utf-8')
    if (isinstance(dbus_type, dbus.Int16) or
            isinstance(dbus_type, dbus.UInt16) or
            isinstance(dbus_type, dbus.Int32) or
            isinstance(dbus_type, dbus.UInt32) or
            isinstance(dbus_type, dbus.Int64) or
            isinstance(dbus_type, dbus.UInt64)):
        return repr(int(dbus_type))
    if isinstance(dbus_type, dbus.Double):
        return repr(float(dbus_type))
    if (isinstance(dbus_type, dbus.Array) or
            isinstance(dbus_type, dbus.Struct)):
        return ', '.join([dbus_string_rep(i) for i in dbus_type])
    else:
        return repr(dbus_type)
