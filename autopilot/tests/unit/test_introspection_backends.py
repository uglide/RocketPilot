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

from dbus import String, DBusException
from unittest.mock import patch, MagicMock, Mock
from testtools import TestCase
from testtools.matchers import Equals, Not, NotEquals, IsInstance

from autopilot.introspection import (
    _xpathselect as xpathselect,
    backends,
    dbus,
)


class DBusAddressTests(TestCase):

    def test_can_construct(self):
        fake_bus = object()
        backends.DBusAddress(fake_bus, "conn", "path")

    def test_can_store_address_in_dictionary(self):
        fake_bus = object()
        backends.DBusAddress(fake_bus, "conn", "path")
        dict(addr=object())

    def test_equality_operator(self):
        fake_bus = object()
        addr1 = backends.DBusAddress(fake_bus, "conn", "path")

        self.assertThat(
            addr1,
            Equals(backends.DBusAddress(fake_bus, "conn", "path"))
        )
        self.assertThat(
            addr1,
            NotEquals(backends.DBusAddress(fake_bus, "conn", "new_path"))
        )
        self.assertThat(
            addr1,
            NotEquals(backends.DBusAddress(fake_bus, "conn2", "path"))
        )
        self.assertThat(
            addr1,
            NotEquals(backends.DBusAddress(object(), "conn", "path"))
        )

    def test_inequality_operator(self):
        fake_bus = object()
        addr1 = backends.DBusAddress(fake_bus, "conn", "path")

        self.assertThat(
            addr1,
            Not(NotEquals(backends.DBusAddress(fake_bus, "conn", "path")))
        )
        self.assertThat(
            addr1,
            NotEquals(backends.DBusAddress(fake_bus, "conn", "new_path"))
        )
        self.assertThat(
            addr1,
            NotEquals(backends.DBusAddress(fake_bus, "conn2", "path"))
        )
        self.assertThat(
            addr1,
            NotEquals(backends.DBusAddress(object(), "conn", "path"))
        )

    def test_session_bus_construction(self):
        connection = self.getUniqueString()
        object_path = self.getUniqueString()
        with patch.object(backends, 'get_session_bus') as patch_sb:
            addr = backends.DBusAddress.SessionBus(connection, object_path)
            self.assertThat(
                addr._addr_tuple,
                Equals(
                    backends.DBusAddress.AddrTuple(
                        patch_sb.return_value,
                        connection,
                        object_path
                    )
                )
            )

    def test_system_bus_construction(self):
        connection = self.getUniqueString()
        object_path = self.getUniqueString()
        with patch.object(backends, 'get_system_bus') as patch_sb:
            addr = backends.DBusAddress.SystemBus(connection, object_path)
            self.assertThat(
                addr._addr_tuple,
                Equals(
                    backends.DBusAddress.AddrTuple(
                        patch_sb.return_value,
                        connection,
                        object_path
                    )
                )
            )

    def test_custom_bus_construction(self):
        connection = self.getUniqueString()
        object_path = self.getUniqueString()
        bus_path = self.getUniqueString()
        with patch.object(backends, 'get_custom_bus') as patch_cb:
            addr = backends.DBusAddress.CustomBus(
                bus_path,
                connection,
                object_path
            )
            self.assertThat(
                addr._addr_tuple,
                Equals(
                    backends.DBusAddress.AddrTuple(
                        patch_cb.return_value,
                        connection,
                        object_path
                    )
                )
            )
            patch_cb.assert_called_once_with(bus_path)


class ClientSideFilteringTests(TestCase):

    def get_empty_fake_object(self):
        return type(
            'EmptyObject',
            (object,),
            {'no_automatic_refreshing': MagicMock()}
        )

    def test_object_passes_filters_disables_refreshing(self):
        obj = self.get_empty_fake_object()
        backends._object_passes_filters(obj)

        obj.no_automatic_refreshing.assert_called_once_with()
        self.assertTrue(
            obj.no_automatic_refreshing.return_value.__enter__.called
        )

    def test_object_passes_filters_works_with_no_filters(self):
        obj = self.get_empty_fake_object()
        self.assertTrue(backends._object_passes_filters(obj))

    def test_object_passes_filters_fails_when_attr_missing(self):
        obj = self.get_empty_fake_object()
        self.assertFalse(backends._object_passes_filters(obj, foo=123))

    def test_object_passes_filters_fails_when_attr_has_wrong_value(self):
        obj = self.get_empty_fake_object()
        obj.foo = 456
        self.assertFalse(backends._object_passes_filters(obj, foo=123))

    def test_object_passes_filters_succeeds_with_one_correct_parameter(self):
        obj = self.get_empty_fake_object()
        obj.foo = 123
        self.assertTrue(backends._object_passes_filters(obj, foo=123))


class BackendTests(TestCase):

    @patch('autopilot.introspection.backends._logger')
    def test_large_query_returns_log_warnings(self, mock_logger):
        """Queries that return large numbers of items must cause a log warning.

        'large' is defined as more than 15.

        """
        query = xpathselect.Query.root('foo')
        fake_dbus_address = Mock()
        fake_dbus_address.introspection_iface.GetState.return_value = \
            [(b'/root/path', {}) for i in range(16)]
        backend = backends.Backend(fake_dbus_address)
        backend.execute_query_get_data(
            query,
        )

        mock_logger.warning.assert_called_once_with(
            "Your query '%r' returned a lot of data (%d items). This "
            "is likely to be slow. You may want to consider optimising"
            " your query to return fewer items.",
            query,
            16)

    @patch('autopilot.introspection.backends._logger')
    def test_small_query_returns_dont_log_warnings(self, mock_logger):
        """Queries that return small numbers of items must not log a warning.

        'small' is defined as 15 or fewer.

        """
        query = xpathselect.Query.root('foo')
        fake_dbus_address = Mock()
        fake_dbus_address.introspection_iface.GetState.return_value = \
            [(b'/root/path', {}) for i in range(15)]
        backend = backends.Backend(fake_dbus_address)
        backend.execute_query_get_data(
            query,
        )

        self.assertThat(mock_logger.warning.called, Equals(False))

    @patch.object(backends, 'make_introspection_object', return_value=None)
    def test_proxy_instances_returns_list(self, mio):
        query = xpathselect.Query.root('foo')
        fake_dbus_address = Mock()
        fake_dbus_address.introspection_iface.GetState.return_value = [
            (b'/root/path', {}) for i in range(1)
        ]
        backend = backends.Backend(fake_dbus_address)

        self.assertThat(
            backend.execute_query_get_proxy_instances(query, 0),
            Equals([None])
        )

    @patch.object(backends, 'make_introspection_object', return_value=None)
    def test_proxy_instances_with_clientside_filtering_returns_list(self, mio):
        query = xpathselect.Query.root('foo')
        query.needs_client_side_filtering = Mock(return_value=True)
        fake_dbus_address = Mock()
        fake_dbus_address.introspection_iface.GetState.return_value = [
            (b'/root/path', {}) for i in range(1)
        ]
        backend = backends.Backend(fake_dbus_address)

        with patch.object(
                backends, '_object_passes_filters', return_value=True):
            self.assertThat(
                backend.execute_query_get_proxy_instances(query, 0),
                Equals([None])
            )

    def test_proxy_instance_catches_unknown_service_exception(self):
        query = xpathselect.Query.root('foo')
        e = DBusException(
            name='org.freedesktop.DBus.Error.ServiceUnknown'
        )
        fake_dbus_address = Mock()
        fake_dbus_address.introspection_iface.GetState.side_effect = e
        backend = backends.Backend(fake_dbus_address)

        self.assertRaises(RuntimeError, backend.execute_query_get_data, query)

    def test_unknown_service_exception_gives_correct_msg(self):
        query = xpathselect.Query.root('foo')
        e = DBusException(
            name='org.freedesktop.DBus.Error.ServiceUnknown'
        )
        fake_dbus_address = Mock()
        fake_dbus_address.introspection_iface.GetState.side_effect = e
        backend = backends.Backend(fake_dbus_address)
        try:
            backend.execute_query_get_data(query)
        except RuntimeError as e:
            msg = ("Lost dbus backend communication. It appears the "
                   "application under test exited before the test "
                   "finished!")
            self.assertEqual(str(e), msg)

    def test_proxy_instance_raises_uncaught_dbus_exceptions(self):
        query = xpathselect.Query.root('foo')
        e = DBusException()
        fake_dbus_address = Mock()
        fake_dbus_address.introspection_iface.GetState.side_effect = e
        backend = backends.Backend(fake_dbus_address)

        self.assertRaises(DBusException, backend.execute_query_get_data, query)

    def test_proxy_instance_raises_uncaught_exceptions(self):
        query = xpathselect.Query.root('foo')
        e = Exception()
        fake_dbus_address = Mock()
        fake_dbus_address.introspection_iface.GetState.side_effect = e
        backend = backends.Backend(fake_dbus_address)

        self.assertRaises(Exception, backend.execute_query_get_data, query)


class MakeIntrospectionObjectTests(TestCase):

    """Test selection of custom proxy object class."""

    class DefaultSelector(dbus.CustomEmulatorBase):
        pass

    class AlwaysSelected(dbus.CustomEmulatorBase):
        @classmethod
        def validate_dbus_object(cls, path, state):
            """Validate always.

            :returns: True

            """
            return True

    class NeverSelected(dbus.CustomEmulatorBase):
        @classmethod
        def validate_dbus_object(cls, path, state):
            """Validate never.

            :returns: False

            """
            return False

    def test_class_has_validation_method(self):
        """Verify that a class has a validation method by default."""
        self.assertTrue(callable(self.DefaultSelector.validate_dbus_object))

    @patch.object(backends, '_get_proxy_object_class')
    def test_make_introspection_object(self, gpoc):
        """Verify that make_introspection_object makes the right call."""
        gpoc.return_value = self.DefaultSelector
        fake_id = Mock()
        new_fake = backends.make_introspection_object(
            (String('/Object'), {'id': [0, 42]}),
            None,
            fake_id,
        )
        self.assertThat(new_fake, IsInstance(self.DefaultSelector))
        gpoc.assert_called_once_with(
            fake_id,
            b'/Object',
            {'id': [0, 42]}
        )

    def test_validate_dbus_object_matches_on_class_name(self):
        """Validate_dbus_object must match class name."""
        selected = self.DefaultSelector.validate_dbus_object(
            '/DefaultSelector', {})
        self.assertTrue(selected)
