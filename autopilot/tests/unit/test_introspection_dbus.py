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

import sys
import tempfile
import shutil
import os.path

from unittest.mock import patch, Mock
from io import StringIO
from textwrap import dedent
from testtools import TestCase
from testtools.matchers import (
    Equals,
    Not,
    NotEquals,
    Raises,
    raises,
)

from autopilot.exceptions import StateNotFoundError
from autopilot.introspection import (
    CustomEmulatorBase,
    dbus,
    is_element,
)
from autopilot.introspection.dbus import (
    _MockableDbusObject,
    _validate_object_properties,
)
from autopilot.utilities import sleep

from autopilot.tests.unit.introspection_base import (
    W_DEFAULT,
    X_DEFAULT,
    Y_DEFAULT,
    get_mock_object,
    get_global_rect,
)


class IntrospectionFeatureTests(TestCase):

    def test_custom_emulator_base_does_not_have_id(self):
        self.assertThat(hasattr(CustomEmulatorBase, '_id'), Equals(False))

    def test_derived_emulator_bases_do_have_id(self):
        class MyEmulatorBase(CustomEmulatorBase):
            pass
        self.assertThat(hasattr(MyEmulatorBase, '_id'), Equals(True))

    def test_derived_children_have_same_id(self):
        class MyEmulatorBase(CustomEmulatorBase):
            pass

        class MyEmulator(MyEmulatorBase):
            pass

        class MyEmulator2(MyEmulatorBase):
            pass

        self.assertThat(MyEmulatorBase._id, Equals(MyEmulator._id))
        self.assertThat(MyEmulatorBase._id, Equals(MyEmulator2._id))

    def test_children_have_different_ids(self):
        class MyEmulatorBase(CustomEmulatorBase):
            pass

        class MyEmulatorBase2(CustomEmulatorBase):
            pass

        self.assertThat(MyEmulatorBase._id, NotEquals(MyEmulatorBase2._id))


class DBusIntrospectionObjectTests(TestCase):

    def test_can_access_path_attribute(self):
        fake_object = dbus.DBusIntrospectionObject(
            dict(id=[0, 123], path=[0, '/some/path']),
            b'/root',
            Mock()
        )
        with fake_object.no_automatic_refreshing():
            self.assertThat(fake_object.path, Equals('/some/path'))

    def test_wait_until_destroyed_works(self):
        """wait_until_destroyed must return if no new state is found."""
        fake_object = dbus.DBusIntrospectionObject(
            dict(id=[0, 123]),
            b'/root',
            Mock()
        )
        fake_object._backend.execute_query_get_data.return_value = []

        fake_object.wait_until_destroyed()
        self.assertThat(fake_object.wait_until_destroyed, Not(Raises()))

    def test_wait_until_destroyed_raises_RuntimeError(self):
        """wait_until_destroyed must raise RuntimeError if the object
        persists.

        """
        fake_state = dict(id=[0, 123])
        fake_object = dbus.DBusIntrospectionObject(
            fake_state,
            b'/root',
            Mock()
        )
        fake_object._backend.execute_query_get_data.return_value = \
            [fake_state]

        with sleep.mocked():
            self.assertThat(
                lambda: fake_object.wait_until_destroyed(timeout=1),
                raises(
                    RuntimeError("Object was not destroyed after 1 seconds")
                ),
            )

    def test_base_class_provides_correct_query_name(self):
        self.assertThat(
            dbus.DBusIntrospectionObject.get_type_query_name(),
            Equals('ProxyBase')
        )

    def test_inherited_uses_default_get_node_name(self):
        class TestCPO(dbus.DBusIntrospectionObject):
            pass

        self.assertThat(
            TestCPO.get_type_query_name(),
            Equals('TestCPO')
        )

    def test_inherited_overwrites_node_name_is_correct(self):
        class TestCPO(dbus.DBusIntrospectionObject):
            @classmethod
            def get_type_query_name(cls):
                return "TestCPO"
        self.assertThat(TestCPO.get_type_query_name(), Equals("TestCPO"))


class ProxyObjectPrintTreeTests(TestCase):

    def _print_test_fake_object(self):
        """common fake object for print_tree tests"""

        fake_object = dbus.DBusIntrospectionObject(
            dict(id=[0, 123], path=[0, '/some/path'], text=[0, 'Hello']),
            b'/some/path',
            Mock()
        )
        # get_properties() always refreshes state, so can't use
        # no_automatic_refreshing()
        fake_object.refresh_state = lambda: None
        fake_object._execute_query = lambda q: []
        return fake_object

    def test_print_tree_stdout(self):
        """print_tree with default output (stdout)"""

        fake_object = self._print_test_fake_object()
        orig_sys_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            fake_object.print_tree()
            result = sys.stdout.getvalue()
        finally:
            sys.stdout = orig_sys_stdout

        self.assertEqual(result, dedent("""\
            == /some/path ==
            id: 123
            path: '/some/path'
            text: 'Hello'
            """))

    def test_print_tree_exception(self):
        """print_tree with StateNotFound exception"""

        fake_object = self._print_test_fake_object()
        child = Mock()
        child.print_tree.side_effect = StateNotFoundError('child')

        with patch.object(fake_object, 'get_children', return_value=[child]):
            out = StringIO()
            print_func = lambda: fake_object.print_tree(out)
            self.assertThat(print_func, Not(Raises(StateNotFoundError)))
            self.assertEqual(out.getvalue(), dedent("""\
            == /some/path ==
            id: 123
            path: '/some/path'
            text: 'Hello'
            Error: Object not found with name 'child'.

            {}
            """.format(StateNotFoundError._troubleshoot_url_message)))

    def test_print_tree_fileobj(self):
        """print_tree with file object output"""

        fake_object = self._print_test_fake_object()
        out = StringIO()

        fake_object.print_tree(out)

        self.assertEqual(out.getvalue(), dedent("""\
            == /some/path ==
            id: 123
            path: '/some/path'
            text: 'Hello'
            """))

    def test_print_tree_path(self):
        """print_tree with file path output"""

        fake_object = self._print_test_fake_object()
        workdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, workdir)
        outfile = os.path.join(workdir, 'widgets.txt')

        fake_object.print_tree(outfile)

        with open(outfile) as f:
            result = f.read()
        self.assertEqual(result, dedent("""\
            == /some/path ==
            id: 123
            path: '/some/path'
            text: 'Hello'
            """))


class GetTypeNameTests(TestCase):

    """Tests for the autopilot.introspection.dbus.get_type_name function."""

    def test_returns_string(self):
        token = self.getUniqueString()
        self.assertEqual(token, dbus.get_type_name(token))

    def test_returns_class_name(self):
        class FooBarBaz(object):
            pass
        self.assertEqual("FooBarBaz", dbus.get_type_name(FooBarBaz))

    def test_get_type_name_returns_classname(self):
        class CustomCPO(dbus.DBusIntrospectionObject):
            pass

        type_name = dbus.get_type_name(CustomEmulatorBase)
        self.assertThat(type_name, Equals('ProxyBase'))

    def test_get_type_name_returns_custom_node_name(self):
        class CustomCPO(dbus.DBusIntrospectionObject):
            @classmethod
            def get_type_query_name(cls):
                return 'TestingCPO'
        type_name = dbus.get_type_name(CustomCPO)
        self.assertThat(type_name, Equals('TestingCPO'))

    def test_get_type_name_returns_classname_of_non_proxybase_classes(self):
        class Foo(object):
            pass
        self.assertEqual('Foo', dbus.get_type_name(Foo))


class IsElementTestCase(TestCase):

    def raise_state_not_found(self, should_raise=True):
        if should_raise:
            raise StateNotFoundError('Just throw the exception')

    def test_returns_false_if_not_element(self):
        self.assertFalse(is_element(self.raise_state_not_found))

    def test_returns_true_if_element(self):
        self.assertTrue(
            is_element(
                self.raise_state_not_found,
                should_raise=False
            )
        )


class IsElementMovingTestCase(TestCase):

    def setUp(self):
        super().setUp()
        self.dbus_object = _MockableDbusObject(
            get_mock_object(globalRect=get_global_rect())
        )

    def test_returns_true_if_x_changed(self):
        mock_object = get_mock_object(
            globalRect=get_global_rect(x=X_DEFAULT + 1)
        )
        with self.dbus_object.mocked(mock_object) as mocked_dbus_object:
            self.assertTrue(mocked_dbus_object.is_moving())

    def test_returns_true_if_y_changed(self):
        mock_object = get_mock_object(
            globalRect=get_global_rect(y=Y_DEFAULT + 1)
        )
        with self.dbus_object.mocked(mock_object) as mocked_dbus_object:
            self.assertTrue(mocked_dbus_object.is_moving())

    def test_returns_true_if_x_and_y_changed(self):
        mock_object = get_mock_object(
            globalRect=get_global_rect(x=X_DEFAULT + 1, y=Y_DEFAULT + 1)
        )
        with self.dbus_object.mocked(mock_object) as mocked_dbus_object:
            self.assertTrue(mocked_dbus_object.is_moving())

    def test_returns_false_if_x_and_y_not_changed(self):
        mock_object = get_mock_object(globalRect=get_global_rect())
        with self.dbus_object.mocked(mock_object) as mocked_dbus_object:
            self.assertFalse(mocked_dbus_object.is_moving())


class ValidateObjectPropertiesTestCase(TestCase):

    def test_return_true_if_property_match(self):
        mock_object = get_mock_object(x=X_DEFAULT)
        self.assertTrue(_validate_object_properties(mock_object, x=X_DEFAULT))

    def test_returns_true_if_all_properties_match(self):
        mock_object = get_mock_object(x=X_DEFAULT, y=Y_DEFAULT)
        self.assertTrue(
            _validate_object_properties(mock_object, x=X_DEFAULT, y=Y_DEFAULT)
        )

    def test_return_false_if_property_not_match(self):
        mock_object = get_mock_object(x=X_DEFAULT + 1)
        self.assertFalse(_validate_object_properties(mock_object, x=X_DEFAULT))

    def test_returns_false_if_property_invalid(self):
        mock_object = get_mock_object()
        self.assertFalse(_validate_object_properties(mock_object, x=X_DEFAULT))

    def test_returns_false_if_any_property_not_match(self):
        mock_object = get_mock_object(x=X_DEFAULT, y=Y_DEFAULT, w=W_DEFAULT)
        self.assertFalse(
            _validate_object_properties(
                mock_object,
                x=X_DEFAULT,
                y=Y_DEFAULT,
                w=W_DEFAULT + 1
            )
        )
