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


import logging
import os
from os.path import join
try:
    import lxml.etree as ET
except ImportError:
    from xml.etree import ElementTree as ET

_logger = logging.getLogger(__name__)


class DBusInspector(object):
    def __init__(self, bus):
        self._bus = bus
        self._xml_processor = None
        self.p_dbus = self._bus.get_object('org.freedesktop.DBus', '/')

    def set_xml_processor(self, processor):
        self._xml_processor = processor

    def __call__(self, conn_name, obj_name='/'):
        """Introspects and applies the reply_handler to the dbus object
        constructed from the provided bus, connection and object name.

        """
        handler = lambda xml: self._xml_processor(
            conn_name,
            obj_name,
            xml
        )
        error_handler = lambda *args: _logger.error("Error occured: %r" % args)
        obj = self._bus.get_object(conn_name, obj_name)

        # avoid introspecting our own PID, as that locks up with libdbus
        try:
            obj_pid = self.p_dbus.GetConnectionUnixProcessID(
                conn_name,
                dbus_interface='org.freedesktop.DBus'
            )
            if obj_pid == os.getpid():
                return
        except:
            # can't get D-BUS daemon's own pid, ignore
            pass
        obj.Introspect(
            dbus_interface='org.freedesktop.DBus.Introspectable',
            reply_handler=handler,
            error_handler=error_handler
        )


class XmlProcessor(object):
    def __init__(self):
        self._dbus_inspector = None
        self._success_callback = None

    def set_dbus_inspector(self, inspector):
        self._dbus_inspector = inspector

    def set_success_callback(self, callback):
        """Must be a callable etc."""
        self._success_callback = callback

    def __call__(self, conn_name, obj_name, xml):
        try:
            root = ET.fromstring(xml)

            for child in root.getchildren():
                try:
                    child_name = join(obj_name, child.attrib['name'])
                except KeyError:
                    continue
                # If we found another node, make sure we get called again with
                # a new XML block.
                if child.tag == 'node':
                    self._dbus_inspector(conn_name, child_name)
                # If we found an interface, call our success function with the
                # interface name
                elif child.tag == 'interface':
                    iface_name = child_name.split('/')[-1]
                    self._success_callback(conn_name, obj_name, iface_name)
        except ET.ParseError:
            _logger.warning(
                "Unable to parse XML response for %s (%s)"
                % (conn_name, obj_name)
            )


def _start_trawl(bus, connection_name, on_success_cb):
    """Start searching *connection_name* on *bus* for interfaces under
    org.freedesktop.DBus.Introspectable.

    on_success_cb gets called when an interface is found.

    """

    if connection_name is None:
        raise ValueError("Connection name is required.")

    if not callable(on_success_cb):
        raise ValueError("on_success_cb needs to be callable.")

    dbus_inspector = DBusInspector(bus)
    xml_processor = XmlProcessor()
    dbus_inspector.set_xml_processor(xml_processor)
    xml_processor.set_dbus_inspector(dbus_inspector)
    xml_processor.set_success_callback(on_success_cb)

    dbus_inspector(connection_name)
