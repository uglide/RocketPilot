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


from autopilot.testcase import AutopilotTestCase
from testtools.matchers import raises


class ApplicationSupportTests(AutopilotTestCase):

    def test_launch_with_bad_types_raises_typeerror(self):
        """Calling launch_test_application with something other than a string
        must raise a TypeError"""

        self.assertThat(
            lambda: self.launch_test_application(1), raises(TypeError))
        self.assertThat(
            lambda: self.launch_test_application(True), raises(TypeError))
        self.assertThat(
            lambda: self.launch_test_application(1.0), raises(TypeError))
        self.assertThat(
            lambda: self.launch_test_application(object()), raises(TypeError))
        self.assertThat(
            lambda: self.launch_test_application(None), raises(TypeError))
        self.assertThat(
            lambda: self.launch_test_application([]), raises(TypeError))
        self.assertThat(
            lambda: self.launch_test_application((None,)), raises(TypeError))
