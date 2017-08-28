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

from dbus import String
from unittest.mock import Mock
from testtools import TestCase
from testtools.matchers import (
    Equals,
    IsInstance,
    raises,
)
import autopilot.introspection._search as _s
from autopilot.introspection.qt import QtObjectProxyMixin
import autopilot.introspection as _i


class GetDetailsFromStateDataTests(TestCase):

    fake_state_data = (String('/some/path'), dict(foo=123))

    def test_returns_classname(self):
        class_name, _, _ = _s._get_details_from_state_data(
            self.fake_state_data
        )
        self.assertThat(class_name, Equals('path'))

    def test_returns_path(self):
        _, path, _ = _s._get_details_from_state_data(self.fake_state_data)
        self.assertThat(path, Equals(b'/some/path'))

    def test_returned_path_is_bytestring(self):
        _, path, _ = _s._get_details_from_state_data(self.fake_state_data)
        self.assertThat(path, IsInstance(type(b'')))

    def test_returns_state_dict(self):
        _, _, state = _s._get_details_from_state_data(self.fake_state_data)
        self.assertThat(state, Equals(dict(foo=123)))


class FooTests(TestCase):

    fake_data_with_ap_interface = """
        <!DOCTYPE node PUBLIC
            "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
            "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
        <!-- GDBus 2.39.92 -->
        <node>
          <interface name="com.canonical.Autopilot.Introspection">
            <method name="GetState">
              <arg type="s" name="piece" direction="in">
              </arg>
              <arg type="a(sv)" name="state" direction="out">
              </arg>
            </method>
            <method name="GetVersion">
              <arg type="s" name="version" direction="out">
              </arg>
            </method>
          </interface>
        </node>
    """

    fake_data_with_ap_and_qt_interfaces = """
        <!DOCTYPE node PUBLIC
            "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
            "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
        <node>
            <interface name="com.canonical.Autopilot.Introspection">
                <method name='GetState'>
                    <arg type='s' name='piece' direction='in' />
                    <arg type='a(sv)' name='state' direction='out' />
                </method>
                <method name='GetVersion'>
                    <arg type='s' name='version' direction='out' />
                </method>
            </interface>
            <interface name="com.canonical.Autopilot.Qt">
                <method name='RegisterSignalInterest'>
                    <arg type='i' name='object_id' direction='in' />
                    <arg type='s' name='signal_name' direction='in' />
                </method>
                <method name='GetSignalEmissions'>
                    <arg type='i' name='object_id' direction='in' />
                    <arg type='s' name='signal_name' direction='in' />
                    <arg type='i' name='sigs' direction='out' />
                </method>
                <method name='ListSignals'>
                    <arg type='i' name='object_id' direction='in' />
                    <arg type='as' name='signals' direction='out' />
                </method>
                <method name='ListMethods'>
                    <arg type='i' name='object_id' direction='in' />
                    <arg type='as' name='methods' direction='out' />
                </method>
                <method name='InvokeMethod'>
                    <arg type='i' name='object_id' direction='in' />
                    <arg type='s' name='method_name' direction='in' />
                    <arg type='av' name='arguments' direction='in' />
                </method>
            </interface>
        </node>
    """

    def test_raises_RuntimeError_when_no_interface_is_found(self):
        self.assertThat(
            lambda: _s._get_proxy_bases_from_introspection_xml(""),
            raises(RuntimeError("Could not find Autopilot interface."))
        )

    def test_returns_ApplicationProxyObject_claws_for_base_interface(self):
        self.assertThat(
            _s._get_proxy_bases_from_introspection_xml(
                self.fake_data_with_ap_interface
            ),
            Equals(())
        )

    def test_returns_both_base_and_qt_interface(self):
        self.assertThat(
            _s._get_proxy_bases_from_introspection_xml(
                self.fake_data_with_ap_and_qt_interfaces
            ),
            Equals((QtObjectProxyMixin,))
        )


class ExtendProxyBasesWithEmulatorBaseTests(TestCase):

    def test_default_emulator_base_name(self):
        bases = _s._extend_proxy_bases_with_emulator_base(tuple(), None)
        self.assertThat(len(bases), Equals(1))
        self.assertThat(bases[0].__name__, Equals("DefaultEmulatorBase"))
        self.assertThat(bases[0].__bases__[0], Equals(_i.CustomEmulatorBase))

    def test_appends_custom_emulator_base(self):
        existing_bases = ('token',)
        custom_emulator_base = Mock()
        new_bases = _s._extend_proxy_bases_with_emulator_base(
            existing_bases,
            custom_emulator_base
        )
        self.assertThat(
            new_bases,
            Equals(existing_bases + (custom_emulator_base,))
        )
