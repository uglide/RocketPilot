# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2016 Canonical
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

from testtools import TestCase

from autopilot.introspection.dbus import raises
from autopilot.introspection.utilities import process_util, sort_by_keys
from autopilot.tests.unit.introspection_base import (
    get_mock_object,
    get_global_rect,
)

PROCESS_NAME = 'dummy_process'
PROCESS_WITH_SINGLE_INSTANCE = [{'name': PROCESS_NAME, 'pid': -80}]
PROCESS_WITH_MULTIPLE_INSTANCES = [
    PROCESS_WITH_SINGLE_INSTANCE[0],
    {'name': PROCESS_NAME, 'pid': -81}
]
# a list of dummy co-ordinates
X_COORDS = [0, 0, 0, 0]
Y_COORDS = [7, 9, 18, 14]


class ProcessUtilitiesTestCase(TestCase):

    def test_passing_non_running_process_raises(self):
        self.assertRaises(
            ValueError,
            process_util._query_pids_for_process,
            PROCESS_NAME
        )

    def test_passing_running_process_not_raises(self):
        with process_util.mocked(PROCESS_WITH_SINGLE_INSTANCE):
            self.assertFalse(
                raises(
                    ValueError,
                    process_util._query_pids_for_process,
                    PROCESS_NAME
                )
            )

    def test_passing_integer_raises(self):
        self.assertRaises(
            ValueError,
            process_util._query_pids_for_process,
            911
        )

    def test_pid_for_process_is_int(self):
        with process_util.mocked(PROCESS_WITH_SINGLE_INSTANCE):
            self.assertIsInstance(
                process_util.get_pid_for_process(PROCESS_NAME),
                int
            )

    def test_pids_for_process_is_list(self):
        with process_util.mocked(PROCESS_WITH_MULTIPLE_INSTANCES):
            self.assertIsInstance(
                process_util.get_pids_for_process(PROCESS_NAME),
                list
            )

    def test_passing_process_with_multiple_pids_raises(self):
        with process_util.mocked(PROCESS_WITH_MULTIPLE_INSTANCES):
            self.assertRaises(
                ValueError,
                process_util.get_pid_for_process,
                PROCESS_NAME
            )


class SortByKeysTests(TestCase):
    def _get_root_property_from_object_list(self, objects, prop):
        return [getattr(obj, prop) for obj in objects]

    def _get_child_property_from_object_list(self, objects, child, prop):
        return [getattr(getattr(obj, child), prop) for obj in objects]

    def test_sort_by_single_property(self):
        objects = [get_mock_object(y=y) for y in Y_COORDS]
        sorted_objects = sort_by_keys(objects, ['y'])
        self.assertEqual(len(sorted_objects), len(objects))
        self.assertEqual(
            self._get_root_property_from_object_list(sorted_objects, 'y'),
            sorted(Y_COORDS)
        )

    def test_sort_by_multiple_properties(self):
        objects = [
            get_mock_object(x=x, y=y) for x, y in zip(X_COORDS, Y_COORDS)
        ]

        sorted_objects = sort_by_keys(objects, ['x', 'y'])
        self.assertEqual(len(sorted_objects), len(objects))
        self.assertEqual(
            self._get_root_property_from_object_list(sorted_objects, 'x'),
            sorted(X_COORDS)
        )
        self.assertEqual(
            self._get_root_property_from_object_list(sorted_objects, 'y'),
            sorted(Y_COORDS)
        )

    def test_sort_by_single_nested_property(self):
        objects = [
            get_mock_object(globalRect=get_global_rect(y=y)) for y in Y_COORDS
        ]
        sorted_objects = sort_by_keys(objects, ['globalRect.y'])
        self.assertEqual(len(sorted_objects), len(objects))
        self.assertEqual(
            self._get_child_property_from_object_list(
                sorted_objects,
                child='globalRect',
                prop='y'
            ),
            sorted(Y_COORDS)
        )

    def test_sort_by_multiple_nested_properties(self):
        objects = [
            get_mock_object(globalRect=get_global_rect(x=x, y=y))
            for x, y in zip(X_COORDS, Y_COORDS)
        ]
        sorted_objects = sort_by_keys(
            objects,
            ['globalRect.x', 'globalRect.y']
        )
        self.assertEqual(len(sorted_objects), len(objects))
        self.assertEqual(
            self._get_child_property_from_object_list(
                sorted_objects,
                child='globalRect',
                prop='x'
            ),
            sorted(X_COORDS)
        )
        self.assertEqual(
            self._get_child_property_from_object_list(
                sorted_objects,
                child='globalRect',
                prop='y'
            ),
            sorted(Y_COORDS)
        )

    def test_sort_three_levels_nested_property(self):
        objects = [
            get_mock_object(
                fake_property=get_global_rect(
                    y=get_global_rect(y=y)
                )
            ) for y in Y_COORDS
        ]
        sorted_objects = sort_by_keys(objects, ['fake_property.y.y'])
        self.assertEqual(len(sorted_objects), len(objects))
        sorted_ys = [i.fake_property.y.y for i in sorted_objects]
        self.assertEqual(sorted_ys, sorted(Y_COORDS))

    def test_raises_if_sort_keys_not_list(self):
        self.assertRaises(ValueError, sort_by_keys, None, 'y')

    def test_returns_unchanged_if_one_object(self):
        obj = [get_mock_object()]
        output = sort_by_keys(obj, ['x'])
        self.assertEqual(output, obj)
