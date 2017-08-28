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

from contextlib import contextmanager
from timeit import default_timer
from textwrap import dedent
from testtools import skipIf
from testtools.matchers import Equals

import logging
from autopilot import platform
from autopilot.tests.functional import AutopilotRunTestBase


logger = logging.getLogger(__name__)


@contextmanager
def maximum_runtime(max_time):
    start_time = default_timer()
    yield
    total_time = abs(default_timer() - start_time)
    if total_time >= max_time:
        raise AssertionError(
            "Runtime of %f was not within defined "
            "limit of %f" % (total_time, max_time)
        )
    else:
        logger.info(
            "Test completed in %f seconds, which is below the "
            " threshold of %f.",
            total_time,
            max_time
        )


@skipIf(platform.model() != "Desktop", "Only suitable on Desktop (WinMocker)")
class AutopilotPerformanceTests(AutopilotRunTestBase):

    """A suite of functional tests that will fail if autopilot performance
    regresses below certain strictly defined limits.

    Each test must be named after the feature we are benchmarking, and should
    use the maximum_runtime contextmanager defined above.

    """

    def test_autopilot_launch_test_app(self):
        self.create_test_file(
            'test_something.py',
            dedent("""
                from autopilot.testcase import AutopilotTestCase

                class LaunchTestAppTests(AutopilotTestCase):

                    def test_launch_test_app(self):
                        app_proxy = self.launch_test_application(
                            'window-mocker',
                            app_type='qt'
                        )
                """)
        )
        with maximum_runtime(5.0):
            rc, out, err = self.run_autopilot(['run', 'tests'])
            self.assertThat(rc, Equals(0))
