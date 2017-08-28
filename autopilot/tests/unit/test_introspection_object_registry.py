# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2014, 2015 Canonical
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

from unittest.mock import patch
from testtools import TestCase
from testtools.matchers import (
    Equals,
    raises,
)

from autopilot.introspection import CustomEmulatorBase
from autopilot.introspection import _object_registry as object_registry
from autopilot.introspection import _xpathselect as xpathselect


class MakeIntrospectionObjectTests(TestCase):

    class DefaultSelector(CustomEmulatorBase):
        pass

    class AlwaysSelected(CustomEmulatorBase):
        @classmethod
        def validate_dbus_object(cls, path, state):
            """Validate always.

            :returns: True

            """
            return True

    class NeverSelected(CustomEmulatorBase):
        @classmethod
        def validate_dbus_object(cls, path, state):
            """Validate never.

            :returns: False

            """
            return False

    @patch.object(object_registry, '_try_custom_proxy_classes')
    @patch.object(object_registry, '_get_default_proxy_class')
    def test_get_proxy_object_class_return_from_list(self, gdpc, tcpc):
        """_get_proxy_object_class should return the value of
        _try_custom_proxy_classes if there is one."""
        token = self.getUniqueString()
        tcpc.return_value = token
        gpoc_return = object_registry._get_proxy_object_class(
            "fake_id",  # cannot set to none.
            None,
            None
        )

        self.assertThat(gpoc_return, Equals(token))
        self.assertFalse(gdpc.called)

    @patch.object(object_registry, '_try_custom_proxy_classes')
    def test_get_proxy_object_class_send_right_args(self, tcpc):
        """_get_proxy_object_class should send the right arguments to
        _try_custom_proxy_classes."""
        class_dict = {'DefaultSelector': self.DefaultSelector}
        path = '/path/to/DefaultSelector'
        state = {}
        object_registry._get_proxy_object_class(class_dict, path, state)
        tcpc.assert_called_once_with(class_dict, path, state)

    @patch.object(object_registry, '_try_custom_proxy_classes')
    def test_get_proxy_object_class_not_handle_error(self, tcpc):
        """_get_proxy_object_class should not handle an exception raised by
        _try_custom_proxy_classes."""
        tcpc.side_effect = ValueError
        self.assertThat(
            lambda: object_registry._get_proxy_object_class(
                "None",  # Cannot be set to None, but don't care about value
                None,
                None
            ),
            raises(ValueError))

    @patch.object(object_registry, '_try_custom_proxy_classes')
    @patch.object(object_registry, '_get_default_proxy_class')
    @patch.object(object_registry, 'get_classname_from_path')
    def test_get_proxy_object_class_call_default_call(self, gcfp, gdpc, tcpc):
        """_get_proxy_object_class should call _get_default_proxy_class if
        _try_custom_proxy_classes returns None."""
        tcpc.return_value = None
        object_registry._get_proxy_object_class(None, None, None)
        self.assertTrue(gdpc.called)

    @patch.object(object_registry, '_try_custom_proxy_classes')
    @patch.object(object_registry, '_get_default_proxy_class')
    def test_get_proxy_object_class_default_args(self, gdpc, tcpc):
        """_get_proxy_object_class should pass the correct arguments to
        _get_default_proxy_class"""
        tcpc.return_value = None
        obj_id = 123
        path = '/path/to/DefaultSelector'
        object_registry._get_proxy_object_class(obj_id, path, None)
        gdpc.assert_called_once_with(
            obj_id,
            xpathselect.get_classname_from_path(path)
        )

    @patch.object(object_registry, '_try_custom_proxy_classes')
    @patch.object(object_registry, '_get_default_proxy_class')
    @patch.object(object_registry, 'get_classname_from_path')
    def test_get_proxy_object_class_default(self, gcfp, gdpc, tcpc):
        """_get_proxy_object_class should return the value of
        _get_default_proxy_class if _try_custom_proxy_classes returns None."""
        token = self.getUniqueString()
        gdpc.return_value = token
        tcpc.return_value = None
        gpoc_return = object_registry._get_proxy_object_class(
            None,
            None,
            None,
        )
        self.assertThat(gpoc_return, Equals(token))

    def test_try_custom_proxy_classes_zero_results(self):
        """_try_custom_proxy_classes must return None if no classes match."""
        proxy_class_dict = {'NeverSelected': self.NeverSelected}
        fake_id = self.getUniqueInteger()
        path = '/path/to/NeverSelected'
        state = {}
        with object_registry.patch_registry({fake_id: proxy_class_dict}):
            class_type = object_registry._try_custom_proxy_classes(
                fake_id,
                path,
                state
            )
        self.assertThat(class_type, Equals(None))

    def test_try_custom_proxy_classes_one_result(self):
        """_try_custom_proxy_classes must return the matching class if there is
        exacly 1."""
        proxy_class_dict = {'DefaultSelector': self.DefaultSelector}
        fake_id = self.getUniqueInteger()
        path = '/path/to/DefaultSelector'
        state = {}
        with object_registry.patch_registry({fake_id: proxy_class_dict}):
            class_type = object_registry._try_custom_proxy_classes(
                fake_id,
                path,
                state
            )
        self.assertThat(class_type, Equals(self.DefaultSelector))

    def test_try_custom_proxy_classes_two_results(self):
        """_try_custom_proxy_classes must raise ValueError if multiple classes
        match."""
        proxy_class_dict = {'DefaultSelector': self.DefaultSelector,
                            'AlwaysSelected': self.AlwaysSelected}
        path = '/path/to/DefaultSelector'
        state = {}
        object_id = self.getUniqueInteger()
        with object_registry.patch_registry({object_id: proxy_class_dict}):
            self.assertThat(
                lambda: object_registry._try_custom_proxy_classes(
                    object_id,
                    path,
                    state
                ),
                raises(ValueError)
            )

    @patch('autopilot.introspection._object_registry.get_debug_logger')
    def test_get_default_proxy_class_logging(self, gdl):
        """_get_default_proxy_class should log a message."""
        object_registry._get_default_proxy_class(self.DefaultSelector, "None")
        gdl.assert_called_once_with()

    def test_get_default_proxy_class_base(self):
        """Subclass must return an emulator of base class."""
        class SubclassedProxy(self.DefaultSelector):
            pass

        result = object_registry._get_default_proxy_class(
            SubclassedProxy,
            'Object'
        )
        self.assertTrue(result, Equals(self.DefaultSelector))

    def test_get_default_proxy_class_base_instead_of_self(self):
        """Subclass must not use self if base class works."""
        class SubclassedProxy(self.DefaultSelector):
            pass

        result = object_registry._get_default_proxy_class(
            SubclassedProxy,
            'Object'
        )
        self.assertFalse(issubclass(result, SubclassedProxy))

    def test_get_default_proxy_class(self):
        """Must default to own class if no usable bases present."""
        result = object_registry._get_default_proxy_class(
            self.DefaultSelector,
            'Object'
        )
        self.assertTrue(result, Equals(self.DefaultSelector))

    def test_get_default_proxy_name(self):
        """Must default to own class if no usable bases present."""
        token = self.getUniqueString()
        result = object_registry._get_default_proxy_class(
            self.DefaultSelector,
            token
        )
        self.assertThat(result.__name__, Equals(token))


class ObjectRegistryPatchTests(TestCase):

    def test_patch_registry_sets_new_registry(self):
        new_registry = dict(foo=123)
        with object_registry.patch_registry(new_registry):
            self.assertEqual(object_registry._object_registry, new_registry)

    def test_patch_registry_undoes_patch(self):
        old_registry = object_registry._object_registry.copy()
        with object_registry.patch_registry({}):
            pass
        self.assertEqual(object_registry._object_registry, old_registry)

    def test_patch_registry_undoes_patch_when_exception_raised(self):
        def patch_reg():
            with object_registry.patch_registry({}):
                raise RuntimeError()

        old_registry = object_registry._object_registry.copy()
        try:
            patch_reg()
        except RuntimeError:
            pass
        self.assertEqual(object_registry._object_registry, old_registry)

    def test_patch_registry_reraised_caught_exception(self):
        def patch_reg():
            with object_registry.patch_registry({}):
                raise RuntimeError()

        self.assertThat(patch_reg, raises(RuntimeError()))

    def test_modifications_are_unwound(self):
        token = self.getUniqueString()
        with object_registry.patch_registry(dict()):
            object_registry._object_registry[token] = token
        self.assertFalse(token in object_registry._object_registry)


class CombineBasesTests(TestCase):
    def test_returns_original_if_no_extensions(self):
        class Base():
            pass

        class Sub(Base):
            pass

        self.assertEqual(
            object_registry._combine_base_and_extensions(Sub, ()),
            (Base,)
        )

    def test_returns_addition_of_extension_classes(self):
        class Base():
            pass

        class Sub(Base):
            pass

        class Ext1():
            pass

        class Ext2():
            pass

        mixed = object_registry._combine_base_and_extensions(Sub, (Ext1, Ext2))

        self.assertIn(Ext1, mixed)
        self.assertIn(Ext2, mixed)

    def test_excludes_duplication_of_base_class_within_extension_classes(self):
        class Base():
            pass

        class Sub(Base):
            pass

        class Ext1():
            pass

        class Ext2(Ext1):
            pass

        self.assertEqual(
            object_registry._combine_base_and_extensions(Sub, (Ext2, Base)),
            (Ext2, Base,)
        )

    def test_excludes_addition_of_extension_base_classes(self):
        class Base():
            pass

        class Sub(Base):
            pass

        class Ext1():
            pass

        class Ext2(Ext1):
            pass

        self.assertNotIn(
            object_registry._combine_base_and_extensions(Sub, (Ext2,)),
            Ext1
        )

    def test_excludes_addition_of_subject_class(self):
        class Base():
            pass

        class Sub(Base):
            pass

        class Ext1():
            pass

        self.assertEqual(
            object_registry._combine_base_and_extensions(Sub, (Ext1, Sub)),
            (Ext1, Base)
        )

    def test_maintains_mro_order(self):
        class Base():
            pass

        class Sub1(Base):
            pass

        class Sub2(Sub1, Base):
            pass

        class Ext1():
            pass

        mixed = object_registry._combine_base_and_extensions(Sub2, (Ext1,))

        self.assertLess(
            mixed.index(Sub1),
            mixed.index(Base)
        )


class MROSortOrderTests(TestCase):
    def test_returns_lower_values_for_lower_classes_in_mro(self):
        class Parent():
            pass

        class Child(Parent):
            pass

        class GrandChild(Child):
            pass

        self.assertGreater(
            object_registry._get_mro_sort_order(Child),
            object_registry._get_mro_sort_order(Parent),
        )
        self.assertGreater(
            object_registry._get_mro_sort_order(GrandChild),
            object_registry._get_mro_sort_order(Child),
        )

    def test_return_higher_values_for_promoted_collections_in_ties(self):
        class Parent1():
            pass

        class Child1(Parent1):
            pass

        class Parent2():
            pass

        class Child2(Parent2):
            pass

        promoted_collection = (Parent1, Child1)

        self.assertGreater(
            object_registry._get_mro_sort_order(
                Child1, promoted_collection),
            object_registry._get_mro_sort_order(
                Child2, promoted_collection),
        )
