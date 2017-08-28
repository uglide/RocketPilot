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

from testtools import skipIf, TestCase
from testtools.matchers import Equals
from unittest.mock import patch

from autopilot import platform
from autopilot.input import Pointer, Mouse


@skipIf(platform.model() != "Desktop", "Not suitable for device (X11)")
class MouseEmulatorTests(TestCase):
    """Tests for the autopilot mouse emulator."""

    def setUp(self):
        super(MouseEmulatorTests, self).setUp()
        self.mouse = Pointer(Mouse.create())

    def tearDown(self):
        super(MouseEmulatorTests, self).tearDown()
        self.mouse = None

    def test_x_y_properties(self):
        """x and y properties must simply return values from the position()
        method."""
        with patch.object(
                self.mouse._device, 'position', return_value=(42, 37)):
            self.assertThat(self.mouse.x, Equals(42))
            self.assertThat(self.mouse.y, Equals(37))
