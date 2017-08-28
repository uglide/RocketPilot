# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2013-2014 Canonical
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

from unittest.mock import Mock
from testtools import TestCase
from testtools.matchers import raises

from autopilot.testcase import (
    _compare_system_with_process_snapshot,
    _considered_failing_test,
    _get_application_launch_args,
)
from autopilot.utilities import sleep


class ProcessSnapshotTests(TestCase):

    def test_snapshot_returns_when_no_apps_running(self):
        with sleep.mocked() as mock_sleep:
            _compare_system_with_process_snapshot(lambda: [], [])

            self.assertEqual(0.0, mock_sleep.total_time_slept())

    def test_snapshot_raises_AssertionError_with_new_apps_opened(self):
        with sleep.mocked():
            fn = lambda: _compare_system_with_process_snapshot(
                lambda: ['foo'],
                []
            )
            self.assertThat(fn, raises(AssertionError(
                "The following apps were started during the test and "
                "not closed: ['foo']"
            )))

    def test_bad_snapshot_waits_10_seconds(self):
        with sleep.mocked() as mock_sleep:
            try:
                _compare_system_with_process_snapshot(
                    lambda: ['foo'],
                    []
                )
            except:
                pass
            finally:
                self.assertEqual(10.0, mock_sleep.total_time_slept())

    def test_snapshot_does_not_raise_on_closed_old_app(self):
        _compare_system_with_process_snapshot(lambda: [], ['foo'])

    def test_snapshot_exits_after_first_success(self):
        get_snapshot = Mock()
        get_snapshot.side_effect = [['foo'], []]

        with sleep.mocked() as mock_sleep:
            _compare_system_with_process_snapshot(
                get_snapshot,
                []
            )
            self.assertEqual(1.0, mock_sleep.total_time_slept())


class AutopilotTestCaseSupportFunctionTests(TestCase):
    def test_considered_failing_test_returns_true_for_failing(self):
        self.assertTrue(_considered_failing_test(AssertionError))

    def test_considered_failing_test_returns_true_for_unexpected_success(self):
        from unittest.case import _UnexpectedSuccess
        self.assertTrue(_considered_failing_test(_UnexpectedSuccess))

    def test_considered_failing_test_returns_false_for_skip(self):
        from unittest.case import SkipTest
        self.assertFalse(_considered_failing_test(SkipTest))

    def test_considered_failing_test_returns_false_for_inherited_skip(self):
        from unittest.case import SkipTest

        class CustomSkip(SkipTest):
            pass

        self.assertFalse(_considered_failing_test(CustomSkip))

    def test_considered_failing_test_returns_false_for_expected_fail(self):
        from testtools.testcase import _ExpectedFailure
        self.assertFalse(_considered_failing_test(_ExpectedFailure))

    def test_considered_failing_test_returns_false_for_inherited_expected_fail(self):  # NOQA
        from testtools.testcase import _ExpectedFailure

        class CustomExpected(_ExpectedFailure):
            pass

        self.assertFalse(_considered_failing_test(CustomExpected))


class AutopilotGetApplicationLaunchArgsTests(TestCase):

    def test_when_no_args_returns_empty_dict(self):
        self.assertEqual(_get_application_launch_args(dict()), dict())

    def test_ignores_unknown_args(self):
        self.assertEqual(_get_application_launch_args(dict(unknown="")), {})

    def test_gets_argument_values(self):
        app_type_value = self.getUniqueString()

        self.assertEqual(
            _get_application_launch_args(dict(app_type=app_type_value)),
            dict(app_type=app_type_value)
        )

    def test_gets_argument_values_ignores_unknown_values(self):
        app_type_value = self.getUniqueString()
        kwargs = dict(app_type=app_type_value, unknown=self.getUniqueString())
        self.assertEqual(
            _get_application_launch_args(kwargs),
            dict(app_type=app_type_value)
        )

    def test_removes_used_arguments_from_parameter(self):
        app_type_value = self.getUniqueString()
        kwargs = dict(app_type=app_type_value)
        _get_application_launch_args(kwargs)
        self.assertEqual(kwargs, dict())
