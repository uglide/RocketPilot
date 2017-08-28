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


import os.path
from testtools import skipIf
from testtools.matchers import Equals

from autopilot import platform
from autopilot.testcase import AutopilotTestCase
from autopilot.process import ProcessManager
import logging
logger = logging.getLogger(__name__)


@skipIf(platform.model() != "Desktop", "Not suitable for device (ProcManager)")
class OpenWindowTests(AutopilotTestCase):

    scenarios = [
        (
            k,
            {
                'app_name': k,
                'app_details': v,
            }
        ) for k, v in ProcessManager.KNOWN_APPS.items()
    ]

    def test_open_window(self):
        """self.start_app_window must open a new window of the given app."""
        if not os.path.exists(
            os.path.join(
                '/usr/share/applications',
                self.app_details['desktop-file']
            )
        ):
            self.skip("Application '%s' is not installed" % self.app_name)
        existing_apps = self.process_manager.get_app_instances(self.app_name)
        # if we opened the app, ensure that we close it again to avoid leaking
        # processes like remmina
        if not existing_apps:
            self.addCleanup(self.process_manager.close_all_app, self.app_name)
        old_wins = []
        for app in existing_apps:
            old_wins.extend(app.get_windows())
        logger.debug("Old windows: %r", old_wins)

        win = self.process_manager.start_app_window(self.app_name)
        logger.debug("New window: %r", win)
        is_new = win.x_id not in [w.x_id for w in old_wins]
        self.assertThat(is_new, Equals(True))
