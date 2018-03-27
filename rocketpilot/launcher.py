# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2013,2017 Canonical
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

"""Base module for application launchers."""

import logging
import os
import psutil
import subprocess
import signal

from rocketpilot import constants
from rocketpilot.application import ApplicationItemProxy
from rocketpilot._timeout import Timeout
from rocketpilot.introspection import (
    get_proxy_object_for_existing_process,
)

_logger = logging.getLogger(__name__)


class ApplicationLauncher(object):
    def __init__(self, emulator_base=ApplicationItemProxy, dbus_bus='session'):
        self.proxy_base = emulator_base
        self.dbus_bus = dbus_bus

    def launch(self, application, arguments=None, launch_dir=None, capture_output=False):
        """Launch an application and return a proxy object.

        Use this method to launch an application and start testing it. The
        arguments passed in ``arguments`` are used as arguments to the
        application to launch. Additional keyword arguments are used to control
        the manner in which the application is launched.

        This fixture is designed to be flexible enough to launch all supported
        types of applications. Autopilot can automatically determine how to
        enable introspection support for dynamically linked binary
        applications. For example, to launch a binary Gtk application, a test
        might start with::

            from autopilot.application import NormalApplicationLauncher
            launcher = NormalApplicationLauncher()
            launcher.setUp()
            app_proxy = launcher.launch('gedit')

        For use within a testcase, use useFixture:

            from autopilot.application import NormalApplicationLauncher
            launcher = self.useFixture(NormalApplicationLauncher())
            app_proxy = launcher.launch('gedit')

        Applications can be given command line arguments by supplying an
        ``arguments`` argument to this method. For example, if we want to
        launch ``gedit`` with a certain document loaded, we might do this::

            app_proxy = launcher.launch(
                'gedit', arguments=['/tmp/test-document.txt'])

        ... a Qt5 Qml application is launched in a similar fashion::

            app_proxy = launcher.launch(
                'qmlscene', arguments=['my_scene.qml'])

        :param application: The application to launch. The application can be
            specified as:

             * A full, absolute path to an executable file.
               (``/usr/bin/gedit``)
             * A relative path to an executable file.
               (``./build/my_app``)
             * An app name, which will be searched for in $PATH (``my_app``)

        :keyword arguments: If set, the list of arguments is passed to the
            launched app.

        :keyword launch_dir: If set to a directory that exists the process
            will be launched from that directory.

        :keyword capture_output: If set to True (the default), the process
            output will be captured and attached to the test as test detail.

        :return: A proxy object that represents the application. Introspection
         data is retrievable via this object.

        """
        if arguments is None:
            arguments = []

        _logger.info(
            "Attempting to launch application '%s' with arguments '%s' as a "
            "normal process",
            application,
            ' '.join(arguments)
        )
        self._app_path = app_path = _get_application_path(application)
        app_path, arguments = self._setup_environment(app_path, arguments)
        self._process = process = self._launch_application_process(
            app_path, capture_output, launch_dir, arguments)
        proxy_object = get_proxy_object_for_existing_process(
            dbus_bus=self.dbus_bus,
            emulator_base=self.proxy_base,
            process=process,
            connection_name=constants.ROCKET_PILOT_DBUS_SERVICE_NAME
        )
        proxy_object.set_process(process)
        return proxy_object

    def _setup_environment(self, app_path, arguments):
        return self._prepare_app_env(
            app_path,
            list(arguments),
        )

    def _launch_application_process(self, app_path, capture_output, cwd,
                                    arguments):
        process = launch_process(
            app_path,
            arguments,
            capture_output,
            cwd=cwd,
        )

        return process

    def _prepare_app_env(self, app_path, arguments):
        if '-testability' not in arguments:
            insert_pos = 0
            for pos, argument in enumerate(arguments):
                if argument.startswith("-qt="):
                    insert_pos = pos + 1
                    break
            arguments.insert(insert_pos, '-testability')

        return app_path, arguments

    def clean_up(self):
        if getattr(self, '._process', None):
            self._kill_process_and_attach_logs(self._process, self._app_path)

    def _kill_process_and_attach_logs(self, process, app_path):
        stdout, stderr, return_code = _kill_process(process)


def launch_process(application, args, capture_output=False, **kwargs):
    """Launch an autopilot-enabled process and return the process object."""
    commandline = [application]
    commandline.extend(args)
    _logger.info("Launching process: %r", commandline)
    cap_mode = None
    if capture_output:
        cap_mode = subprocess.PIPE
    process = subprocess.Popen(
        commandline,
        stdin=subprocess.PIPE,
        stdout=cap_mode,
        stderr=cap_mode,
        close_fds=True,
        preexec_fn=os.setsid,
        universal_newlines=True,
        **kwargs
    )
    return process


def _get_application_path(application):
    try:
        return subprocess.check_output(
            ['which', application],
            universal_newlines=True
        ).strip()
    except subprocess.CalledProcessError as e:
        raise ValueError(
            "Unable to find path for application {app}: {reason}"
                .format(app=application, reason=str(e))
        )


def _kill_process(process):
    """Kill the process, and return the stdout, stderr and return code."""
    stdout_parts = []
    stderr_parts = []
    _logger.info("waiting for process to exit.")
    _attempt_kill_pid(process.pid)
    for _ in Timeout.default():
        tmp_out, tmp_err = process.communicate()
        if isinstance(tmp_out, bytes):
            tmp_out = tmp_out.decode('utf-8', errors='replace')
        if isinstance(tmp_err, bytes):
            tmp_err = tmp_err.decode('utf-8', errors='replace')
        stdout_parts.append(tmp_out)
        stderr_parts.append(tmp_err)
        if not psutil.pid_exists(process.pid):
            break
    else:
        _logger.info(
            "Killing process group, since it hasn't exited after "
            "10 seconds."
        )
        _attempt_kill_pid(process.pid, signal.SIGKILL)
    return ''.join(stdout_parts), ''.join(stderr_parts), process.returncode


def _attempt_kill_pid(pid, sig=signal.SIGTERM):
    try:
        _logger.info("Killing process %d", pid)
        os.killpg(pid, sig)
    except OSError:
        _logger.info("Appears process has already exited.")
