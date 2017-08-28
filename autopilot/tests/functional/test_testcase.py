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
from testtools.matchers import Contains
from testtools.content_type import ContentType

from unittest.mock import patch
import time

from autopilot import testcase


class AutopilotTestCaseScreenshotTests(TestCase):
    def test_screenshot_taken_when_test_fails(self):
        class InnerTest(testcase.AutopilotTestCase):
            def test_foo(self):
                self.fail()

        test = InnerTest('test_foo')
        test_run = test.run()

        self.assertFalse(test_run.wasSuccessful())

        screenshot_content = test.getDetails()['FailedTestScreenshot']
        self.assertEqual(
            screenshot_content.content_type,
            ContentType("image", "png")
        )

    def test_take_screenshot(self):
        screenshot_name = self.getUniqueString()

        class InnerTest(testcase.AutopilotTestCase):
            def test_foo(self):
                self.take_screenshot(screenshot_name)

        test = InnerTest('test_foo')
        test_run = test.run()

        self.assertTrue(test_run.wasSuccessful())

        screenshot_content = test.getDetails()[screenshot_name]
        self.assertEqual(
            screenshot_content.content_type,
            ContentType("image", "png")
        )


class TimedRunTestTests(TestCase):

    @patch.object(testcase, 'get_test_timeout', new=lambda: 5)
    def test_timed_run_test_times_out(self):
        class TimedTest(testcase.AutopilotTestCase):

            def test_will_timeout(self):
                time.sleep(10)  # should timeout after 5 seconds

        test = TimedTest('test_will_timeout')
        result = test.run()
        self.assertFalse(result.wasSuccessful())
        self.assertEqual(1, len(result.errors))
        self.assertThat(
            result.errors[0][1],
            Contains('raise TimeoutException()')
        )

    @patch.object(testcase, 'get_test_timeout', new=lambda: 0)
    def test_untimed_run_test_does_not_time_out(self):
        class TimedTest(testcase.AutopilotTestCase):

            def test_wont_timeout(self):
                time.sleep(10)

        test = TimedTest('test_wont_timeout')
        result = test.run()
        self.assertTrue(result.wasSuccessful())
