# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2014 Canonical
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


"""BAMF implementation of the Process Management"""

import dbus
import dbus.glib
from gi.repository import Gio
from gi.repository import GLib
import logging
import os
from Xlib import display, X, protocol
from subprocess import check_output, CalledProcessError, call

import autopilot._glib
from autopilot._timeout import Timeout
from autopilot.dbus_handler import get_session_bus
from autopilot.process import (
    ProcessManager as ProcessManagerBase,
    Application as ApplicationBase,
    Window as WindowBase
)
from autopilot.utilities import (
    addCleanup,
    Silence,
)


_BAMF_BUS_NAME = 'org.ayatana.bamf'
_X_DISPLAY = None

_logger = logging.getLogger(__name__)


def get_display():
    """Create an Xlib display object (silently) and return it."""
    global _X_DISPLAY
    if _X_DISPLAY is None:
        with Silence():
            _X_DISPLAY = display.Display()
    return _X_DISPLAY


def _filter_user_visible(win):
    """Filter out non-user-visible objects.

    In some cases the DBus method we need to call hasn't been registered yet,
    in which case we do the safe thing and return False.

    """
    try:
        return win.user_visible
    except dbus.DBusException:
        return False


class ProcessManager(ProcessManagerBase):
    """High-level class for interacting with Bamf from within a test.

    Use this class to inspect the state of running applications and open
    windows.

    """

    def __init__(self):
        matcher_path = '/org/ayatana/bamf/matcher'
        self.matcher_interface_name = 'org.ayatana.bamf.matcher'
        self.matcher_proxy = get_session_bus().get_object(
            _BAMF_BUS_NAME, matcher_path)
        self.matcher_interface = dbus.Interface(
            self.matcher_proxy, self.matcher_interface_name)

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
        window = self._open_window(app_name, files, locale)
        if window:
            addCleanup(self.close_all_app, app_name)
            return window.application

        raise AssertionError("No new application window was opened.")

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
        window = self._open_window(app_name, files, locale)
        if window:
            addCleanup(window.close)
            return window
        raise AssertionError("No window was opened.")

    def _open_window(self, app_name, files, locale):
        """Open a new 'app_name' window, returning the window instance or None.

        Raises an AssertionError if this creates more than one window.

        """
        existing_windows = self.get_open_windows_by_application(app_name)

        if locale:
            os.putenv("LC_ALL", locale)
            addCleanup(os.unsetenv, "LC_ALL")
            _logger.info(
                "Starting application '%s' with files %r in locale %s",
                app_name, files, locale)
        else:
            _logger.info(
                "Starting application '%s' with files %r", app_name, files)

        app = self.KNOWN_APPS[app_name]
        self._launch_application(app['desktop-file'], files)
        apps = self.get_running_applications_by_desktop_file(
            app['desktop-file'])

        for _ in Timeout.default():
            try:
                new_windows = []
                [new_windows.extend(a.get_windows()) for a in apps]
                filter_fn = lambda w: w.x_id not in [
                    c.x_id for c in existing_windows]
                new_wins = list(filter(filter_fn, new_windows))
                if new_wins:
                    assert len(new_wins) == 1
                    return new_wins[0]
            except dbus.DBusException:
                pass
        return None

    def get_open_windows_by_application(self, app_name):
        """Get a list of ~autopilot.process.Window` instances
        for the given application name.

        :param app_name: The name of one of the well-known applications.
        :returns: A list of :class:`~autopilot.process.Window`
         instances.

        """
        existing_windows = []
        [existing_windows.extend(a.get_windows()) for a in
         self.get_app_instances(app_name)]
        return existing_windows

    def close_all_app(self, app_name):
        """Close all instances of the application 'app_name'."""
        app = self.KNOWN_APPS[app_name]
        try:
            pids = check_output(["pidof", app['process-name']]).split()
            if len(pids):
                call(["kill"] + pids)
        except CalledProcessError:
            _logger.warning(
                "Tried to close applicaton '%s' but it wasn't running.",
                app_name)

    def get_app_instances(self, app_name):
        """Get `~autopilot.process.Application` instances for app_name."""
        desktop_file = self.KNOWN_APPS[app_name]['desktop-file']
        return self.get_running_applications_by_desktop_file(desktop_file)

    def app_is_running(self, app_name):
        """Return true if an instance of the application is running."""
        apps = self.get_app_instances(app_name)
        return len(apps) > 0

    def get_running_applications(self, user_visible_only=True):
        """Get a list of the currently running applications.

        If user_visible_only is True (the default), only applications
        visible to the user in the switcher will be returned.

        """
        apps = [Application(p) for p in
                self.matcher_interface.RunningApplications()]
        if user_visible_only:
            return list(filter(_filter_user_visible, apps))
        return apps

    def get_running_applications_by_desktop_file(self, desktop_file):
        """Return a list of applications with the desktop file *desktop_file*.

        This method will return an empty list if no applications are found
        with the specified desktop file.

        """
        apps = []
        for a in self.get_running_applications():
            try:
                if a.desktop_file == desktop_file:
                    apps.append(a)
            except dbus.DBusException:
                pass
        return apps

    def get_open_windows(self, user_visible_only=True):
        """Get a list of currently open windows.

        If *user_visible_only* is True (the default), only applications visible
        to the user in the switcher will be returned.

        The result is sorted to be in stacking order.

        """

        windows = [Window(w) for w in
                   self.matcher_interface.WindowStackForMonitor(-1)]
        if user_visible_only:
            windows = list(filter(_filter_user_visible, windows))
        # Now sort on stacking order.
        # We explicitly convert to a list from an iterator since tests
        # frequently try and use len() on return values from these methods.
        return list(reversed(windows))

    def wait_until_application_is_running(self, desktop_file, timeout):
        """Wait until a given application is running.

        :param string desktop_file: The name of the application desktop file.
        :param integer timeout: The maximum time to wait, in seconds. *If set
         to something less than 0, this method will wait forever.*

        :return: true once the application is found, or false if the
         application was not found until the timeout was reached.
        """
        desktop_file = os.path.split(desktop_file)[1]
        # python workaround since you can't assign to variables in the
        # enclosing scope: see on_timeout_reached below...
        found_app = [True]

        # maybe the app is running already?
        running_applications = self.get_running_applications_by_desktop_file(
            desktop_file)
        if len(running_applications) == 0:
            wait_forever = timeout < 0
            gobject_loop = GLib.MainLoop()

            # No, so define a callback to watch the ViewOpened signal:
            def on_view_added(bamf_path, name):
                if bamf_path.split('/')[-2].startswith('application'):
                    app = Application(bamf_path)
                    if desktop_file == os.path.split(app.desktop_file)[1]:
                        gobject_loop.quit()

            # ...and one for when the user-defined timeout has been reached:
            def on_timeout_reached():
                gobject_loop.quit()
                found_app[0] = False
                return False

            # need a timeout? if so, connect it:
            if not wait_forever:
                GLib.timeout_add(timeout * 1000, on_timeout_reached)
            # connect signal handler:
            get_session_bus().add_signal_receiver(on_view_added, 'ViewOpened')
            # pump the gobject main loop until either the correct signal is
            # emitted, or the timeout happens.
            gobject_loop.run()

        return found_app[0]

    def _launch_application(self, desktop_file, files=[], wait=True):
        """Launch an application by specifying a desktop file.

        :param files: List of files to pass to the application. *Not all
         apps support this.*
        :type files: List of strings

        .. note:: If `wait` is True, this method will wait up to 10 seconds for
         the application to appear in the BAMF model.


        :raises: **TypeError** on invalid *files* parameter.
        :return: The Gobject process object.
        """
        if type(files) is not list:
            raise TypeError("files must be a list.")
        proc = _launch_application(desktop_file, files)
        if wait:
            self.wait_until_application_is_running(desktop_file, 10)
        return proc


def _launch_application(desktop_file, files):
    proc = Gio.DesktopAppInfo.new(desktop_file)
    # simple launch_uris() uses GLib.SpawnFlags.SEARCH_PATH by default only,
    # but this inherits stdout; we don't want that as it hangs when tee'ing
    # autopilot output into a file.
    # Instead of depending on a newer version of gir/glib attempt to use the
    # newer verison (i.e. launch_uris_as_manager works) and fall back on using
    # the simple launch_uris
    try:
        proc.launch_uris_as_manager(
            files, None,
            GLib.SpawnFlags.SEARCH_PATH | GLib.SpawnFlags.STDOUT_TO_DEV_NULL,
            None, None, None, None)
    except TypeError:
        proc.launch_uris(files, None)


class Application(ApplicationBase):
    """Represents an application, with information as returned by Bamf.

    .. important:: Don't instantiate this class yourself. instead, use the
     methods as provided by the Bamf class.

    :raises: **dbus.DBusException** in the case of a DBus error.

    """
    def __init__(self, bamf_app_path):
        self.bamf_app_path = bamf_app_path
        try:
            self._app_proxy = get_session_bus().get_object(
                _BAMF_BUS_NAME, bamf_app_path)
            self._view_iface = dbus.Interface(
                self._app_proxy, 'org.ayatana.bamf.view')
            self._app_iface = dbus.Interface(
                self._app_proxy, 'org.ayatana.bamf.application')
        except dbus.DBusException as e:
            e.args += ('bamf_app_path=%r' % (bamf_app_path),)
            raise

    @property
    def desktop_file(self):
        """Get the application desktop file.

        This just returns the filename, not the full path.
        If the application no longer exists, this returns an empty string.
        """
        try:
            return os.path.split(self._app_iface.DesktopFile())[1]
        except dbus.DBusException:
            return ""

    @property
    def name(self):
        """Get the application name.

        .. note:: This may change according to the current locale. If you want
         a unique string to match applications against, use the desktop_file
         instead.

        """
        return self._view_iface.Name()

    @property
    def icon(self):
        """Get the application icon.

        :return: The name of the icon.

        """
        return self._view_iface.Icon()

    @property
    def is_active(self):
        """Is the application active (i.e.- has keyboard focus)?"""
        return self._view_iface.IsActive()

    @property
    def is_urgent(self):
        """Is the application currently signalling urgency?"""
        return self._view_iface.IsUrgent()

    @property
    def user_visible(self):
        """Is this application visible to the user?

        .. note:: Some applications (such as the panel) are hidden to the user
         but will still be returned by bamf.

        """
        return self._view_iface.UserVisible()

    def get_windows(self):
        """Get a list of the application windows."""
        return [Window(w) for w in self._view_iface.Children()]

    def __repr__(self):
        return "<Application '%s'>" % (self.name)

    def __eq__(self, other):
        if other is None:
            return False
        return self.desktop_file == other.desktop_file


class Window(WindowBase):
    """Represents an application window, as returned by Bamf.

    .. important:: Don't instantiate this class yourself. Instead, use the
     appropriate methods in Application.

    """
    def __init__(self, window_path):
        self._bamf_win_path = window_path
        self._app_proxy = get_session_bus().get_object(
            _BAMF_BUS_NAME, window_path)
        self._window_iface = dbus.Interface(
            self._app_proxy, 'org.ayatana.bamf.window')
        self._view_iface = dbus.Interface(
            self._app_proxy, 'org.ayatana.bamf.view')

        self._xid = int(self._window_iface.GetXid())
        self._x_root_win = get_display().screen().root
        self._x_win = get_display().create_resource_object(
            'window', self._xid)

    @property
    def x_id(self):
        """Get the X11 Window Id."""
        return self._xid

    @property
    def x_win(self):
        """Get the X11 window object of the underlying window."""
        return self._x_win

    @property
    def name(self):
        """Get the window name.

        .. note:: This may change according to the current locale. If you want
         a unique string to match windows against, use the x_id instead.

        """
        return self._view_iface.Name()

    @property
    def title(self):
        """Get the window title.

        This may be different from the application name.

        .. note:: This may change depending on the current locale.

        """
        return self._getProperty('_NET_WM_NAME')

    @property
    def geometry(self):
        """Get the geometry for this window.

        :return: Tuple containing (x, y, width, height).

        """
        # Note: MUST import these here, rather than at the top of the file.
        # Why? Because sphinx imports these modules to build the API
        # documentation, which in turn tries to import Gdk, which in turn
        # fails because there's no DISPlAY environment set in the package
        # builder.
        Gdk = autopilot._glib._import_gdk()
        GdkX11 = autopilot._glib._import_gdkx11()
        # FIXME: We need to use the gdk window here to get the real coordinates
        geometry = self._x_win.get_geometry()
        origin = GdkX11.X11Window.foreign_new_for_display(
            Gdk.Display().get_default(), self._xid).get_origin()
        return (origin[1], origin[2], geometry.width, geometry.height)

    @property
    def is_maximized(self):
        """Is the window maximized?

        Maximized in this case means both maximized vertically and
        horizontally. If a window is only maximized in one direction it is not
        considered maximized.

        """
        win_state = self._get_window_states()
        return '_NET_WM_STATE_MAXIMIZED_VERT' in win_state and \
            '_NET_WM_STATE_MAXIMIZED_HORZ' in win_state

    @property
    def application(self):
        """Get the application that owns this window.

        This method may return None if the window does not have an associated
        application. The 'desktop' window is one such example.

        """
        # BAMF returns a list of parents since some windows don't have an
        # associated application. For these windows we return none.
        parents = self._view_iface.Parents()
        if parents:
            return Application(parents[0])
        else:
            return None

    @property
    def user_visible(self):
        """Is this window visible to the user in the switcher?"""
        return self._view_iface.UserVisible()

    @property
    def is_hidden(self):
        """Is this window hidden?

        Windows are hidden when the 'Show Desktop' mode is activated.

        """
        win_state = self._get_window_states()
        return '_NET_WM_STATE_HIDDEN' in win_state

    @property
    def is_focused(self):
        """Is this window focused?"""
        win_state = self._get_window_states()
        return '_NET_WM_STATE_FOCUSED' in win_state

    @property
    def is_valid(self):
        """Is this window object valid?

        Invalid windows are caused by windows closing during the construction
        of this object instance.

        """
        return self._x_win is not None

    @property
    def monitor(self):
        """Returns the monitor to which the windows belongs to"""
        return self._window_iface.Monitor()

    @property
    def closed(self):
        """Returns True if the window has been closed"""
        # This will return False when the window is closed and then removed
        # from BUS.
        try:
            return (self._window_iface.GetXid() != self.x_id)
        except:
            return True

    def close(self):
        """Close the window."""

        self._setProperty('_NET_CLOSE_WINDOW', [0, 0])

    def set_focus(self):
        self._x_win.set_input_focus(X.RevertToParent, X.CurrentTime)
        self._x_win.configure(stack_mode=X.Above)

    def __repr__(self):
        return "<Window '%s' Xid: %d>" % (
            self.title if self._x_win else '', self.x_id)

    def _getProperty(self, _type):
        """Get an X11 property.

        _type is a string naming the property type. win is the X11 window
        object.

        """
        atom = self._x_win.get_full_property(
            get_display().get_atom(_type), X.AnyPropertyType)
        if atom:
            return atom.value

    def _setProperty(self, _type, data, mask=None):
        if type(data) is str:
            dataSize = 8
        else:
            # data length must be 5 - pad with 0's if it's short, truncate
            # otherwise.
            data = (data + [0] * (5 - len(data)))[:5]
            dataSize = 32

        ev = protocol.event.ClientMessage(
            window=self._x_win, client_type=get_display().get_atom(_type),
            data=(dataSize, data))

        if not mask:
            mask = (X.SubstructureRedirectMask | X.SubstructureNotifyMask)
        self._x_root_win.send_event(ev, event_mask=mask)
        get_display().sync()

    def _get_window_states(self):
        """Return a list of strings representing the current window state."""

        get_display().sync()
        return [get_display().get_atom_name(p)
                for p in self._getProperty('_NET_WM_STATE')]

    def resize(self, width, height):
        """Resize the window.

        :param width: The new width for the window.
        :param height: The new height for the window.

        """
        self.x_win.configure(width=width, height=height)
        self.x_win.change_attributes(
            win_gravity=X.NorthWestGravity, bit_gravity=X.StaticGravity)
        # A call to get the window geometry commits the changes.
        self.geometry
