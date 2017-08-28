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
from testtools.matchers import Equals

import autopilot.globals as _g


def restore_value(cleanup_enabled, object, attr_name):
    """Ensure that, at the end of the current test, object.attr_name is
    restored to it's current state.

    """
    original_value = getattr(object, attr_name)
    cleanup_enabled.addCleanup(
        lambda: setattr(object, attr_name, original_value)
    )


class DebugProfileFunctionTests(TestCase):

    def setUp(self):
        super(DebugProfileFunctionTests, self).setUp()
        # since we're modifying a global in our tests, make sure we restore
        # the original value after each test has run:
        restore_value(self, _g, '_debug_profile_fixture')

    def test_can_set_and_get_fixture(self):
        fake_fixture = object()
        _g.set_debug_profile_fixture(fake_fixture)
        self.assertThat(_g.get_debug_profile_fixture(), Equals(fake_fixture))


class TimeoutFunctionTests(TestCase):

    def setUp(self):
        super(TimeoutFunctionTests, self).setUp()
        # since we're modifying a global in our tests, make sure we restore
        # the original value after each test has run:
        restore_value(self, _g, '_default_timeout_value')
        restore_value(self, _g, '_long_timeout_value')
        restore_value(self, _g, '_test_timeout')

    def test_default_timeout_values(self):
        self.assertEqual(10.0, _g.get_default_timeout_period())
        self.assertEqual(30.0, _g.get_long_timeout_period())

    def test_can_set_default_timeout_value(self):
        new_value = self.getUniqueInteger()
        _g.set_default_timeout_period(new_value)
        self.assertEqual(new_value, _g.get_default_timeout_period())

    def test_can_set_long_timeout_value(self):
        new_value = self.getUniqueInteger()
        _g.set_long_timeout_period(new_value)
        self.assertEqual(new_value, _g.get_long_timeout_period())

    def test_can_set_test_timeout(self):
        new_value = self.getUniqueInteger()
        _g.set_test_timeout(new_value)
        self.assertEqual(new_value, _g.get_test_timeout())
