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

"""Acceptance tests for the autopilot vis tool."""

import sys

from testtools import skipIf
from testtools.matchers import Equals

from autopilot.introspection.dbus import CustomEmulatorBase
from autopilot.matchers import Eventually
from autopilot.platform import model
from autopilot.testcase import AutopilotTestCase


class VisToolEmulatorBase(CustomEmulatorBase):
    pass


class VisAcceptanceTests(AutopilotTestCase):

    def launch_windowmocker(self):
        return self.launch_test_application("window-mocker", app_type="qt")

    @skipIf(model() != "Desktop", "Vis not usable on device.")
    def test_can_select_windowmocker(self):
        wm = self.launch_windowmocker()
        vis = self.launch_test_application(
            sys.executable,
            '-m', 'autopilot.run', 'vis', '-testability',
            app_type='qt',
        )
        connection_list = vis.select_single('ConnectionList')
        connection_list.slots.trySetSelectedItem(wm.applicationName)
        self.assertThat(
            connection_list.currentText,
            Eventually(Equals(wm.applicationName))
        )
