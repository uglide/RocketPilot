# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012, 2013, 2015 Canonical
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


from collections import OrderedDict

from autopilot.utilities import _pick_backend


class ProcessManager(object):

    """A simple process manager class.

    The process manager is used to handle processes, windows and applications.
    This class should not be instantiated directly however. To get an instance
    of the keyboard class, call :py:meth:`create` instead.

    """

    KNOWN_APPS = {
        'Character Map': {
            'desktop-file': 'gucharmap.desktop',
            'process-name': 'gucharmap',
        },
        'Calculator': {
            'desktop-file': 'gcalctool.desktop',
            'process-name': 'gnome-calculator',
        },
        'Mahjongg': {
            'desktop-file': 'gnome-mahjongg.desktop',
            'process-name': 'gnome-mahjongg',
        },
        'Remmina': {
            'desktop-file': 'remmina.desktop',
            'process-name': 'remmina',
        },
        'System Settings': {
            'desktop-file': 'unity-control-center.desktop',
            'process-name': 'unity-control-center',
        },
        'Text Editor': {
            'desktop-file': 'gedit.desktop',
            'process-name': 'gedit',
        },
        'Terminal': {
            'desktop-file': 'gnome-terminal.desktop',
            'process-name': 'gnome-terminal',
        },
    }

    @staticmethod
    def create(preferred_backend=""):
        """Get an instance of the :py:class:`ProcessManager` class.

        For more infomration on picking specific backends, see
        :ref:`tut-picking-backends`

        :param preferred_backend: A string containing a hint as to which
            backend you would like. Possible backends are:

            * ``BAMF`` - Get process information using the BAMF Application
                Matching Framework.

        :raises: RuntimeError if autopilot cannot instantate any of the
            possible backends.
        :raises: RuntimeError if the preferred_backend is specified and is not
            one of the possible backends for this device class.
        :raises: :class:`~autopilot.BackendException` if the preferred_backend
            is set, but that backend could not be instantiated.

        """
        def get_bamf_pm():
            from autopilot.process._bamf import ProcessManager
            return ProcessManager()

        backends = OrderedDict()
        backends['BAMF'] = get_bamf_pm
        return _pick_backend(backends, preferred_backend)

    @classmethod
    def register_known_application(cls, name, desktop_file, process_name):
        """Register an application with autopilot.

        After calling this method, you may call :meth:`start_app` or
        :meth:`start_app_window` with the `name` parameter to start this
        application.
        You need only call this once within a test run - the application will
        remain registerred until the test run ends.

        :param name: The name to be used when launching the application.
        :param desktop_file: The filename (without path component) of the
         desktop file used to launch the application.
        :param process_name: The name of the executable process that gets run.
        :raises: **KeyError** if application has been registered already

        """
        if name in cls.KNOWN_APPS:
            raise KeyError("Application has been registered already")
        else:
            cls.KNOWN_APPS[name] = {
                "desktop-file": desktop_file,
                "process-name": process_name
            }

    @classmethod
    def unregister_known_application(cls, name):
        """Unregister an application with the known_apps dictionary.

        :param name: The name to be used when launching the application.
        :raises: **KeyError** if the application has not been registered.

        """
        if name in cls.KNOWN_APPS:
            del cls.KNOWN_APPS[name]
        else:
            raise KeyError("Application has not been registered")

    def start_app(self, app_name, files=[], locale=None):
        """Start one of the known applications, and kill it on tear down.

        .. warning:: This method will clear all instances of this application
         on tearDown, not just the one opened by this method! We recommend that
         you use the :meth:`start_app_window` method instead, as it is
         generally safer.

        :param app_name: The application name. *This name must either already
         be registered as one of the built-in applications that are supported
         by autopilot, or must have been registered using*
         :meth:`register_known_application` *beforehand.*
        :param files: (Optional) A list of paths to open with the
         given application. *Not all applications support opening files in this
         way.*
        :param locale: (Optional) The locale will to set when the application
         is launched. *If you want to launch an application without any
         localisation being applied, set this parameter to 'C'.*
        :returns: A :class:`~autopilot.process.Application` instance.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def start_app_window(self, app_name, files=[], locale=None):
        """Open a single window for one of the known applications, and close it
        at the end of the test.

        :param app_name: The application name. *This name must either already
         be registered as one of the built-in applications that are supported
         by autopilot, or must have been registered with*
         :meth:`register_known_application` *beforehand.*
        :param files: (Optional) Should be a list of paths to open with the
         given application. *Not all applications support opening files in this
         way.*
        :param locale: (Optional) The locale will to set when the application
         is launched. *If you want to launch an application without any
         localisation being applied, set this parameter to 'C'.*
        :raises: **AssertionError** if no window was opened, or more than one
         window was opened.
        :returns: A :class:`~autopilot.process.Window` instance.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def get_open_windows_by_application(self, app_name):
        """Get a list of ~autopilot.process.Window` instances
        for the given application name.

        :param app_name: The name of one of the well-known applications.
        :returns: A list of :class:`~autopilot.process.Window`
         instances.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def close_all_app(self, app_name):
        raise NotImplementedError("You cannot use this class directly.")

    def get_app_instances(self, app_name):
        raise NotImplementedError("You cannot use this class directly.")

    def app_is_running(self, app_name):
        raise NotImplementedError("You cannot use this class directly.")

    def get_running_applications(self, user_visible_only=True):
        """Get a list of the currently running applications.

        If user_visible_only is True (the default), only applications
        visible to the user in the switcher will be returned.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def get_running_applications_by_desktop_file(self, desktop_file):
        """Return a list of applications with the desktop file *desktop_file*.

        This method will return an empty list if no applications
        are found with the specified desktop file.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def get_open_windows(self, user_visible_only=True):
        """Get a list of currently open windows.

        If *user_visible_only* is True (the default), only applications visible
        to the user in the switcher will be returned.

        The result is sorted to be in stacking order.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def wait_until_application_is_running(self, desktop_file, timeout):
        """Wait until a given application is running.

        :param string desktop_file: The name of the application desktop file.
        :param integer timeout: The maximum time to wait, in seconds. *If set
         to something less than 0, this method will wait forever.*

        :return: true once the application is found, or false if the
         application was not found until the timeout was reached.
        """
        raise NotImplementedError("You cannot use this class directly.")

    def launch_application(self, desktop_file, files=[], wait=True):
        """Launch an application by specifying a desktop file.

        :param files: List of files to pass to the application. *Not all
         apps support this.*
        :type files: List of strings

        .. note:: If `wait` is True, this method will wait up to 10 seconds for
         the application to appear.

        :raises: **TypeError** on invalid *files* parameter.
        :return: The Gobject process object.
        """
        raise NotImplementedError("You cannot use this class directly.")


class Application(object):
    @property
    def desktop_file(self):
        """Get the application desktop file.

        This returns just the filename, not the full path.
        If the application no longer exists, this returns an empty string.
        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def name(self):
        """Get the application name.

        .. note:: This may change according to the current locale. If you want
         a unique string to match applications against, use desktop_file
         instead.

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def icon(self):
        """Get the application icon.

        :return: The name of the icon.

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def is_active(self):
        """Is the application active (i.e. has keyboard focus)?"""
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def is_urgent(self):
        """Is the application currently signalling urgency?"""
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def user_visible(self):
        """Is this application visible to the user?

        .. note:: Some applications (such as the panel) are hidden to the user
         but may still be returned.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def get_windows(self):
        """Get a list of the application windows."""
        raise NotImplementedError("You cannot use this class directly.")


class Window(object):
    @property
    def x_id(self):
        """Get the X11 Window Id."""
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def x_win(self):
        """Get the X11 window object of the underlying window."""
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def get_wm_state(self):
        """Get the state of the underlying window."""
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def name(self):
        """Get the window name.

        .. note:: This may change according to the current locale. If you want
         a unique string to match windows against, use the x_id instead.

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def title(self):
        """Get the window title.

        This may be different from the application name.

        .. note:: This may change depending on the current locale.

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def geometry(self):
        """Get the geometry for this window.

        :return: Tuple containing (x, y, width, height).

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def is_maximized(self):
        """Is the window maximized?

        Maximized in this case means both maximized vertically and
        horizontally. If a window is only maximized in one direction it is not
        considered maximized.

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def application(self):
        """Get the application that owns this window.

        This method may return None if the window does not have an associated
        application. The 'desktop' window is one such example.

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def user_visible(self):
        """Is this window visible to the user in the switcher?"""
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def is_hidden(self):
        """Is this window hidden?

        Windows are hidden when the 'Show Desktop' mode is activated.

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def is_focused(self):
        """Is this window focused?"""
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def is_valid(self):
        """Is this window object valid?

        Invalid windows are caused by windows closing during the construction
        of this object instance.

        """
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def monitor(self):
        """Returns the monitor to which the windows belongs to"""
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def closed(self):
        """Returns True if the window has been closed"""
        raise NotImplementedError("You cannot use this class directly.")

    def close(self):
        """Close the window."""
        raise NotImplementedError("You cannot use this class directly.")

    def set_focus(self):
        raise NotImplementedError("You cannot use this class directly.")
