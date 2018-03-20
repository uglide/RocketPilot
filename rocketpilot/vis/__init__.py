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


import dbus
import sys


def vis_main():
    # To aid in testing only import when we are launching the GUI component
    from dbus.mainloop.pyqt5 import DBusQtMainLoop
    from PyQt5 import QtWidgets
    from rocketpilot.vis.main_window import MainWindow
    from rocketpilot.launcher import ApplicationLauncher

    if len(sys.argv) < 2:
        print("Usage: rocketpilot-vis APP_PATH [APP_ARGS]")
        exit(1)

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Autopilot")
    app.setOrganizationName("Canonical")

    dbus_loop = DBusQtMainLoop(set_as_default=True)
    session_bus = dbus.SessionBus(mainloop=dbus_loop)

    window = MainWindow(session_bus)

    launcher = ApplicationLauncher()

    if len(sys.argv) > 2:
        args = sys.argv[2:]
    else:
        args = []

    window.app = launcher.launch(sys.argv[1], arguments=args)
    window.on_proxy_object_built(window.app)

    window.show()
    sys.exit(app.exec_())
