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

from contextlib import ExitStack
from gi.repository import GLib
import signal
import subprocess
from testtools import TestCase
from testtools.matchers import (
    Contains,
    Equals,
    GreaterThan,
    HasLength,
    IsInstance,
    MatchesListwise,
    Not,
    raises,
)
from testtools.content import text_content
from unittest.mock import MagicMock, Mock, patch

from autopilot.application import (
    ClickApplicationLauncher,
    NormalApplicationLauncher,
    UpstartApplicationLauncher,
)
from autopilot.application._environment import (
    GtkApplicationEnvironment,
    QtApplicationEnvironment,
)
import autopilot.application._launcher as _l
from autopilot.application._launcher import (
    ApplicationLauncher,
    get_application_launcher_wrapper,
    launch_process,
    _attempt_kill_pid,
    _get_app_env_from_string_hint,
    _get_application_environment,
    _get_application_path,
    _get_click_app_id,
    _get_click_manifest,
    _is_process_running,
    _kill_process,
)
from autopilot.utilities import sleep


class ApplicationLauncherTests(TestCase):
    def test_raises_on_attempt_to_use_launch(self):
        self.assertThat(
            lambda: ApplicationLauncher(self.addDetail).launch(),
            raises(
                NotImplementedError("Sub-classes must implement this method.")
            )
        )

    def test_init_uses_default_values(self):
        launcher = ApplicationLauncher()
        self.assertEqual(launcher.caseAddDetail, launcher.addDetail)
        self.assertEqual(launcher.proxy_base, None)
        self.assertEqual(launcher.dbus_bus, 'session')

    def test_init_uses_passed_values(self):
        case_addDetail = self.getUniqueString()
        emulator_base = self.getUniqueString()
        dbus_bus = self.getUniqueString()

        launcher = ApplicationLauncher(
            case_addDetail=case_addDetail,
            emulator_base=emulator_base,
            dbus_bus=dbus_bus,
        )
        self.assertEqual(launcher.caseAddDetail, case_addDetail)
        self.assertEqual(launcher.proxy_base, emulator_base)
        self.assertEqual(launcher.dbus_bus, dbus_bus)

    @patch('autopilot.application._launcher.fixtures.EnvironmentVariable')
    def test_setUp_patches_environment(self, ev):
        self.useFixture(ApplicationLauncher(dbus_bus=''))
        ev.assert_called_with('DBUS_SESSION_BUS_ADDRESS', '')


class NormalApplicationLauncherTests(TestCase):

    def test_kill_process_and_attach_logs(self):
        mock_addDetail = Mock()
        app_launcher = NormalApplicationLauncher(mock_addDetail)

        with patch.object(
            _l, '_kill_process', return_value=("stdout", "stderr", 0)
        ):
            app_launcher._kill_process_and_attach_logs(0, 'app')

            self.assertThat(
                mock_addDetail.call_args_list,
                MatchesListwise([
                    Equals(
                        [('process-return-code (app)', text_content('0')), {}]
                    ),
                    Equals(
                        [('process-stdout (app)', text_content('stdout')), {}]
                    ),
                    Equals(
                        [('process-stderr (app)', text_content('stderr')), {}]
                    ),
                ])
            )

    def test_setup_environment_returns_prepare_environment_return_value(self):
        app_launcher = self.useFixture(NormalApplicationLauncher())
        with patch.object(_l, '_get_application_environment') as gae:
            self.assertThat(
                app_launcher._setup_environment(
                    self.getUniqueString(), None, []),
                Equals(gae.return_value.prepare_environment.return_value)
            )

    @patch('autopilot.application._launcher.'
           'get_proxy_object_for_existing_process')
    @patch('autopilot.application._launcher._get_application_path')
    def test_launch_call_to_get_application_path(self, gap, _):
        """Test that NormalApplicationLauncher.launch calls
        _get_application_path with the arguments it was passed,"""
        launcher = NormalApplicationLauncher()
        with patch.object(launcher, '_launch_application_process'):
            with patch.object(launcher, '_setup_environment') as se:
                se.return_value = ('', [])
                token = self.getUniqueString()
                launcher.launch(token)
                gap.assert_called_once_with(token)

    @patch('autopilot.application._launcher.'
           'get_proxy_object_for_existing_process')
    @patch('autopilot.application._launcher._get_application_path')
    def test_launch_call_to_setup_environment(self, gap, _):
        """Test the NornmalApplicationLauncher.launch calls
        self._setup_environment with the correct application path from
        _get_application_path and the arguments passed to it."""
        launcher = NormalApplicationLauncher()
        with patch.object(launcher, '_launch_application_process'):
            with patch.object(launcher, '_setup_environment') as se:
                se.return_value = ('', [])
                token_a = self.getUniqueString()
                token_b = self.getUniqueString()
                token_c = self.getUniqueString()
                launcher.launch(token_a, arguments=[token_b, token_c])
                se.assert_called_once_with(
                    gap.return_value,
                    None,
                    [token_b, token_c],
                )

    @patch('autopilot.application._launcher.'
           'get_proxy_object_for_existing_process')
    @patch('autopilot.application._launcher._get_application_path')
    def test_launch_call_to_launch_application_process(self, _, __):
        """Test that NormalApplicationLauncher.launch calls
        launch_application_process with the return values of
        setup_environment."""
        launcher = NormalApplicationLauncher()
        with patch.object(launcher, '_launch_application_process') as lap:
            with patch.object(launcher, '_setup_environment') as se:
                token_a = self.getUniqueString()
                token_b = self.getUniqueString()
                token_c = self.getUniqueString()
                se.return_value = (token_a, [token_b, token_c])
                launcher.launch('', arguments=['', ''])
                lap.assert_called_once_with(
                    token_a,
                    True,
                    None,
                    [token_b, token_c],
                )

    @patch('autopilot.application._launcher.'
           'get_proxy_object_for_existing_process')
    @patch('autopilot.application._launcher._get_application_path')
    def test_launch_gets_correct_proxy_object(self, _, gpofep):
        """Test that NormalApplicationLauncher.launch calls
        get_proxy_object_for_existing_process with the correct return values of
        other functions."""
        launcher = NormalApplicationLauncher()
        with patch.object(launcher, '_launch_application_process') as lap:
            with patch.object(launcher, '_setup_environment') as se:
                se.return_value = ('', [])
                launcher.launch('')
                gpofep.assert_called_once_with(process=lap.return_value,
                                               pid=lap.return_value.pid,
                                               emulator_base=None,
                                               dbus_bus='session')

    @patch('autopilot.application._launcher.'
           'get_proxy_object_for_existing_process')
    @patch('autopilot.application._launcher._get_application_path')
    def test_launch_sets_process_of_proxy_object(self, _, gpofep):
        """Test that NormalApplicationLauncher.launch returns the proxy object
        returned by get_proxy_object_for_existing_process."""
        launcher = NormalApplicationLauncher()
        with patch.object(launcher, '_launch_application_process') as lap:
            with patch.object(launcher, '_setup_environment') as se:
                se.return_value = ('', [])
                launcher.launch('')
                set_process = gpofep.return_value.set_process
                set_process.assert_called_once_with(lap.return_value)

    @patch('autopilot.application._launcher.'
           'get_proxy_object_for_existing_process')
    @patch('autopilot.application._launcher._get_application_path')
    def test_launch_returns_proxy_object(self, _, gpofep):
        """Test that NormalApplicationLauncher.launch returns the proxy object
        returned by get_proxy_object_for_existing_process."""
        launcher = NormalApplicationLauncher()
        with patch.object(launcher, '_launch_application_process'):
            with patch.object(launcher, '_setup_environment') as se:
                se.return_value = ('', [])
                result = launcher.launch('')
                self.assertEqual(result, gpofep.return_value)

    def test_launch_application_process(self):
        """The _launch_application_process method must return the process
        object, must add the _kill_process_and_attach_logs method to the
        fixture cleanups, and must call the launch_process function with the
        correct arguments.
        """
        launcher = NormalApplicationLauncher(self.addDetail)
        launcher.setUp()

        expected_process_return = self.getUniqueString()
        with patch.object(
            _l, 'launch_process', return_value=expected_process_return
        ) as patched_launch_process:
            process = launcher._launch_application_process(
                "/foo/bar", False, None, [])

            self.assertThat(process, Equals(expected_process_return))
            self.assertThat(
                [f[0] for f in launcher._cleanups._cleanups],
                Contains(launcher._kill_process_and_attach_logs)
            )
            patched_launch_process.assert_called_with(
                "/foo/bar",
                [],
                False,
                cwd=None
            )


class ClickApplicationLauncherTests(TestCase):

    def test_raises_exception_on_unknown_kwargs(self):
        self.assertThat(
            lambda: ClickApplicationLauncher(self.addDetail, unknown=True),
            raises(TypeError("__init__() got an unexpected keyword argument "
                             "'unknown'"))
        )

    @patch('autopilot.application._launcher._get_click_app_id')
    def test_handle_string(self, gcai):
        class FakeUpstartBase(_l.ApplicationLauncher):
            launch_call_args = []

            def launch(self, *args):
                FakeUpstartBase.launch_call_args = list(args)

        patcher = patch.object(
            _l.ClickApplicationLauncher,
            '__bases__',
            (FakeUpstartBase,)
        )
        token = self.getUniqueString()
        with patcher:
            # Prevent mock from trying to delete __bases__
            patcher.is_local = True
            launcher = self.useFixture(
                _l.ClickApplicationLauncher())
            launcher.launch('', '', token)
        self.assertEqual(
            FakeUpstartBase.launch_call_args,
            [gcai.return_value, [token]])

    @patch('autopilot.application._launcher._get_click_app_id')
    def test_handle_bytes(self, gcai):
        class FakeUpstartBase(_l.ApplicationLauncher):
            launch_call_args = []

            def launch(self, *args):
                FakeUpstartBase.launch_call_args = list(args)

        patcher = patch.object(
            _l.ClickApplicationLauncher,
            '__bases__',
            (FakeUpstartBase,)
        )
        token = self.getUniqueString()
        with patcher:
            # Prevent mock from trying to delete __bases__
            patcher.is_local = True
            launcher = self.useFixture(
                _l.ClickApplicationLauncher())
            launcher.launch('', '', token.encode())
        self.assertEqual(
            FakeUpstartBase.launch_call_args,
            [gcai.return_value, [token]])

    @patch('autopilot.application._launcher._get_click_app_id')
    def test_handle_list(self, gcai):
        class FakeUpstartBase(_l.ApplicationLauncher):
            launch_call_args = []

            def launch(self, *args):
                FakeUpstartBase.launch_call_args = list(args)

        patcher = patch.object(
            _l.ClickApplicationLauncher,
            '__bases__',
            (FakeUpstartBase,)
        )
        token = self.getUniqueString()
        with patcher:
            # Prevent mock from trying to delete __bases__
            patcher.is_local = True
            launcher = self.useFixture(
                _l.ClickApplicationLauncher())
            launcher.launch('', '', [token])
        self.assertEqual(
            FakeUpstartBase.launch_call_args,
            [gcai.return_value, [token]])

    @patch('autopilot.application._launcher._get_click_app_id')
    def test_call_get_click_app_id(self, gcai):
        class FakeUpstartBase(_l.ApplicationLauncher):
            launch_call_args = []

            def launch(self, *args):
                FakeUpstartBase.launch_call_args = list(args)

        patcher = patch.object(
            _l.ClickApplicationLauncher,
            '__bases__',
            (FakeUpstartBase,)
        )
        token_a = self.getUniqueString()
        token_b = self.getUniqueString()
        with patcher:
            # Prevent mock from trying to delete __bases__
            patcher.is_local = True
            launcher = self.useFixture(
                _l.ClickApplicationLauncher())
            launcher.launch(token_a, token_b)
        gcai.assert_called_once_with(token_a, token_b)

    @patch('autopilot.application._launcher._get_click_app_id')
    def test_call_upstart_launch(self, gcai):
        class FakeUpstartBase(_l.ApplicationLauncher):
            launch_call_args = []

            def launch(self, *args):
                FakeUpstartBase.launch_call_args = list(args)

        patcher = patch.object(
            _l.ClickApplicationLauncher,
            '__bases__',
            (FakeUpstartBase,)
        )
        with patcher:
            # Prevent mock from trying to delete __bases__
            patcher.is_local = True
            launcher = self.useFixture(
                _l.ClickApplicationLauncher())
            launcher.launch('', '')
            self.assertEqual(launcher.launch_call_args,
                             [gcai.return_value, []])


class ClickFunctionTests(TestCase):

    def test_get_click_app_id_raises_runtimeerror_on_empty_manifest(self):
        """_get_click_app_id must raise a RuntimeError if the requested
        package id is not found in the click manifest.

        """
        with patch.object(_l, '_get_click_manifest', return_value=[]):
            self.assertThat(
                lambda: _get_click_app_id("com.autopilot.testing"),
                raises(
                    RuntimeError(
                        "Unable to find package 'com.autopilot.testing' in "
                        "the click manifest."
                    )
                )
            )

    def test_get_click_app_id_raises_runtimeerror_on_missing_package(self):
        with patch.object(_l, '_get_click_manifest') as cm:
            cm.return_value = [
                {
                    'name': 'com.not.expected.name',
                    'hooks': {'bar': {}}, 'version': '1.0'
                }
            ]

            self.assertThat(
                lambda: _get_click_app_id("com.autopilot.testing"),
                raises(
                    RuntimeError(
                        "Unable to find package 'com.autopilot.testing' in "
                        "the click manifest."
                    )
                )
            )

    def test_get_click_app_id_raises_runtimeerror_on_wrong_app(self):
        """get_click_app_id must raise a RuntimeError if the requested
        application is not found within the click package.

        """
        with patch.object(_l, '_get_click_manifest') as cm:
            cm.return_value = [{'name': 'com.autopilot.testing', 'hooks': {}}]

            self.assertThat(
                lambda: _get_click_app_id("com.autopilot.testing", "bar"),
                raises(
                    RuntimeError(
                        "Application 'bar' is not present within the click "
                        "package 'com.autopilot.testing'."
                    )
                )
            )

    def test_get_click_app_id_returns_id(self):
        with patch.object(_l, '_get_click_manifest') as cm:
            cm.return_value = [
                {
                    'name': 'com.autopilot.testing',
                    'hooks': {'bar': {}}, 'version': '1.0'
                }
            ]

            self.assertThat(
                _get_click_app_id("com.autopilot.testing", "bar"),
                Equals("com.autopilot.testing_bar_1.0")
            )

    def test_get_click_app_id_returns_id_without_appid_passed(self):
        with patch.object(_l, '_get_click_manifest') as cm:
            cm.return_value = [
                {
                    'name': 'com.autopilot.testing',
                    'hooks': {'bar': {}}, 'version': '1.0'
                }
            ]

            self.assertThat(
                _get_click_app_id("com.autopilot.testing"),
                Equals("com.autopilot.testing_bar_1.0")
            )


class UpstartApplicationLauncherTests(TestCase):

    def test_can_construct_UpstartApplicationLauncher(self):
        UpstartApplicationLauncher(self.addDetail)

    def test_raises_exception_on_unknown_kwargs(self):
        self.assertThat(
            lambda: UpstartApplicationLauncher(self.addDetail, unknown=True),
            raises(TypeError("__init__() got an unexpected keyword argument "
                             "'unknown'"))
        )

    def test_on_failed_only_sets_status_on_correct_app_id(self):
        state = {
            'expected_app_id': 'gedit',
        }

        UpstartApplicationLauncher._on_failed('some_game', None, state)

        self.assertThat(state, Not(Contains('status')))

    def assertFunctionSetsCorrectStateAndQuits(self, observer, expected_state):
        """Assert that the observer observer sets the correct state id.

        :param observer: The observer callable you want to test.
        :param expected_state: The state id the observer callable must set.

        """
        expected_app_id = self.getUniqueString()
        state = {
            'expected_app_id': expected_app_id,
            'loop': Mock()
        }

        if observer == UpstartApplicationLauncher._on_failed:
            observer(expected_app_id, None, state)
        elif observer == UpstartApplicationLauncher._on_started or \
                observer == UpstartApplicationLauncher._on_stopped:
            observer(expected_app_id, state)
        else:
            observer(state)

        self.assertThat(
            state['status'],
            Equals(expected_state)
        )
        state['loop'].quit.assert_called_once_with()

    def test_on_failed_sets_status_with_correct_app_id(self):
        self.assertFunctionSetsCorrectStateAndQuits(
            UpstartApplicationLauncher._on_failed,
            UpstartApplicationLauncher.Failed
        )

    def test_on_started_sets_status_with_correct_app_id(self):
        self.assertFunctionSetsCorrectStateAndQuits(
            UpstartApplicationLauncher._on_started,
            UpstartApplicationLauncher.Started
        )

    def test_on_timeout_sets_status_and_exits_loop(self):
        self.assertFunctionSetsCorrectStateAndQuits(
            UpstartApplicationLauncher._on_timeout,
            UpstartApplicationLauncher.Timeout
        )

    def test_on_started_only_sets_status_on_correct_app_id(self):
        state = {
            'expected_app_id': 'gedit',
        }

        UpstartApplicationLauncher._on_started('some_game', state)

        self.assertThat(state, Not(Contains('status')))

    def test_on_stopped_only_sets_status_on_correct_app_id(self):
        state = {
            'expected_app_id': 'gedit',
        }

        UpstartApplicationLauncher._on_stopped('some_game', state)
        self.assertThat(state, Not(Contains('status')))

    def test_on_stopped_sets_status_and_exits_loop(self):
        self.assertFunctionSetsCorrectStateAndQuits(
            UpstartApplicationLauncher._on_stopped,
            UpstartApplicationLauncher.Stopped
        )

    def test_get_pid_calls_upstart_module(self):
        expected_return = self.getUniqueInteger()
        with patch.object(_l, 'UbuntuAppLaunch') as mock_ual:
            mock_ual.get_primary_pid.return_value = expected_return
            observed = UpstartApplicationLauncher._get_pid_for_launched_app(
                'gedit'
            )

            mock_ual.get_primary_pid.assert_called_once_with('gedit')
            self.assertThat(expected_return, Equals(observed))

    def test_launch_app_calls_upstart_module(self):
        with patch.object(_l, 'UbuntuAppLaunch') as mock_ual:
            UpstartApplicationLauncher._launch_app(
                'gedit',
                ['some', 'uris']
            )

            mock_ual.start_application_test.assert_called_once_with(
                'gedit',
                ['some', 'uris']
            )

    def test_check_error_raises_RuntimeError_on_timeout(self):
        fn = lambda: UpstartApplicationLauncher._check_status_error(
            UpstartApplicationLauncher.Timeout
        )
        self.assertThat(
            fn,
            raises(
                RuntimeError(
                    "Timed out while waiting for application to launch"
                )
            )
        )

    def test_check_error_raises_RuntimeError_on_failure(self):
        fn = lambda: UpstartApplicationLauncher._check_status_error(
            UpstartApplicationLauncher.Failed
        )
        self.assertThat(
            fn,
            raises(
                RuntimeError(
                    "Application Launch Failed"
                )
            )
        )

    def test_check_error_raises_RuntimeError_with_extra_message(self):
        fn = lambda: UpstartApplicationLauncher._check_status_error(
            UpstartApplicationLauncher.Failed,
            "extra message"
        )
        self.assertThat(
            fn,
            raises(
                RuntimeError(
                    "Application Launch Failed: extra message"
                )
            )
        )

    def test_check_error_does_nothing_on_None(self):
        UpstartApplicationLauncher._check_status_error(None)

    def test_get_loop_returns_glib_mainloop_instance(self):
        loop = UpstartApplicationLauncher._get_glib_loop()
        self.assertThat(loop, IsInstance(GLib.MainLoop))

    @patch('autopilot.application._launcher.UbuntuAppLaunch')
    @patch('autopilot.application._launcher.'
           'get_proxy_object_for_existing_process')
    def test_handle_string(self, gpofep, ual):
        launcher = UpstartApplicationLauncher()
        token_a = self.getUniqueString()
        token_b = self.getUniqueString()
        with patch.object(launcher, '_launch_app') as la:
            with patch.object(launcher, '_get_pid_for_launched_app'):
                with patch.object(launcher, '_get_glib_loop'):
                    launcher.launch(token_a, token_b)
                    la.assert_called_once_with(token_a, [token_b])

    @patch('autopilot.application._launcher.UbuntuAppLaunch')
    @patch('autopilot.application._launcher.'
           'get_proxy_object_for_existing_process')
    def test_handle_bytes(self, gpofep, ual):
        launcher = UpstartApplicationLauncher()
        token_a = self.getUniqueString()
        token_b = self.getUniqueString()
        with patch.object(launcher, '_launch_app') as la:
            with patch.object(launcher, '_get_pid_for_launched_app'):
                with patch.object(launcher, '_get_glib_loop'):
                    launcher.launch(token_a, token_b.encode())
                    la.assert_called_once_with(token_a, [token_b])

    @patch('autopilot.application._launcher.UbuntuAppLaunch')
    @patch('autopilot.application._launcher.'
           'get_proxy_object_for_existing_process')
    def test_handle_list(self, gpofep, ual):
        launcher = UpstartApplicationLauncher()
        token_a = self.getUniqueString()
        token_b = self.getUniqueString()
        with patch.object(launcher, '_launch_app') as la:
            with patch.object(launcher, '_get_pid_for_launched_app'):
                with patch.object(launcher, '_get_glib_loop'):
                    launcher.launch(token_a, [token_b])
                    la.assert_called_once_with(token_a, [token_b])

    @patch('autopilot.application._launcher.UbuntuAppLaunch')
    @patch('autopilot.application._launcher.'
           'get_proxy_object_for_existing_process')
    def test_calls_get_pid(self, gpofep, ual):
        launcher = UpstartApplicationLauncher()
        token = self.getUniqueString()
        with patch.object(launcher, '_launch_app'):
            with patch.object(launcher, '_get_pid_for_launched_app') as gp:
                with patch.object(launcher, '_get_glib_loop'):
                    launcher.launch(token)
                    gp.assert_called_once_with(token)

    @patch('autopilot.application._launcher.UbuntuAppLaunch')
    @patch('autopilot.application._launcher.'
           'get_proxy_object_for_existing_process')
    def test_gets_correct_proxy_object(self, gpofep, ual):
        launcher = UpstartApplicationLauncher()
        with patch.object(launcher, '_launch_app'):
            with patch.object(launcher, '_get_pid_for_launched_app') as gp:
                with patch.object(launcher, '_get_glib_loop'):
                    launcher.launch('')
                    gpofep.assert_called_once_with(pid=gp.return_value,
                                                   emulator_base=None,
                                                   dbus_bus='session')

    @patch('autopilot.application._launcher.UbuntuAppLaunch')
    @patch('autopilot.application._launcher.'
           'get_proxy_object_for_existing_process')
    def test_returns_proxy_object(self, gpofep, ual):
        launcher = UpstartApplicationLauncher()
        with patch.object(launcher, '_launch_app'):
            with patch.object(launcher, '_get_pid_for_launched_app'):
                with patch.object(launcher, '_get_glib_loop'):
                    result = launcher.launch('')
                    self.assertEqual(result, gpofep.return_value)

    @patch('autopilot.application._launcher.UbuntuAppLaunch')
    @patch('autopilot.application._launcher.'
           'get_proxy_object_for_existing_process')
    def test_calls_get_glib_loop(self, gpofep, ual):
        launcher = UpstartApplicationLauncher()
        with patch.object(launcher, '_launch_app'):
            with patch.object(launcher, '_get_pid_for_launched_app'):
                with patch.object(launcher, '_get_glib_loop') as ggl:
                    launcher.launch('')
                    ggl.assert_called_once_with()

    def assertFailedObserverSetsExtraMessage(self, fail_type, expected_msg):
        """Assert that the on_failed observer must set the expected message
        for a particular failure_type."""
        expected_app_id = self.getUniqueString()
        state = {
            'expected_app_id': expected_app_id,
            'loop': Mock()
        }
        UpstartApplicationLauncher._on_failed(
            expected_app_id,
            fail_type,
            state
        )
        self.assertEqual(expected_msg, state['message'])

    def test_on_failed_sets_message_for_app_crash(self):
        self.assertFailedObserverSetsExtraMessage(
            _l.UbuntuAppLaunch.AppFailed.CRASH,
            'Application crashed.'
        )

    def test_on_failed_sets_message_for_app_start_failure(self):
        self.assertFailedObserverSetsExtraMessage(
            _l.UbuntuAppLaunch.AppFailed.START_FAILURE,
            'Application failed to start.'
        )

    def test_add_application_cleanups_adds_both_cleanup_actions(self):
        token = self.getUniqueString()
        state = {
            'status': UpstartApplicationLauncher.Started,
            'expected_app_id': token,
        }
        launcher = UpstartApplicationLauncher(Mock())
        launcher.setUp()
        launcher._maybe_add_application_cleanups(state)
        self.assertThat(
            launcher._cleanups._cleanups,
            Contains(
                (launcher._attach_application_log, (token,), {})
            )
        )
        self.assertThat(
            launcher._cleanups._cleanups,
            Contains(
                (launcher._stop_application, (token,), {})
            )
        )

    def test_add_application_cleanups_does_nothing_when_app_timedout(self):
        state = {
            'status': UpstartApplicationLauncher.Timeout,
        }
        launcher = UpstartApplicationLauncher(Mock())
        launcher.setUp()
        launcher._maybe_add_application_cleanups(state)
        self.assertThat(launcher._cleanups._cleanups, HasLength(0))

    def test_add_application_cleanups_does_nothing_when_app_failed(self):
        state = {
            'status': UpstartApplicationLauncher.Failed,
        }
        launcher = UpstartApplicationLauncher(Mock())
        launcher.setUp()
        launcher._maybe_add_application_cleanups(state)
        self.assertThat(launcher._cleanups._cleanups, HasLength(0))

    def test_attach_application_log_does_nothing_wth_no_log_specified(self):
        app_id = self.getUniqueString()
        case_addDetail = Mock()
        launcher = UpstartApplicationLauncher(case_addDetail)
        j = MagicMock(spec=_l.journal.Reader)
        with patch.object(_l.journal, 'Reader', return_value=j):
            launcher._attach_application_log(app_id)
            expected = launcher._get_user_unit_match(app_id)
            j.add_match.assert_called_once_with(_SYSTEMD_USER_UNIT=expected)
            self.assertEqual(0, case_addDetail.call_count)

    def test_attach_application_log_attaches_log(self):
        token = self.getUniqueString()
        case_addDetail = Mock()
        launcher = UpstartApplicationLauncher(case_addDetail)
        app_id = self.getUniqueString()
        j = MagicMock(spec=_l.journal.Reader)
        j.__iter__ = lambda x: iter([token])
        with patch.object(_l.journal, 'Reader', return_value=j):
            launcher._attach_application_log(app_id)

            self.assertEqual(1, case_addDetail.call_count)
            content_name, content_obj = case_addDetail.call_args[0]
            self.assertEqual(
                "Application Log (%s)" % app_id,
                content_name
            )
            self.assertThat(content_obj.as_text(), Contains(token))

    def test_stop_adds_app_stopped_observer(self):
        mock_add_detail = Mock()
        mock_glib_loop = Mock()
        patch_get_loop = patch.object(
            UpstartApplicationLauncher,
            '_get_glib_loop',
            new=mock_glib_loop,
        )
        mock_UAL = Mock()
        patch_UAL = patch.object(_l, 'UbuntuAppLaunch', new=mock_UAL)
        launcher = UpstartApplicationLauncher(mock_add_detail)
        app_id = self.getUniqueString()
        with ExitStack() as patches:
            patches.enter_context(patch_get_loop)
            patches.enter_context(patch_UAL)

            launcher._stop_application(app_id)
            call_args = mock_UAL.observer_add_app_stop.call_args[0]
            self.assertThat(
                call_args[0],
                Equals(UpstartApplicationLauncher._on_stopped)
            )
            self.assertThat(call_args[1]['expected_app_id'], Equals(app_id))

    def test_stop_calls_libUAL_stop_function(self):
        mock_add_detail = Mock()
        mock_glib_loop = Mock()
        patch_get_loop = patch.object(
            UpstartApplicationLauncher,
            '_get_glib_loop',
            new=mock_glib_loop,
        )
        mock_UAL = Mock()
        patch_UAL = patch.object(_l, 'UbuntuAppLaunch', new=mock_UAL)
        launcher = UpstartApplicationLauncher(mock_add_detail)
        app_id = self.getUniqueString()
        with ExitStack() as patches:
            patches.enter_context(patch_get_loop)
            patches.enter_context(patch_UAL)

            launcher._stop_application(app_id)
            mock_UAL.stop_application.assert_called_once_with(app_id)

    def test_stop_logs_error_on_timeout(self):
        mock_add_detail = Mock()
        mock_glib_loop = Mock()
        patch_get_loop = patch.object(
            UpstartApplicationLauncher,
            '_get_glib_loop',
            new=mock_glib_loop,
        )
        mock_UAL = Mock()

        # we replace the add_observer function with one that can set the
        # tiemout state, so we can ibject the timeout condition within the
        # glib loop. This is ugly, but necessary.
        def fake_add_observer(fn, state):
            state['status'] = UpstartApplicationLauncher.Timeout
        mock_UAL.observer_add_app_stop = fake_add_observer
        patch_UAL = patch.object(_l, 'UbuntuAppLaunch', new=mock_UAL)
        launcher = UpstartApplicationLauncher(mock_add_detail)
        app_id = self.getUniqueString()
        mock_logger = Mock()
        patch_logger = patch.object(_l, '_logger', new=mock_logger)
        with ExitStack() as patches:
            patches.enter_context(patch_get_loop)
            patches.enter_context(patch_UAL)
            patches.enter_context(patch_logger)

            launcher._stop_application(app_id)

            mock_logger.error.assert_called_once_with(
                "Timed out waiting for Application with app_id '%s' to stop.",
                app_id
            )


class ApplicationLauncherInternalTests(TestCase):

    def test_get_app_env_from_string_hint_returns_qt_env(self):
        self.assertThat(
            _get_app_env_from_string_hint('QT'),
            IsInstance(QtApplicationEnvironment)
        )

    def test_get_app_env_from_string_hint_returns_gtk_env(self):
        self.assertThat(
            _get_app_env_from_string_hint('GTK'),
            IsInstance(GtkApplicationEnvironment)
        )

    def test_get_app_env_from_string_hint_raises_on_unknown(self):
        self.assertThat(
            lambda: _get_app_env_from_string_hint('FOO'),
            raises(ValueError("Unknown hint string: FOO"))
        )

    def test_get_application_environment_uses_app_type_argument(self):
        with patch.object(_l, '_get_app_env_from_string_hint') as from_hint:
            _get_application_environment(app_type="app_type")
            from_hint.assert_called_with("app_type")

    def test_get_application_environment_uses_app_path_argument(self):
        with patch.object(
            _l, 'get_application_launcher_wrapper'
        ) as patched_wrapper:
            _get_application_environment(app_path="app_path")
            patched_wrapper.assert_called_with("app_path")

    def test_get_application_environment_raises_runtime_with_no_args(self):
        self.assertThat(
            lambda: _get_application_environment(),
            raises(
                ValueError(
                    "Must specify either app_type or app_path."
                )
            )
        )

    def test_get_application_environment_raises_on_app_type_error(self):
        unknown_app_type = self.getUniqueString()
        with patch.object(
            _l, '_get_app_env_from_string_hint',
            side_effect=ValueError()
        ):
            self.assertThat(
                lambda: _get_application_environment(
                    app_type=unknown_app_type
                ),
                raises(RuntimeError(
                    "Autopilot could not determine the correct introspection "
                    "type to use. You can specify this by providing app_type."
                ))
            )

    def test_get_application_environment_raises_on_app_path_error(self):
        unknown_app_path = self.getUniqueString()
        with patch.object(
            _l, 'get_application_launcher_wrapper', side_effect=RuntimeError()
        ):
            self.assertThat(
                lambda: _get_application_environment(
                    app_path=unknown_app_path
                ),
                raises(RuntimeError(
                    "Autopilot could not determine the correct introspection "
                    "type to use. You can specify this by providing app_type."
                ))
            )

    @patch.object(_l.os, 'killpg')
    def test_attempt_kill_pid_logs_if_process_already_exited(self, killpg):
        killpg.side_effect = OSError()

        with patch.object(_l, '_logger') as patched_log:
            _attempt_kill_pid(0)
            patched_log.info.assert_called_with(
                "Appears process has already exited."
            )

    @patch.object(_l, '_attempt_kill_pid')
    def test_kill_process_succeeds(self, patched_kill_pid):
        mock_process = Mock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("", "",)

        with patch.object(
            _l, '_is_process_running', return_value=False
        ):
            self.assertThat(_kill_process(mock_process), Equals(("", "", 0)))

    @patch.object(_l, '_attempt_kill_pid')
    def test_kill_process_tries_again(self, patched_kill_pid):
        with sleep.mocked():
            mock_process = Mock()
            mock_process.pid = 123
            mock_process.communicate.return_value = ("", "",)

            with patch.object(
                _l, '_is_process_running', return_value=True
            ) as proc_running:
                _kill_process(mock_process)

                self.assertThat(proc_running.call_count, GreaterThan(1))
                self.assertThat(patched_kill_pid.call_count, Equals(2))
                patched_kill_pid.assert_called_with(123, signal.SIGKILL)

    @patch.object(_l.subprocess, 'Popen')
    def test_launch_process_uses_arguments(self, popen):
        launch_process("testapp", ["arg1", "arg2"])

        self.assertThat(
            popen.call_args_list[0][0],
            Contains(['testapp', 'arg1', 'arg2'])
        )

    @patch.object(_l.subprocess, 'Popen')
    def test_launch_process_default_capture_is_false(self, popen):
        launch_process("testapp", [])

        self.assertThat(
            popen.call_args[1]['stderr'],
            Equals(None)
        )
        self.assertThat(
            popen.call_args[1]['stdout'],
            Equals(None)
        )

    @patch.object(_l.subprocess, 'Popen')
    def test_launch_process_can_set_capture_output(self, popen):
        launch_process("testapp", [], capture_output=True)

        self.assertThat(
            popen.call_args[1]['stderr'],
            Not(Equals(None))
        )
        self.assertThat(
            popen.call_args[1]['stdout'],
            Not(Equals(None))
        )

    @patch.object(_l.subprocess, 'check_output')
    def test_get_application_launcher_wrapper_finds_qt(self, check_output):
        check_output.return_value = "LIBQTCORE"
        self.assertThat(
            get_application_launcher_wrapper("/fake/app/path"),
            IsInstance(QtApplicationEnvironment)
        )

    @patch.object(_l.subprocess, 'check_output')
    def test_get_application_launcher_wrapper_finds_gtk(self, check_output):
        check_output.return_value = "LIBGTK"
        self.assertThat(
            get_application_launcher_wrapper("/fake/app/path"),
            IsInstance(GtkApplicationEnvironment)
        )

    @patch.object(_l.subprocess, 'check_output')
    def test_get_application_path_returns_stripped_path(self, check_output):
        check_output.return_value = "/foo/bar   "

        self.assertThat(_get_application_path("bar"), Equals('/foo/bar'))
        check_output.assert_called_with(
            ['which', 'bar'], universal_newlines=True
        )

    def test_get_application_path_raises_when_cant_find_app(self):
        test_path = self.getUniqueString()
        expected_error = "Unable to find path for application {app}: Command"\
                         " '['which', '{app}']' returned non-zero exit "\
                         "status 1".format(app=test_path)
        with patch.object(_l.subprocess, 'check_output') as check_output:
            check_output.side_effect = subprocess.CalledProcessError(
                1,
                ['which', test_path]
            )

            self.assertThat(
                lambda: _get_application_path(test_path),
                raises(ValueError(expected_error))
            )

    def test_get_application_launcher_wrapper_raises_runtimeerror(self):
        test_path = self.getUniqueString()
        expected_error = "Command '['ldd', '%s']' returned non-zero exit"\
                         " status 1" % test_path
        with patch.object(_l.subprocess, 'check_output') as check_output:
            check_output.side_effect = subprocess.CalledProcessError(
                1,
                ['ldd', test_path]
            )

            self.assertThat(
                lambda: get_application_launcher_wrapper(test_path),
                raises(RuntimeError(expected_error))
            )

    def test_get_application_launcher_wrapper_returns_none_for_unknown(self):
        with patch.object(_l.subprocess, 'check_output') as check_output:
            check_output.return_value = self.getUniqueString()
            self.assertThat(
                get_application_launcher_wrapper(""), Equals(None)
            )

    def test_get_click_manifest_returns_python_object(self):
        example_manifest = """
            [{
                "description": "Calculator application",
                "framework": "ubuntu-sdk-13.10",
                "hooks": {
                    "calculator": {
                        "apparmor": "apparmor/calculator.json",
                        "desktop": "ubuntu-calculator-app.desktop"
                    }
                },
                "icon": "calculator64.png"
            }]
        """
        with patch.object(_l.subprocess, 'check_output') as check_output:
            check_output.return_value = example_manifest
            self.assertThat(_get_click_manifest(), IsInstance(list))

    @patch.object(_l.psutil, 'pid_exists')
    def test_is_process_running_checks_with_pid(self, pid_exists):
        pid_exists.return_value = True
        self.assertThat(_is_process_running(123), Equals(True))
        pid_exists.assert_called_with(123)
