# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2014 Canonical
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
from unittest.mock import patch

from autopilot.testcase import AutopilotTestCase
from autopilot.application import _launcher


class AutopilotTestCaseClassTests(TestCase):

    """Test functions of the AutopilotTestCase class."""

    @patch('autopilot.testcase.NormalApplicationLauncher')
    def test_launch_test_application(self, nal):
        class LauncherTest(AutopilotTestCase):

            """Test launchers."""

            def test_anything(self):
                pass

        test_case = LauncherTest('test_anything')
        with patch.object(test_case, 'useFixture') as uf:
            result = test_case.launch_test_application('a', 'b', 'c')
            uf.assert_called_once_with(nal.return_value)
            uf.return_value.launch.assert_called_once_with('a', ('b', 'c'))
            self.assertEqual(result, uf.return_value.launch.return_value)

    @patch('autopilot.testcase.ClickApplicationLauncher')
    def test_launch_click_package(self, cal):
        class LauncherTest(AutopilotTestCase):

            """Test launchers."""

            def test_anything(self):
                pass

        test_case = LauncherTest('test_anything')
        with patch.object(test_case, 'useFixture') as uf:
            result = test_case.launch_click_package('a', 'b', ['c', 'd'])
            uf.assert_called_once_with(cal.return_value)
            uf.return_value.launch.assert_called_once_with(
                'a', 'b', ['c', 'd']
            )
            self.assertEqual(result, uf.return_value.launch.return_value)

    @patch('autopilot.testcase.UpstartApplicationLauncher')
    def test_launch_upstart_application_defaults(self, ual):
        class LauncherTest(AutopilotTestCase):

            """Test launchers."""

            def test_anything(self):
                pass

        test_case = LauncherTest('test_anything')
        with patch.object(test_case, 'useFixture') as uf:
            result = test_case.launch_upstart_application(
                'a', ['b'], launcher_class=ual
            )
            uf.assert_called_once_with(ual.return_value)
            uf.return_value.launch.assert_called_once_with('a', ['b'])
            self.assertEqual(result, uf.return_value.launch.return_value)

    def test_launch_upstart_application_custom_launcher(self):
        class LauncherTest(AutopilotTestCase):

            """Test launchers."""

            def test_anything(self):
                pass

        test_case = LauncherTest('test_anything')
        self.assertRaises(
            NotImplementedError,
            test_case.launch_upstart_application,
            'a', ['b'], launcher_class=_launcher.ApplicationLauncher
        )
