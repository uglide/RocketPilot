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

"""Backend IPC interface for autopilot.

This module contains two primative classes that Autopilot uses for it's IPC
routines.

The first is the DBusAddress class. This contains knowledge of how to talk dbus
to a particular application exposed over dbus. In the future, this interface
could be provided by some alternative IPC mechanism.

The second class is the Backend class. This holds a reference to a DBusAddress
class, and contains code that turns a query object into proxy classes.

"""

import logging
from collections import namedtuple

import dbus
import psutil

from rocketpilot.constants import (
    AP_INTROSPECTION_IFACE,
    CURRENT_WIRE_PROTOCOL_VERSION,
    DBUS_INTROSPECTION_IFACE,
    QT_AUTOPILOT_IFACE,
)
from rocketpilot.dbus_handler import (
    get_session_bus,
    get_system_bus,
    get_custom_bus,
)
from rocketpilot.introspection._object_registry import _get_proxy_object_class
from rocketpilot.introspection.utilities import _get_bus_connections_pid
from rocketpilot.utilities import Timer

_logger = logging.getLogger(__name__)


class WireProtocolVersionMismatch(RuntimeError):
    """Wire protocols mismatch."""


class DBusAddress(object):
    """Store information about an Autopilot dbus backend, from keyword
    arguments."""
    _checked_backends = []

    AddrTuple = namedtuple(
        'AddressTuple', ['bus', 'connection', 'object_path'])

    @staticmethod
    def SessionBus(connection, object_path):
        """Construct a DBusAddress that backs on to the session bus."""
        return DBusAddress(get_session_bus(), connection, object_path)

    @staticmethod
    def SystemBus(connection, object_path):
        """Construct a DBusAddress that backs on to the system bus."""
        return DBusAddress(get_system_bus(), connection, object_path)

    @staticmethod
    def CustomBus(bus_address, connection, object_path):
        """Construct a DBusAddress that backs on to a custom bus.

        :param bus_address: A string representing the address of the dbus bus
            to connect to.

        """
        return DBusAddress(
            get_custom_bus(bus_address), connection, object_path)

    def __init__(self, bus, connection, object_path):
        """Construct a DBusAddress instance.

        :param bus: A valid DBus bus object.
        :param connection: A string connection name to look at, or None to
            search all dbus connections for objects that resemble an autopilot
            conection.
        :param object_path: The path to the object that provides the autopilot
            interface, or None to search for the object.

        """
        # We cannot evaluate kwargs for accuracy now, since this class will be
        # created at module import time, at which point the bus backend
        # probably does not exist yet.
        self._addr_tuple = DBusAddress.AddrTuple(bus, connection, object_path)

    @property
    def introspection_iface(self):
        if not isinstance(self._addr_tuple.connection, str):
            raise TypeError("Service name must be a string.")
        if not isinstance(self._addr_tuple.object_path, str):
            raise TypeError("Object name must be a string")

        proxy_obj = self._addr_tuple.bus.get_object(
            self._addr_tuple.connection,
            self._addr_tuple.object_path
        )
        iface = dbus.Interface(proxy_obj, AP_INTROSPECTION_IFACE)
        if self._addr_tuple not in DBusAddress._checked_backends:
            try:
                self._check_version(iface)
            except WireProtocolVersionMismatch:
                raise
            else:
                DBusAddress._checked_backends.append(self._addr_tuple)
        return iface

    def _check_version(self, iface):
        """Check the wire protocol version on 'iface', and raise an error if
        the version does not match what we were expecting.

        """
        try:
            version = iface.GetVersion()
        except dbus.DBusException:
            version = "1.2"
        if version != CURRENT_WIRE_PROTOCOL_VERSION:
            raise WireProtocolVersionMismatch(
                "Wire protocol mismatch at %r: is %s, expecting %s" % (
                    self,
                    version,
                    CURRENT_WIRE_PROTOCOL_VERSION)
            )

    def _check_pid_running(self):
        try:
            process_pid = _get_bus_connections_pid(
                self._addr_tuple.bus,
                self._addr_tuple.connection
            )
            return psutil.pid_exists(process_pid)
        except dbus.DBusException as e:
            if e.get_dbus_name() == \
                    'org.freedesktop.DBus.Error.NameHasNoOwner':
                return False
            else:
                raise

    @property
    def dbus_introspection_iface(self):
        dbus_object = self._addr_tuple.bus.get_object(
            self._addr_tuple.connection,
            self._addr_tuple.object_path
        )
        return dbus.Interface(dbus_object, DBUS_INTROSPECTION_IFACE)

    @property
    def qt_introspection_iface(self):
        proxy_obj = self._addr_tuple.bus.get_object(
            self._addr_tuple.connection,
            self._addr_tuple.object_path
        )
        return dbus.Interface(proxy_obj, QT_AUTOPILOT_IFACE)

    def __hash__(self):
        return hash(self._addr_tuple)

    def __eq__(self, other):
        return self._addr_tuple.bus == other._addr_tuple.bus and \
            self._addr_tuple.connection == other._addr_tuple.connection and \
            self._addr_tuple.object_path == other._addr_tuple.object_path

    def __ne__(self, other):
        return (self._addr_tuple.object_path !=
                other._addr_tuple.object_path or
                self._addr_tuple.connection != other._addr_tuple.connection or
                self._addr_tuple.bus != other._addr_tuple.bus)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        if self._addr_tuple.bus._bus_type == dbus.Bus.TYPE_SESSION:
            name = "session"
        elif self._addr_tuple.bus._bus_type == dbus.Bus.TYPE_SYSTEM:
            name = "system"
        else:
            name = "custom"
        return "<%s bus %s %s>" % (
            name, self._addr_tuple.connection, self._addr_tuple.object_path)


class Backend(object):

    """A Backend object that works with an ipc address interface.

    Will raise a RunTimeError if the dbus backend communication is lost."""

    def __init__(self, ipc_address):
        self.ipc_address = ipc_address

    def execute_query_get_data(self, query):
        """Execute 'query', return the raw dbus reply."""
        with Timer("GetState %r" % query):
            try:
                data = self.ipc_address.introspection_iface.GetState(
                    query.server_query_bytes()
                )
            except dbus.DBusException as e:
                desired_exception = 'org.freedesktop.DBus.Error.ServiceUnknown'
                if e.get_dbus_name() != desired_exception:
                    raise
                else:
                    raise RuntimeError(
                        "Lost dbus backend communication. It appears the "
                        "application under test exited before the test "
                        "finished!"
                    )
            if len(data) > 15:
                _logger.warning(
                    "Your query '%r' returned a lot of data (%d items). This "
                    "is likely to be slow. You may want to consider optimising"
                    " your query to return fewer items.",
                    query,
                    len(data)
                )
            return data

    def execute_query_get_proxy_instances(self, query, id):
        """Execute 'query', returning proxy instances."""
        data = self.execute_query_get_data(query)
        objects = [
            make_introspection_object(
                t,
                type(self)(self.ipc_address),
                id,
            )
            for t in data
        ]
        if query.needs_client_side_filtering():
            return list(filter(
                lambda i: _object_passes_filters(
                    i,
                    **query.get_client_side_filters()
                ),
                objects
            ))
        return objects


class FakeBackend(Backend):

    """A backend that always returns fake data, useful for testing."""

    def __init__(self, fake_ipc_return_data):
        """Create a new FakeBackend instance.

        If this backend creates any proxy objects, they will be created with
        a FakeBackend with the same fake ipc return data.

        :param fake_ipc_return_data: The data you want to pretend was returned
            by the applicatoin under test. This must be in the correct protocol
            format, or the results are undefined.
        """
        super(FakeBackend, self).__init__(fake_ipc_return_data)
        self.fake_ipc_return_data = fake_ipc_return_data

    def execute_query_get_data(self, query):
        return self.fake_ipc_return_data


def make_introspection_object(dbus_tuple, backend, object_id):
    """Make an introspection object given a DBus tuple of
    (path, state_dict).

    :param dbus_tuple: A two-item iterable containing a dbus.String object that
        contains the object path, and a dbus.Dictionary object that contains
        the objects state dictionary.
    :param backend: An instance of the Backend class.
    :returns: A proxy object that derives from DBusIntrospectionObject
    :raises ValueError: if more than one class is appropriate for this
             dbus_tuple

    """
    path, state = dbus_tuple
    path = path.encode('utf-8')
    class_object = _get_proxy_object_class(object_id, path, state)
    return class_object(state, path, backend)


def _object_passes_filters(instance, **kwargs):
    """Return true if *instance* satisifies all the filters present in
    kwargs."""
    with instance.no_automatic_refreshing():
        for attr, val in kwargs.items():
            if not hasattr(instance, attr) or getattr(instance, attr) != val:
                # Either attribute is not present, or is present but with
                # the wrong value - don't add this instance to the results
                # list.
                return False
    return True
