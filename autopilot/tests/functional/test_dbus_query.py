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


import json
import os
import subprocess
import signal
from timeit import default_timer
from tempfile import mktemp
from testtools import skipIf
from testtools.matchers import Equals, NotEquals, raises, LessThan, GreaterThan

from autopilot import platform
from autopilot.testcase import AutopilotTestCase
from autopilot.exceptions import StateNotFoundError


@skipIf(platform.model() != "Desktop", "Only suitable on Desktop (WinMocker)")
class DbusQueryTests(AutopilotTestCase):
    """A collection of dbus query tests for autopilot."""

    def start_fully_featured_app(self):
        """Create an application that includes menus and other nested
        elements.

        """
        window_spec = {
            "Menu": [
                {
                    "Title": "File",
                    "Menu": [
                        "Open",
                        "Save",
                        "Save As",
                        "Quit"
                    ]
                },
                {
                    "Title": "Help",
                    "Menu": [
                        "Help 1",
                        "Help 2",
                        "Help 3",
                        "Help 4"
                    ]
                }
            ],
            "Contents": "TextEdit"
        }

        file_path = mktemp()
        json.dump(window_spec, open(file_path, 'w'))
        self.addCleanup(os.remove, file_path)

        return self.launch_test_application(
            'window-mocker', file_path, app_type="qt")

    def test_select_single_selects_only_available_object(self):
        """Must be able to select a single unique object."""
        app = self.start_fully_featured_app()
        main_window = app.select_single('QMainWindow')
        self.assertThat(main_window, NotEquals(None))

    def test_can_select_parent_of_root(self):
        """Must be able to select the parent of the root object."""
        root = self.start_fully_featured_app()
        root_parent = root.get_parent()
        self.assertThat(root.id, Equals(root_parent.id))

    def test_can_select_parent_of_normal_node(self):
        root = self.start_fully_featured_app()
        main_window = root.select_single('QMainWindow')
        window_parent = main_window.get_parent()
        self.assertThat(window_parent.id, Equals(root.id))

    def test_can_select_specific_parent(self):
        root = self.start_fully_featured_app()
        action_item = root.select_single('QAction', text='Save')
        window_parent = action_item.get_parent('window-mocker')
        self.assertThat(window_parent.id, Equals(root.id))

    def test_select_parent_raises_if_node_not_parent(self):
        root = self.start_fully_featured_app()
        action_item = root.select_single('QAction', text='Save')
        match_fn = lambda: action_item.get_parent('QMadeUpType')
        self.assertThat(match_fn, raises(StateNotFoundError('QMadeUpType')))

    def test_select_parent_with_property_only(self):
        root = self.start_fully_featured_app()
        action_item = root.select_single('QAction', text='Save')
        # The ID of parent of a tree is always 1.
        window_parent = action_item.get_parent(id=1)
        self.assertThat(window_parent.id, Equals(root.id))

    def test_select_parent_raises_if_property_not_match(self):
        root = self.start_fully_featured_app()
        action_item = root.select_single('QAction', text='Save')
        self.assertIsNotNone(action_item.get_parent('QMenu'))
        match_fn = lambda: action_item.get_parent('QMenu', visible=True)
        self.assertThat(
            match_fn,
            raises(StateNotFoundError('QMenu', visible=True))
        )

    def test_single_select_on_object(self):
        """Must be able to select a single unique child of an object."""
        app = self.start_fully_featured_app()
        main_win = app.select_single('QMainWindow')
        menu_bar = main_win.select_single('QMenuBar')
        self.assertThat(menu_bar, NotEquals(None))

    def test_select_multiple_on_object_returns_all(self):
        """Must be able to select all child objects."""
        app = self.start_fully_featured_app()
        main_win = app.select_single('QMainWindow')
        menu_bar = main_win.select_single('QMenuBar')
        menus = menu_bar.select_many('QMenu')
        self.assertThat(len(menus), Equals(2))

    def test_select_multiple_on_object_with_parameter(self):
        """Must be able to select a specific object determined by a
        parameter.

        """
        app = self.start_fully_featured_app()
        main_win = app.select_single('QMainWindow')
        menu_bar = main_win.select_single('QMenuBar')
        help_menu = menu_bar.select_many('QMenu', title='Help')
        self.assertThat(len(help_menu), Equals(1))
        self.assertThat(help_menu[0].title, Equals('Help'))

    def test_select_single_on_object_with_param(self):
        """Must only select a single unique object using a parameter."""
        app = self.start_fully_featured_app()
        main_win = app.select_single('QMainWindow')
        menu_bar = main_win.select_single('QMenuBar')
        help_menu = menu_bar.select_single('QMenu', title='Help')
        self.assertThat(help_menu, NotEquals(None))
        self.assertThat(help_menu.title, Equals('Help'))

    def test_select_many_uses_unique_object(self):
        """Given 2 objects of the same type with childen, selection on one will
        only get its children.

        """
        app = self.start_fully_featured_app()
        main_win = app.select_single('QMainWindow')
        menu_bar = main_win.select_single('QMenuBar')
        help_menu = menu_bar.select_single('QMenu', title='Help')
        actions = help_menu.select_many('QAction')
        self.assertThat(len(actions), Equals(5))

    def test_select_single_no_name_no_parameter_raises_exception(self):
        app = self.start_fully_featured_app()
        fn = lambda: app.select_single()
        self.assertRaises(ValueError, fn)

    def test_select_single_no_match_raises_exception(self):
        app = self.start_fully_featured_app()
        match_fn = lambda: app.select_single("QMadeupType")
        self.assertThat(match_fn, raises(StateNotFoundError('QMadeupType')))

    def test_exception_raised_when_operating_on_dead_app(self):
        app = self.start_fully_featured_app()
        main_window = app.select_single('QMainWindow')
        app.kill_application()
        self.assertRaises(RuntimeError, main_window.get_parent)

    def test_exception_message_when_operating_on_dead_app(self):
        app = self.start_fully_featured_app()
        app.kill_application()
        try:
            app.select_single('QMainWindow')
        except RuntimeError as e:
            msg = ("Lost dbus backend communication. It appears the "
                   "application under test exited before the test "
                   "finished!")
            self.assertEqual(str(e), msg)

    def test_select_single_parameters_only(self):
        app = self.start_fully_featured_app()
        main_win = app.select_single('QMainWindow')
        titled_help = main_win.select_single(title='Help')
        self.assertThat(titled_help, NotEquals(None))
        self.assertThat(titled_help.title, Equals('Help'))

    def test_select_single_parameters_no_match_raises_exception(self):
        app = self.start_fully_featured_app()
        match_fn = lambda: app.select_single(title="Non-existant object")
        self.assertThat(
            match_fn,
            raises(StateNotFoundError('*', title="Non-existant object"))
        )

    def test_select_single_returning_multiple_raises(self):
        app = self.start_fully_featured_app()
        fn = lambda: app.select_single('QMenu')
        self.assertRaises(ValueError, fn)

    def test_select_many_no_name_no_parameter_raises_exception(self):
        app = self.start_fully_featured_app()
        fn = lambda: app.select_single()
        self.assertRaises(ValueError, fn)

    def test_select_many_only_using_parameters(self):
        app = self.start_fully_featured_app()
        many_help_menus = app.select_many(title='Help')
        self.assertThat(len(many_help_menus), Equals(1))

    def test_select_many_with_no_parameter_matches_returns_empty_list(self):
        app = self.start_fully_featured_app()
        failed_match = app.select_many('QMenu', title='qwerty')
        self.assertThat(failed_match, Equals([]))

    def test_select_many_sorted_result(self):
        app = self.start_fully_featured_app()
        un_sorted_texts = [item.text for item in app.select_many('QAction')]
        sorted_texts = [
            item.text for item in app.select_many(
                'QAction',
                ap_result_sort_keys=['text']
            )
        ]
        self.assertNotEqual(un_sorted_texts, sorted_texts)
        self.assertEqual(sorted_texts, sorted(un_sorted_texts))

    def test_wait_select_single_succeeds_quickly(self):
        app = self.start_fully_featured_app()
        start_time = default_timer()
        main_window = app.wait_select_single('QMainWindow')
        end_time = default_timer()
        self.assertThat(main_window, NotEquals(None))
        self.assertThat(abs(end_time - start_time), LessThan(1))

    def test_wait_select_single_timeout_less_than_ten_seconds(self):
        app = self.start_fully_featured_app()
        match_fn = lambda: app.wait_select_single(
            'QMadeupType',
            ap_query_timeout=3
        )
        start_time = default_timer()
        self.assertThat(match_fn, raises(StateNotFoundError('QMadeupType')))
        end_time = default_timer()
        self.assertThat(abs(end_time - start_time), GreaterThan(2))
        self.assertThat(abs(end_time - start_time), LessThan(4))

    def test_wait_select_single_timeout_more_than_ten_seconds(self):
        app = self.start_fully_featured_app()
        match_fn = lambda: app.wait_select_single(
            'QMadeupType',
            ap_query_timeout=12
        )
        start_time = default_timer()
        self.assertThat(match_fn, raises(StateNotFoundError('QMadeupType')))
        end_time = default_timer()
        self.assertThat(abs(end_time - start_time), GreaterThan(11))
        self.assertThat(abs(end_time - start_time), LessThan(13))

    def test_wait_select_many_requested_elements_count_not_match_raises(self):
        app = self.start_fully_featured_app()
        fn = lambda: app.wait_select_many(
            'QMadeupType',
            ap_query_timeout=4,
            ap_result_count=2
        )
        start_time = default_timer()
        self.assertRaises(ValueError, fn)
        end_time = default_timer()
        self.assertThat(abs(end_time - start_time), GreaterThan(3))
        self.assertThat(abs(end_time - start_time), LessThan(5))

    def test_wait_select_many_requested_elements_count_matches(self):
        app = self.start_fully_featured_app()
        start_time = default_timer()
        menus = app.wait_select_many(
            'QMenu',
            ap_query_timeout=4,
            ap_result_count=3
        )
        end_time = default_timer()
        self.assertThat(len(menus), GreaterThan(2))
        self.assertThat(abs(end_time - start_time), LessThan(5))

    def test_wait_select_many_sorted_result(self):
        app = self.start_fully_featured_app()
        start_time = default_timer()
        sorted_action_items = app.wait_select_many(
            'QAction',
            ap_query_timeout=4,
            ap_result_count=10,
            ap_result_sort_keys=['text']
        )
        end_time = default_timer()
        self.assertThat(len(sorted_action_items), GreaterThan(9))
        self.assertThat(abs(end_time - start_time), LessThan(5))
        unsorted_action_items = app.wait_select_many(
            'QAction',
            ap_query_timeout=4,
            ap_result_count=10
        )
        sorted_texts = [item.text for item in sorted_action_items]
        un_sorted_texts = [item.text for item in unsorted_action_items]
        self.assertNotEqual(un_sorted_texts, sorted_texts)
        self.assertEqual(sorted_texts, sorted(un_sorted_texts))


@skipIf(platform.model() != "Desktop", "Only suitable on Desktop (WinMocker)")
class DbusCustomBusTests(AutopilotTestCase):
    """Test the ability to use custom dbus buses during a test."""

    def setUp(self):
        self.dbus_bus_addr = self._enable_custom_dbus_bus()
        super(DbusCustomBusTests, self).setUp()

    def _enable_custom_dbus_bus(self):
        p = subprocess.Popen(['dbus-launch'], stdout=subprocess.PIPE,
                             universal_newlines=True)
        output = p.communicate()
        results = output[0].split("\n")
        dbus_pid = int(results[1].split("=")[1])
        dbus_address = results[0].split("=", 1)[1]

        kill_dbus = lambda pid: os.killpg(pid, signal.SIGTERM)
        self.addCleanup(kill_dbus, dbus_pid)

        return dbus_address

    def _start_mock_app(self, dbus_bus):
        window_spec = {
            "Contents": "TextEdit"
        }

        file_path = mktemp()
        json.dump(window_spec, open(file_path, 'w'))
        self.addCleanup(os.remove, file_path)

        return self.launch_test_application(
            'window-mocker',
            file_path,
            app_type="qt",
            dbus_bus=dbus_bus,
        )

    def test_can_use_custom_dbus_bus(self):
        app = self._start_mock_app(self.dbus_bus_addr)
        self.assertThat(app, NotEquals(None))
