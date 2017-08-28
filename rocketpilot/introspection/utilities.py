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

import psutil
from dbus import Interface


def _get_bus_connections_pid(bus, connection_name):
    """Returns the pid for the connection **connection_name** on **bus**

    :raises: **DBusException** if connection_name is invalid etc.

    """
    bus_obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
    bus_iface = Interface(bus_obj, 'org.freedesktop.DBus')
    return bus_iface.GetConnectionUnixProcessID(connection_name)


def translate_state_keys(state_dict):
    """Translates the *state_dict* passed in so the keys are usable as python
    attributes."""
    return {k.replace('-', '_'): v for k, v in state_dict.items()}


def sort_by_keys(instances, sort_keys):
    """Sorts DBus object instances by requested keys."""
    def get_sort_key(item):
        sort_key = []
        for sk in sort_keys:
            if not isinstance(sk, str):
                raise ValueError(
                    'Parameter `sort_keys` must be a list of strings'
                )
            value = item
            for key in sk.split('.'):
                value = getattr(value, key)
            sort_key.append(value)
        return sort_key

    if sort_keys and not isinstance(sort_keys, list):
        raise ValueError('Parameter `sort_keys` must be a list.')
    if len(instances) > 1 and sort_keys:
        return sorted(instances, key=get_sort_key)
    return instances


def get_pid_for_process(process_name):

    if not isinstance(process_name, str):
        raise ValueError('Process name must be a string.')

    pids = [process.pid for process in psutil.process_iter()
            if process.name() == process_name]

    if not pids:
        raise ValueError('Process \'{}\' not running'.format(process_name))

    if len(pids) > 1:
        raise ValueError(
            'More than one PID exists for process \'{}\''.format(
                process_name
            )
        )

    return pids[0]
