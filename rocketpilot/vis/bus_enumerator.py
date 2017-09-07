# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2013 Canonical
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

from collections import defaultdict

from rocketpilot.vis.dbus_search import _start_trawl
from rocketpilot.constants import ROCKET_PILOT_DBUS_SERVICE_NAME

from PyQt5.QtCore import (
    pyqtSignal,
    QObject,
)


class BusEnumerator(QObject):
    """A simple utility class to support enumeration of all DBus connections,
    objects, and interfaces.

    Create an instance of ths class, and connect to the new_interface_found
    signal.

    """

    new_interface_found = pyqtSignal(str, str, str)

    def __init__(self, bus):
        super(BusEnumerator, self).__init__()
        self._bus = bus
        self._data = defaultdict(lambda: defaultdict(list))

    def get_found_connections(self):
        """Get a list of found connection names. This may not be up to date."""
        return list(self._data.keys())

    def get_found_objects(self, connection_string):
        """Get a list of found objects for a particular connection name.

        This may be out of date.

        """
        if connection_string not in self._data:
            raise KeyError("%s not in results" % connection_string)
        return list(self._data[connection_string].keys())

    def get_found_interfaces(self, connection_string, object_path):
        """Get a list of found interfaces for a particular connection name and
        object path.

        This may be out of date.

        """
        if connection_string not in self._data:
            raise KeyError("connection %s not in results" % connection_string)
        if object_path not in self._data[connection_string]:
            raise KeyError(
                "object %s not in results for connection %s" %
                (object_path, connection_string))
        return self._data[connection_string][object_path]

    def start_trawl(self):
        """Start trawling the bus for interfaces."""

        if ROCKET_PILOT_DBUS_SERVICE_NAME in self._bus.list_names():
            _start_trawl(self._bus, ROCKET_PILOT_DBUS_SERVICE_NAME, self._add_hit)

    def _add_hit(self, conn_name, obj_name, interface_name):
        self.new_interface_found.emit(conn_name, obj_name, interface_name)
        self._data[conn_name][obj_name].append(interface_name)
