# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012, 2013, 2014, 2015 Canonical
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

import os
import sys
from subprocess import Popen, call
from textwrap import dedent
from threading import Thread
from time import sleep
from timeit import default_timer

from testtools import skipIf
from testtools.matchers import Equals, GreaterThan, NotEquals, LessThan

from autopilot.exceptions import BackendException
from autopilot.matchers import Eventually
from autopilot.platform import model
from autopilot.process import ProcessManager
from autopilot.testcase import AutopilotTestCase
from autopilot.tests.functional.fixtures import ExecutableScript


@skipIf(model() != "Desktop", "Not suitable for device (ProcManager)")
class ProcessEmulatorTests(AutopilotTestCase):

    def ensure_gedit_not_running(self):
        """Close any open gedit applications."""
        apps = self.process_manager.get_running_applications_by_desktop_file(
            'gedit.desktop')
        if apps:
            # this is a bit brutal, but easier in this context than the
            # alternative.
            call(['killall', 'gedit'])

    def test_wait_for_app_running_works(self):
        """Make sure we can wait for an application to start."""
        def start_gedit():
            sleep(5)
            Popen(['gedit'])

        self.addCleanup(self.ensure_gedit_not_running)
        start = default_timer()
        t = Thread(target=start_gedit())
        t.start()
        ret = self.process_manager.wait_until_application_is_running(
            'gedit.desktop', 10)
        end = default_timer()
        t.join()

        self.assertThat(ret, Equals(True))
        self.assertThat(end - start, GreaterThan(5))

    def test_wait_for_app_running_times_out_correctly(self):
        """Make sure the bamf emulator times out correctly if no app is
        started."""
        self.ensure_gedit_not_running()

        start = default_timer()
        ret = self.process_manager.wait_until_application_is_running(
            'gedit.desktop', 5)
        end = default_timer()

        self.assertThat(abs(end - start - 5.0), LessThan(1))
        self.assertThat(ret, Equals(False))

    def test_start_app(self):
        """Ensure we can start an Application."""
        app = self.process_manager.start_app('Calculator')

        self.assertThat(app, NotEquals(None))
        # locale='C' does not work here as this goes through bamf, so we can't
        # assert the precise name
        self.assertThat(app.name, NotEquals(''))
        self.assertThat(app.desktop_file, Equals('gcalctool.desktop'))

    def test_start_app_window(self):
        """Ensure we can start an Application Window."""
        app = self.process_manager.start_app_window('Calculator', locale='C')

        self.assertThat(app, NotEquals(None))
        self.assertThat(app.name, Equals('Calculator'))

    @skipIf(model() != 'Desktop', "Bamf only available on desktop (Qt4)")
    def test_bamf_geometry_gives_reliable_results(self):
        script = dedent("""\
            #!%s
            from PyQt4.QtGui import QMainWindow, QApplication
            from sys import argv

            app = QApplication(argv)
            win = QMainWindow()
            win.show()
            app.exec_()
            """ % sys.executable)
        path = self.useFixture(ExecutableScript(script)).path
        app_proxy = self.launch_test_application(path, app_type='qt')
        proxy_window = app_proxy.select_single('QMainWindow')
        pm = ProcessManager.create()
        window = [
            w for w in pm.get_open_windows()
            if w.name == os.path.basename(path)
        ][0]
        self.assertThat(list(window.geometry), Equals(proxy_window.geometry))


@skipIf(model() != "Desktop", "Not suitable for device (ProcManager)")
class StartKnowAppsTests(AutopilotTestCase):

    scenarios = [
        (app_name, {
            'app_name': app_name,
            'desktop_file': (
                ProcessManager.KNOWN_APPS[app_name]['desktop-file'])
        })
        for app_name in ProcessManager.KNOWN_APPS
    ]

    def test_start_app_window(self):
        """Ensure we can start all the known applications."""
        app = self.process_manager.start_app_window(self.app_name, locale='C')

        self.assertThat(app, NotEquals(None))


class ProcessManagerApplicationNoCleanupTests(AutopilotTestCase):
    """Testing the process manager without the automated cleanup that running
    within as an AutopilotTestCase provides.

    """

    def test_can_close_all_app(self):
        """Ensure that closing an app actually closes all app instances."""
        try:
            process_manager = ProcessManager.create(preferred_backend="BAMF")
        except BackendException as e:
            self.skip("Test is only for BAMF backend ({}).".format(str(e)))

        process_manager.start_app('Calculator')

        process_manager.close_all_app('Calculator')

        # ps/pgrep lists gnome-calculator as gnome-calculato (see lp
        # bug:1174911)
        ret_code = call(["pgrep", "-c", "gnome-calculato"])
        self.assertThat(ret_code, Equals(1), "Application is still running")


@skipIf(model() != "Desktop", "Not suitable for device (X11)")
class BAMFResizeWindowTestCase(AutopilotTestCase):
    """Tests for the BAMF window helpers."""

    scenarios = [
        ('increase size', dict(delta_width=40, delta_height=40)),
        ('decrease size', dict(delta_width=-40, delta_height=-40))
    ]

    def start_mock_window(self):
        self.launch_test_application(
            'window-mocker',
            app_type='qt'
        )

        try:
            process_manager = ProcessManager.create(preferred_backend='BAMF')
        except BackendException as e:
            self.skip('Test is only for BAMF backend ({}).'.format(str(e)))

        window = [
            w for w in process_manager.get_open_windows()
            if w.name == 'Default Window Title'
        ][0]

        return window

    def test_resize_window_must_update_width_and_height_geometry(self):
        window = self.start_mock_window()

        def get_size():
            _, _, width, height = window.geometry
            return width, height

        initial_width, initial_height = get_size()

        expected_width = initial_width + self.delta_width
        expected_height = initial_height + self.delta_height
        window.resize(width=expected_width, height=expected_height)

        self.assertThat(
            get_size, Eventually(Equals((expected_width, expected_height))))
