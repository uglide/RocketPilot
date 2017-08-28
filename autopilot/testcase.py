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


"""
Quick Start
===========

The :class:`AutopilotTestCase` is the main class test authors will be
interacting with. Every autopilot test case should derive from this class.
:class:`AutopilotTestCase` derives from :class:`testtools.TestCase`, so test
authors can use all the methods defined in that class as well.

**Writing tests**

Tests must be named: ``test_<testname>``, where *<testname>* is the name of the
test. Test runners (including autopilot itself) look for methods with this
naming convention. It is recommended that you make your test names descriptive
of what each test is testing. For example, possible test names include::

    test_ctrl_p_opens_print_dialog
    test_dash_remembers_maximized_state

**Launching the Application Under Test**

If you are writing a test for an application, you need to use the
:meth:`~AutopilotTestCase.launch_test_application` method. This will launch the
application, enable introspection, and return a proxy object representing the
root of the application introspection tree.

"""

import logging

import fixtures
from testtools import TestCase, RunTest
from testtools.content import ContentType, content_from_stream
from testtools.matchers import Equals
from testtools.testcase import _ExpectedFailure
from unittest.case import SkipTest

from autopilot.application import (
    ClickApplicationLauncher,
    NormalApplicationLauncher,
    UpstartApplicationLauncher,
)
from autopilot.display import Display, get_screenshot_data
from autopilot.globals import get_debug_profile_fixture, get_test_timeout
from autopilot.input import Keyboard, Mouse
from autopilot.keybindings import KeybindingsHelper
from autopilot.matchers import Eventually
from autopilot.platform import get_display_server
from autopilot.process import ProcessManager
from autopilot.utilities import deprecated, on_test_started
from autopilot._fixtures import OSKAlwaysEnabled
from autopilot._timeout import Timeout
from autopilot._logging import TestCaseLoggingFixture
from autopilot._video import get_video_recording_fixture
try:
    from autopilot import tracepoint as tp
    HAVE_TRACEPOINT = True
except ImportError:
    HAVE_TRACEPOINT = False

_logger = logging.getLogger(__name__)


try:
    from testscenarios.scenarios import multiply_scenarios
except ImportError:
    from itertools import product

    def multiply_scenarios(*scenarios):
        """Multiply two or more iterables of scenarios.

        It is safe to pass scenario generators or iterators.

        :returns: A list of compound scenarios: the cross-product of all
            scenarios, with the names concatenated and the parameters
            merged together.
        """
        result = []
        scenario_lists = map(list, scenarios)
        for combination in product(*scenario_lists):
            names, parameters = zip(*combination)
            scenario_name = ','.join(names)
            scenario_parameters = {}
            for parameter in parameters:
                scenario_parameters.update(parameter)
            result.append((scenario_name, scenario_parameters))
        return result


def _lttng_trace_test_started(test_id):
    if HAVE_TRACEPOINT:
        tp.emit_test_started(test_id)
    else:
        _logger.warning(
            "No tracing available - install the python-autopilot-trace "
            "package!")


def _lttng_trace_test_ended(test_id):
    if HAVE_TRACEPOINT:
        tp.emit_test_ended(test_id)


class _TimedRunTest(RunTest):

    def run(self, *args, **kwargs):
        timeout = get_test_timeout()
        if timeout > 0:
            with fixtures.Timeout(timeout, True):
                return super().run(*args, **kwargs)
        else:
            return super().run(*args, **kwargs)


class AutopilotTestCase(TestCase, KeybindingsHelper):

    """Wrapper around testtools.TestCase that adds significant functionality.

    This class should be the base class for all autopilot test case classes.
    Not using this class as the base class disables several important
    convenience methods, and also prevents the use of the failed-test
    recording tools.

    """

    run_tests_with = _TimedRunTest

    def setUp(self):
        super(AutopilotTestCase, self).setUp()
        on_test_started(self)
        self.useFixture(
            TestCaseLoggingFixture(
                self.shortDescription(),
                self.addDetailUniqueName,
            )
        )
        self.useFixture(get_debug_profile_fixture()(self.addDetailUniqueName))
        self.useFixture(get_video_recording_fixture()(self))
        _lttng_trace_test_started(self.id())
        self.addCleanup(_lttng_trace_test_ended, self.id())

        self._process_manager = None
        self._mouse = None
        self._display = None
        #self._kb = Keyboard.create()

        # Instatiate this after keyboard creation to ensure it doesn't get
        # overwritten
        # Workaround for bug lp:1474444
        self.useFixture(OSKAlwaysEnabled())

        # Work around for bug lp:1297592.
        _ensure_uinput_device_created()

        if get_display_server() == 'X11':
            try:
                self._app_snapshot = _get_process_snapshot()
                self.addCleanup(self._compare_system_with_app_snapshot)
            except RuntimeError:
                _logger.warning(
                    "Process manager backend unavailable, application "
                    "snapshot support disabled.")

        self.addOnException(self._take_screenshot_on_failure)

    @property
    def process_manager(self):
        if self._process_manager is None:
            self._process_manager = ProcessManager.create()
        return self._process_manager

    @property
    def keyboard(self):
        return self._kb

    @property
    def mouse(self):
        if self._mouse is None:
            self._mouse = Mouse.create()
        return self._mouse

    @property
    def display(self):
        if self._display is None:
            self._display = Display.create()
        return self._display

    def launch_test_application(self, application, *arguments, **kwargs):
        """Launch ``application`` and return a proxy object for the
        application.

        Use this method to launch an application and start testing it. The
        positional arguments are used as arguments to the application to lanch.
        Keyword arguments are used to control the manner in which the
        application is launched.

        This method is designed to be flexible enough to launch all supported
        types of applications. Autopilot can automatically determine how to
        enable introspection support for dynamically linked binary
        applications. For example, to launch a binary Gtk application, a test
        might start with::

            app_proxy = self.launch_test_application('gedit')

        Applications can be given command line arguments by supplying
        positional arguments to this method. For example, if we want to launch
        ``gedit`` with a certain document loaded, we might do this::

            app_proxy = self.launch_test_application(
                'gedit', '/tmp/test-document.txt')

        ... a Qt5 Qml application is launched in a similar fashion::

            app_proxy = self.launch_test_application(
                'qmlscene', 'my_scene.qml')

        If you wish to launch an application that is not a dynamically linked
        binary, you must specify the application type. For example, a Qt4
        python application might be launched like this::

            app_proxy = self.launch_test_application(
                'my_qt_app.py', app_type='qt')

        Similarly, a python/Gtk application is launched like so::

            app_proxy = self.launch_test_application(
                'my_gtk_app.py', app_type='gtk')

        :param application: The application to launch. The application can be
            specified as:

             * A full, absolute path to an executable file.
               (``/usr/bin/gedit``)
             * A relative path to an executable file.
               (``./build/my_app``)
             * An app name, which will be searched for in $PATH (``my_app``)

        :keyword app_type: If set, provides a hint to autopilot as to which
            kind of introspection to enable. This is needed when the
            application you wish to launch is *not* a dynamically linked
            binary. Valid values are 'gtk' or 'qt'. These strings are case
            insensitive.

        :keyword launch_dir: If set to a directory that exists the process
            will be launched from that directory.

        :keyword capture_output: If set to True (the default), the process
            output will be captured and attached to the test as test detail.

        :keyword emulator_base: If set, specifies the base class to be used for
            all emulators for this loaded application.

        :return: A proxy object that represents the application. Introspection
         data is retrievable via this object.

        """
        launch_args = _get_application_launch_args(kwargs)

        launcher = self.useFixture(
            NormalApplicationLauncher(
                case_addDetail=self.addDetailUniqueName,
                **kwargs
            )
        )
        return launcher.launch(application, arguments, **launch_args)

    def launch_click_package(self, package_id, app_name=None, app_uris=[],
                             **kwargs):
        """Launch a click package application with introspection enabled.

        This method takes care of launching a click package with introspection
        exabled. You probably want to use this method if your application is
        packaged in a click application, or is started via upstart.

        Usage is similar to the
        :py:meth:`AutopilotTestCase.launch_test_application`::

            app_proxy = self.launch_click_package(
                "com.ubuntu.dropping-letters"
            )

        :param package_id: The Click package name you want to launch. For
            example: ``com.ubuntu.dropping-letters``
        :param app_name: Currently, only one application can be packaged in a
            click package, and this parameter can be left at None. If
            specified, it should be the application name you wish to launch.
        :param app_uris: Parameters used to launch the click package. This
            parameter will be left empty if not used.

        :keyword emulator_base: If set, specifies the base class to be used for
            all emulators for this loaded application.

        :raises RuntimeError: If the specified package_id cannot be found in
            the click package manifest.
        :raises RuntimeError: If the specified app_name cannot be found within
            the specified click package.

        :returns: proxy object for the launched package application

        """
        launcher = self.useFixture(
            ClickApplicationLauncher(
                case_addDetail=self.addDetailUniqueName,
                **kwargs
            )
        )
        return launcher.launch(package_id, app_name, app_uris)

    def launch_upstart_application(self, application_name, uris=[],
                                   launcher_class=UpstartApplicationLauncher,
                                   **kwargs):
        """Launch an application with upstart.

        This method launched an application via the ``ubuntu-app-launch``
        library, on platforms that support it.

        Usage is similar to the
        :py:meth:`AutopilotTestCase.launch_test_application`::

            app_proxy = self.launch_upstart_application("gallery-app")

        :param application_name: The name of the application to launch.
        :param launcher_class: The application launcher class to use. Useful if
        you need to overwrite the default to do something custom (i.e. using
          AlreadyLaunchedUpstartLauncher)
        :keyword emulator_base: If set, specifies the base class to be used for
            all emulators for this loaded application.

        :raises RuntimeError: If the specified application cannot be launched.
        """
        launcher = self.useFixture(
            launcher_class(
                case_addDetail=self.addDetailUniqueName,
                **kwargs
            )
        )
        return launcher.launch(application_name, uris)

    def _compare_system_with_app_snapshot(self):
        """Compare the currently running application with the last snapshot.

        This method will raise an AssertionError if there are any new
        applications currently running that were not running when the snapshot
        was taken.
        """
        try:
            _compare_system_with_process_snapshot(
                _get_process_snapshot,
                self._app_snapshot
            )
        finally:
            self._app_snapshot = None

    def take_screenshot(self, attachment_name):
        """Take a screenshot of the current screen and adds it to the test as a
        detail named *attachment_name*.

        If *attachment_name* already exists as a detail the name will be
        modified to remove the naming conflict
        (i.e. using TestCase.addDetailUniqueName).

        Returns True if the screenshot was taken and attached successfully,
        False otherwise.

        """
        try:
            image_content = content_from_stream(
                get_screenshot_data(get_display_server()),
                content_type=ContentType('image', 'png'),
                buffer_now=True
            )
            self.addDetailUniqueName(attachment_name, image_content)
            return True
        except Exception as e:
            logging.error(
                "Taking screenshot failed: {exception}".format(exception=e)
            )
            return False

    def _take_screenshot_on_failure(self, ex_info):
        failure_class_type = ex_info[0]
        if _considered_failing_test(failure_class_type):
            self.take_screenshot("FailedTestScreenshot")

    @deprecated('fixtures.EnvironmentVariable')
    def patch_environment(self, key, value):
        """Patch environment using fixture.

        This function is deprecated and planned for removal in autopilot 1.6.
        New implementations should use EnvironmenVariable from the fixtures
        module::

            from fixtures import EnvironmentVariable

            def my_test(AutopilotTestCase):
                my_patch = EnvironmentVariable('key', 'value')
                self.useFixture(my_patch)

        'key' will be set to 'value'.  During tearDown, it will be reset to a
        previous value, if one is found, or unset if not.

        """
        self.useFixture(fixtures.EnvironmentVariable(key, value))

    def assertVisibleWindowStack(self, stack_start):
        """Check that the visible window stack starts with the windows passed
        in.

        .. note:: Minimised windows are skipped.

        :param stack_start: An iterable of
         :class:`~autopilot.process.Window` instances.
        :raises AssertionError: if the top of the window stack does not
         match the contents of the stack_start parameter.

        """
        stack = [
            win for win in
            self.process_manager.get_open_windows() if not win.is_hidden]
        for pos, win in enumerate(stack_start):
            self.assertThat(
                stack[pos].x_id, Equals(win.x_id),
                "%r at %d does not equal %r" % (stack[pos], pos, win))

    def assertProperty(self, obj, **kwargs):
        """Assert that *obj* has properties equal to the key/value pairs in
        kwargs.

        This method is intended to be used on objects whose attributes do not
        have the :meth:`wait_for` method (i.e.- objects that do not come from
        the autopilot DBus interface).

        For example, from within a test, to assert certain properties on a
        `~autopilot.process.Window` instance::

            self.assertProperty(my_window, is_maximized=True)

        .. note:: assertProperties is a synonym for this method.

        :param obj: The object to test.
        :param kwargs: One or more keyword arguments to match against the
         attributes of the *obj* parameter.
        :raises ValueError: if no keyword arguments were given.
        :raises ValueError: if a named attribute is a callable object.
        :raises AssertionError: if any of the attribute/value pairs in
         kwargs do not match the attributes on the object passed in.

        """
        if not kwargs:
            raise ValueError("At least one keyword argument must be present.")

        for prop_name, desired_value in kwargs.items():
            none_val = object()
            attr = getattr(obj, prop_name, none_val)
            if attr == none_val:
                raise AssertionError(
                    "Object %r does not have an attribute named '%s'"
                    % (obj, prop_name))
            if callable(attr):
                raise ValueError(
                    "Object %r's '%s' attribute is a callable. It must be a "
                    "property." % (obj, prop_name))
            self.assertThat(
                lambda: getattr(obj, prop_name),
                Eventually(Equals(desired_value)))

    assertProperties = assertProperty


def _get_application_launch_args(kwargs):
    """Returns a dict containing relevant args and values for launching an
    application.

    Removes used arguments from kwargs parameter.

    """
    launch_args = {}
    launch_arg_list = ['app_type', 'launch_dir', 'capture_output']
    for arg in launch_arg_list:
        if arg in kwargs:
            launch_args[arg] = kwargs.pop(arg)
    return launch_args


def _get_process_snapshot():
    """Return a snapshot of running processes on the system.

    :returns: a list of running processes.
    :raises RuntimeError: if the process manager is unsavailble on this
        platform.

    """
    return ProcessManager.create().get_running_applications()


def _compare_system_with_process_snapshot(snapshot_fn, old_snapshot):
    """Compare an existing process snapshot with current running processes.

    :param snapshot_fn: A callable that returns the current running process
        list.
    :param old_snapshot: A list of processes to compare against.
    :raises AssertionError: If, after 10 seconds, there are still running
        processes that were not present in ``old_snapshot``.

    """
    new_apps = []
    for _ in Timeout.default():
        current_apps = snapshot_fn()
        new_apps = [app for app in current_apps if app not in old_snapshot]
        if not new_apps:
            return
    raise AssertionError(
        "The following apps were started during the test and not closed: "
        "%r" % new_apps)


def _ensure_uinput_device_created():
    # This exists for a work around for bug lp:1297592. Need to create
    # an input device before an application launch.
    try:
        from autopilot.input._uinput import Touch, _UInputTouchDevice
        if _UInputTouchDevice._device is None:
            Touch.create()
    except Exception as e:
        _logger.warning(
            "Failed to create Touch device for bug lp:1297595 workaround: "
            "%s" % str(e)
        )


def _considered_failing_test(failure_class_type):
    return (
        not issubclass(failure_class_type, SkipTest)
        and not issubclass(failure_class_type, _ExpectedFailure)
    )
