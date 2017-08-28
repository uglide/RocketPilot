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
from testtools.matchers import Equals, GreaterThan

from autopilot.globals import (
    get_default_timeout_period,
    get_long_timeout_period,
    set_default_timeout_period,
    set_long_timeout_period,
)
from autopilot._timeout import Timeout
from autopilot.utilities import sleep


class TimeoutClassTests(TestCase):

    def setUp(self):
        super(TimeoutClassTests, self).setUp()
        # We need to ignore the settings the autopilot runner may set,
        # otherwise we cannot make any meaningful assertions in these tests.
        self.addCleanup(
            set_default_timeout_period,
            get_default_timeout_period()
        )
        set_default_timeout_period(10.0)
        self.addCleanup(
            set_long_timeout_period,
            get_long_timeout_period()
        )
        set_long_timeout_period(30.0)

    def test_medium_sleeps_for_correct_time(self):
        with sleep.mocked() as mocked_sleep:
            for _ in Timeout.default():
                pass
            self.assertEqual(10.0, mocked_sleep.total_time_slept())

    def test_long_sleeps_for_correct_time(self):
        with sleep.mocked() as mocked_sleep:
            for _ in Timeout.long():
                pass
            self.assertEqual(30.0, mocked_sleep.total_time_slept())

    def test_medium_elapsed_time_increases(self):
        with sleep.mocked():
            last_elapsed = None
            for elapsed in Timeout.default():
                if last_elapsed is not None:
                    self.assertThat(elapsed, GreaterThan(last_elapsed))
                else:
                    self.assertEqual(elapsed, 0.0)
                last_elapsed = elapsed

    def test_long_elapsed_time_increases(self):
        with sleep.mocked():
            last_elapsed = None
            for elapsed in Timeout.long():
                if last_elapsed is not None:
                    self.assertThat(elapsed, GreaterThan(last_elapsed))
                else:
                    self.assertEqual(elapsed, 0.0)
                last_elapsed = elapsed

    def test_medium_timeout_final_call(self):
        set_default_timeout_period(0.0)
        self.assertThat(len(list(Timeout.default())), Equals(1))

    def test_long_timeout_final_call(self):
        set_long_timeout_period(0.0)
        self.assertThat(len(list(Timeout.long())), Equals(1))
