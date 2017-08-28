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

from testtools import TestCase, skipIf

import autopilot.platform as platform


class PublicAPITests(TestCase):

    @skipIf(platform.model() != "Desktop", "Only available on desktop.")
    def test_get_display_server_returns_x11(self):
        self.assertEqual(platform.get_display_server(), "X11")

    @skipIf(platform.model() == "Desktop", "Only available on device.")
    def test_get_display_server_returns_mir(self):
        self.assertEqual(platform.get_display_server(), "MIR")
