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

from argparse import Namespace
from unittest.mock import Mock, patch
import logging
import os.path
from shutil import rmtree
import subprocess
import tempfile
from testtools import TestCase, skipUnless
from testtools.matchers import (
    Contains,
    DirExists,
    Equals,
    FileExists,
    IsInstance,
    Not,
    raises,
    Raises,
    StartsWith,
)

from contextlib import ExitStack
from io import StringIO

from autopilot import get_version_string, have_vis, run, _video


class RunUtilityFunctionTests(TestCase):

    @patch('autopilot.run.autopilot.globals.set_debug_profile_fixture')
    def test_sets_when_correct_profile_found(self, patched_set_fixture):
        mock_profile = Mock()
        mock_profile.name = "verbose"
        parsed_args = Namespace(debug_profile="verbose")

        with patch.object(
                run, 'get_all_debug_profiles', lambda: {mock_profile}):

            run._configure_debug_profile(parsed_args)
            patched_set_fixture.assert_called_once_with(mock_profile)

    @patch('autopilot.run.autopilot.globals.set_debug_profile_fixture')
    def test_does_nothing_when_no_profile_found(self, patched_set_fixture):
        mock_profile = Mock()
        mock_profile.name = "verbose"
        parsed_args = Namespace(debug_profile="normal")

        with patch.object(
                run, 'get_all_debug_profiles', lambda: {mock_profile}):

            run._configure_debug_profile(parsed_args)
        self.assertFalse(patched_set_fixture.called)

    @patch('autopilot.run.autopilot.globals')
    def test_timeout_values_set_with_long_profile(self, patched_globals):
        args = Namespace(timeout_profile='long')
        run._configure_timeout_profile(args)

        patched_globals.set_default_timeout_period.assert_called_once_with(
            20.0
        )
        patched_globals.set_long_timeout_period.assert_called_once_with(30.0)

    @patch('autopilot.run.autopilot.globals')
    def test_timeout_value_not_set_with_normal_profile(self, patched_globals):
        args = Namespace(timeout_profile='normal')
        run._configure_timeout_profile(args)

        self.assertFalse(patched_globals.set_default_timeout_period.called)
        self.assertFalse(patched_globals.set_long_timeout_period.called)

    @patch('autopilot.run.autopilot.globals')
    def test_test_tiemout_value_set_in_globals(self, patched_globals):
        args = Namespace(test_timeout=42)
        run._configure_test_timeout(args)

        patched_globals.set_test_timeout.assert_called_once_with(42)

    @patch.object(_video, '_have_video_recording_facilities', new=lambda: True)
    def test_correct_video_record_fixture_is_called_with_record_on(self):
        args = Namespace(record_directory='', record=True)
        _video.configure_video_recording(args)
        FixtureClass = _video.get_video_recording_fixture()
        fixture = FixtureClass(args)

        self.assertEqual(fixture.__class__.__name__, 'RMDVideoLogFixture')

    @patch.object(_video, '_have_video_recording_facilities', new=lambda: True)
    def test_correct_video_record_fixture_is_called_with_record_off(self):
        args = Namespace(record_directory='', record=False)
        _video.configure_video_recording(args)
        FixtureClass = _video.get_video_recording_fixture()
        fixture = FixtureClass(args)

        self.assertEqual(fixture.__class__.__name__, 'DoNothingFixture')

    @patch.object(_video, '_have_video_recording_facilities', new=lambda: True)
    def test_configure_video_record_directory_implies_record(self):
        token = self.getUniqueString()
        args = Namespace(record_directory=token, record=False)
        _video.configure_video_recording(args)
        FixtureClass = _video.get_video_recording_fixture()
        fixture = FixtureClass(args)

        self.assertEqual(fixture.__class__.__name__, 'RMDVideoLogFixture')

    @patch.object(_video, '_have_video_recording_facilities', new=lambda: True)
    def test_configure_video_recording_sets_default_dir(self):
        args = Namespace(record_directory='', record=True)
        _video.configure_video_recording(args)
        PartialFixture = _video.get_video_recording_fixture()
        partial_fixture = PartialFixture(None)

        self.assertEqual(partial_fixture.recording_directory, '/tmp/autopilot')

    @patch.object(
        _video,
        '_have_video_recording_facilities',
        new=lambda: False
    )
    def test_configure_video_recording_raises_RuntimeError(self):
        args = Namespace(record_directory='', record=True)
        self.assertThat(
            lambda: _video.configure_video_recording(args),
            raises(
                RuntimeError(
                    "The application 'recordmydesktop' needs to be installed "
                    "to record failing jobs."
                )
            )
        )

    def test_video_record_check_calls_subprocess_with_correct_args(self):
        with patch.object(_video.subprocess, 'call') as patched_call:
            _video._have_video_recording_facilities()
            patched_call.assert_called_once_with(
                ['which', 'recordmydesktop'],
                stdout=run.subprocess.PIPE
            )

    def test_video_record_check_returns_true_on_zero_return_code(self):
        with patch.object(_video.subprocess, 'call') as patched_call:
            patched_call.return_value = 0
            self.assertTrue(_video._have_video_recording_facilities())

    def test_video_record_check_returns_false_on_nonzero_return_code(self):
        with patch.object(_video.subprocess, 'call') as patched_call:
            patched_call.return_value = 1
            self.assertFalse(_video._have_video_recording_facilities())

    def test_run_with_profiling_creates_profile_data_file(self):
        output_path = tempfile.mktemp()
        self.addCleanup(os.unlink, output_path)

        def empty_callable():
            pass
        run._run_with_profiling(empty_callable, output_path)
        self.assertThat(output_path, FileExists())

    def test_run_with_profiling_runs_callable(self):
        output_path = tempfile.mktemp()
        self.addCleanup(os.unlink, output_path)
        empty_callable = Mock()
        run._run_with_profiling(empty_callable, output_path)
        empty_callable.assert_called_once_with()


class TestRunLaunchApp(TestCase):
    @patch.object(run, 'launch_process')
    def test_launch_app_launches_app_with_arguments(self, patched_launch_proc):
        app_name = self.getUniqueString()
        app_arguments = self.getUniqueString()
        fake_args = Namespace(
            mode='launch',
            application=[app_name, app_arguments],
            interface=None
        )

        with patch.object(
            run,
            '_prepare_application_for_launch',
            return_value=(app_name, app_arguments)
        ):
            program = run.TestProgram(fake_args)
            program.run()
            patched_launch_proc.assert_called_once_with(
                app_name,
                app_arguments,
                capture_output=False
            )

    def test_launch_app_exits_using_print_message_and_exit_error(self):
        app_name = self.getUniqueString()
        app_arguments = self.getUniqueString()
        error_message = "Cannot find application 'blah'"
        fake_args = Namespace(
            mode='launch',
            application=[app_name, app_arguments],
            interface=None
        )

        with patch.object(
            run,
            '_prepare_application_for_launch',
                side_effect=RuntimeError(error_message)
        ):
            with patch.object(
                run, '_print_message_and_exit_error'
            ) as print_and_exit:
                run.TestProgram(fake_args).run()
                print_and_exit.assert_called_once_with(
                    "Error: %s" % error_message
                )

    @patch.object(run, 'launch_process')
    def test_launch_app_exits_with_message_on_failure(self, patched_launch_proc):  # NOQA
        app_name = self.getUniqueString()
        app_arguments = self.getUniqueString()
        fake_args = Namespace(
            mode='launch',
            application=[app_name, app_arguments],
            interface=None
        )

        with patch.object(
            run,
            '_prepare_application_for_launch',
            return_value=(app_name, app_arguments)
        ):
            with patch('sys.stdout', new=StringIO()) as stdout:
                patched_launch_proc.side_effect = RuntimeError(
                    "Failure Message"
                )
                program = run.TestProgram(fake_args)
                self.assertThat(lambda: program.run(), raises(SystemExit(1)))
                self.assertThat(
                    stdout.getvalue(),
                    Contains("Error: Failure Message")
                )

    @skipUnless(have_vis(), "Requires vis module.")
    @patch('autopilot.vis.vis_main')
    def test_passes_testability_to_vis_main(self, patched_vis_main):
        args = Namespace(
            mode='vis',
            testability=True,
            enable_profile=False,
        )
        program = run.TestProgram(args)
        program.run()

        patched_vis_main.assert_called_once_with(['-testability'])

    @skipUnless(have_vis(), "Requires vis module.")
    @patch('autopilot.vis.vis_main')
    def test_passes_empty_list_without_testability_set(self, patched_vis_main):
        args = Namespace(
            mode='vis',
            testability=False,
            enable_profile=False,
        )
        program = run.TestProgram(args)
        program.run()

        patched_vis_main.assert_called_once_with([])


class TestRunLaunchAppHelpers(TestCase):
    """Tests for the 'autopilot launch' command"""

    def test_get_app_name_and_args_returns_app_name_passed_app_name(self):
        app_name = self.getUniqueString()
        launch_args = [app_name]

        self.assertThat(
            run._get_app_name_and_args(launch_args),
            Equals((app_name, []))
        )

    def test_get_app_name_and_args_returns_app_name_passed_arg_and_name(self):
        app_name = self.getUniqueString()
        app_arg = [self.getUniqueString()]
        launch_args = [app_name] + app_arg

        self.assertThat(
            run._get_app_name_and_args(launch_args),
            Equals((app_name, app_arg))
        )

    def test_get_app_name_and_args_returns_app_name_passed_args_and_name(self):
        app_name = self.getUniqueString()
        app_args = [self.getUniqueString(), self.getUniqueString()]

        launch_args = [app_name] + app_args

        self.assertThat(
            run._get_app_name_and_args(launch_args),
            Equals((app_name, app_args))
        )

    def test_application_name_is_full_path_True_when_is_abs_path(self):
        with patch.object(run.os.path, 'isabs', return_value=True):
            self.assertTrue(run._application_name_is_full_path(""))

    def test_application_name_is_full_path_True_when_path_exists(self):
        with patch.object(run.os.path, 'exists', return_value=True):
            self.assertTrue(run._application_name_is_full_path(""))

    def test_application_name_is_full_path_False_neither_abs_or_exists(self):
        with patch.object(run.os.path, 'exists', return_value=False):
            with patch.object(run.os.path, 'isabs', return_value=False):
                self.assertFalse(run._application_name_is_full_path(""))

    def test_get_applications_full_path_returns_same_when_full_path(self):
        app_name = self.getUniqueString()

        with patch.object(
            run,
            '_application_name_is_full_path',
            return_value=True
        ):
            self.assertThat(
                run._get_applications_full_path(app_name),
                Equals(app_name)
            )

    def test_get_applications_full_path_calls_which_command_on_app_name(self):
        app_name = self.getUniqueString()
        full_path = "/usr/bin/%s" % app_name
        with patch.object(
            run.subprocess,
            'check_output',
            return_value=full_path
        ):
            self.assertThat(
                run._get_applications_full_path(app_name),
                Equals(full_path)
            )

    def test_get_applications_full_path_raises_valueerror_when_not_found(self):
        app_name = self.getUniqueString()
        expected_error = "Cannot find application '%s'" % (app_name)

        with patch.object(
            run.subprocess,
            'check_output',
            side_effect=subprocess.CalledProcessError(1, "")
        ):
            self.assertThat(
                lambda: run._get_applications_full_path(app_name),
                raises(ValueError(expected_error))
            )

    def test_get_application_path_and_arguments_raises_for_unknown_app(self):
        app_name = self.getUniqueString()
        expected_error = "Cannot find application '{app_name}'".format(
            app_name=app_name
        )

        self.assertThat(
            lambda: run._get_application_path_and_arguments([app_name]),
            raises(RuntimeError(expected_error))
        )

    def test_get_application_path_and_arguments_returns_app_and_args(self):
        app_name = self.getUniqueString()

        with patch.object(
            run,
            '_get_applications_full_path',
            side_effect=lambda arg: arg
        ):
            self.assertThat(
                run._get_application_path_and_arguments([app_name]),
                Equals((app_name, []))
            )

    def test_get_application_launcher_env_attempts_auto_selection(self):
        interface = "Auto"
        app_path = self.getUniqueString()
        test_launcher_env = self.getUniqueString()

        with patch.object(
            run,
            '_try_determine_launcher_env_or_raise',
            return_value=test_launcher_env
        ) as get_launcher:
            self.assertThat(
                run._get_application_launcher_env(interface, app_path),
                Equals(test_launcher_env)
            )
            get_launcher.assert_called_once_with(app_path)

    def test_get_application_launcher_env_uses_string_hint_to_determine(self):
        interface = None
        app_path = self.getUniqueString()
        test_launcher_env = self.getUniqueString()

        with patch.object(
            run,
            '_get_app_env_from_string_hint',
            return_value=test_launcher_env
        ) as get_launcher:
            self.assertThat(
                run._get_application_launcher_env(interface, app_path),
                Equals(test_launcher_env)
            )
            get_launcher.assert_called_once_with(interface)

    def test_get_application_launcher_env_returns_None_on_failure(self):
        interface = None
        app_path = self.getUniqueString()

        with patch.object(
            run,
            '_get_app_env_from_string_hint',
            return_value=None
        ):
            self.assertThat(
                run._get_application_launcher_env(interface, app_path),
                Equals(None)
            )

    def test_try_determine_launcher_env_or_raise_raises_on_failure(self):
        app_name = self.getUniqueString()
        err_msg = self.getUniqueString()
        with patch.object(
            run,
            'get_application_launcher_wrapper',
            side_effect=RuntimeError(err_msg)
        ):
            self.assertThat(
                lambda: run._try_determine_launcher_env_or_raise(app_name),
                raises(
                    RuntimeError(
                        "Error detecting launcher: {err}\n"
                        "(Perhaps use the '-i' argument to specify an "
                        "interface.)"
                        .format(err=err_msg)
                    )
                )
            )

    def test_try_determine_launcher_env_or_raise_returns_launcher_wrapper_result(self):  # NOQA
        app_name = self.getUniqueString()
        launcher_env = self.getUniqueString()

        with patch.object(
            run,
            'get_application_launcher_wrapper',
            return_value=launcher_env
        ):
            self.assertThat(
                run._try_determine_launcher_env_or_raise(app_name),
                Equals(launcher_env)
            )

    def test_raise_if_launcher_is_none_raises_on_none(self):
        app_name = self.getUniqueString()

        self.assertThat(
            lambda: run._raise_if_launcher_is_none(None, app_name),
            raises(
                RuntimeError(
                    "Could not determine introspection type to use for "
                    "application '{app_name}'.\n"
                    "(Perhaps use the '-i' argument to specify an interface.)"
                    .format(app_name=app_name)
                )
            )
        )

    def test_raise_if_launcher_is_none_does_not_raise_on_none(self):
        launcher_env = self.getUniqueString()
        app_name = self.getUniqueString()

        run._raise_if_launcher_is_none(launcher_env, app_name)

    def test_prepare_launcher_environment_creates_launcher_env(self):
        interface = self.getUniqueString()
        app_name = self.getUniqueString()
        app_arguments = self.getUniqueString()

        with patch.object(
            run,
            '_get_application_launcher_env',
        ) as get_launcher:
            get_launcher.return_value.prepare_environment = lambda *args: args

            self.assertThat(
                run._prepare_launcher_environment(
                    interface,
                    app_name,
                    app_arguments
                ),
                Equals((app_name, app_arguments))
            )

    def test_prepare_launcher_environment_checks_launcher_isnt_None(self):
        interface = self.getUniqueString()
        app_name = self.getUniqueString()
        app_arguments = self.getUniqueString()

        with patch.object(
            run,
            '_get_application_launcher_env',
        ) as get_launcher:
            get_launcher.return_value.prepare_environment = lambda *args: args

            with patch.object(
                run,
                '_raise_if_launcher_is_none'
            ) as launcher_check:
                run._prepare_launcher_environment(
                    interface,
                    app_name,
                    app_arguments
                )
                launcher_check.assert_called_once_with(
                    get_launcher.return_value,
                    app_name
                )

    def test_print_message_and_exit_error_prints_message(self):
        err_msg = self.getUniqueString()
        with patch('sys.stdout', new=StringIO()) as stdout:
            try:
                run._print_message_and_exit_error(err_msg)
            except SystemExit:
                pass

            self.assertThat(stdout.getvalue(), Contains(err_msg))

    def test_print_message_and_exit_error_exits_non_zero(self):
        self.assertThat(
            lambda: run._print_message_and_exit_error(""),
            raises(SystemExit(1))
        )

    def test_prepare_application_for_launch_returns_prepared_details(self):
        interface = self.getUniqueString()
        application = self.getUniqueString()
        app_name = self.getUniqueString()
        app_arguments = self.getUniqueString()

        with ExitStack() as stack:
            stack.enter_context(
                patch.object(
                    run,
                    '_get_application_path_and_arguments',
                    return_value=(app_name, app_arguments)
                )
            )
            prepare_launcher = stack.enter_context(
                patch.object(
                    run,
                    '_prepare_launcher_environment',
                    return_value=(app_name, app_arguments)
                )
            )

            self.assertThat(
                run._prepare_application_for_launch(application, interface),
                Equals((app_name, app_arguments))
            )
            prepare_launcher.assert_called_once_with(
                interface,
                app_name,
                app_arguments
            )


class LoggingSetupTests(TestCase):

    verbose_level_none = 0
    verbose_level_v = 1
    verbose_level_vv = 2

    def test_run_logs_autopilot_version(self):
        with patch.object(run, 'log_autopilot_version') as log_version:
            fake_args = Namespace(mode=None)
            program = run.TestProgram(fake_args)
            program.run()

            log_version.assert_called_once_with()

    def test_log_autopilot_version_logs_current_version(self):
        current_version = get_version_string()
        with patch.object(run, 'get_root_logger') as fake_get_root_logger:
            run.log_autopilot_version()
            fake_get_root_logger.return_value.info.assert_called_once_with(
                current_version
            )

    def test_get_root_logger_returns_logging_instance(self):
        logger = run.get_root_logger()
        self.assertThat(logger, IsInstance(logging.RootLogger))

    def test_setup_logging_calls_get_root_logger(self):
        with patch.object(run, 'get_root_logger') as fake_get_root_logger:
            run.setup_logging(self.verbose_level_none)
            fake_get_root_logger.assert_called_once_with()

    def test_setup_logging_defaults_to_info_level(self):
        with patch.object(run, 'get_root_logger') as fake_get_logger:
            run.setup_logging(self.verbose_level_none)
            fake_get_logger.return_value.setLevel.assert_called_once_with(
                logging.INFO
            )

    def test_setup_logging_keeps_root_logging_level_at_info_for_v(self):
        with patch.object(run, 'get_root_logger') as fake_get_logger:
            run.setup_logging(self.verbose_level_v)
            fake_get_logger.return_value.setLevel.assert_called_once_with(
                logging.INFO
            )

    def test_setup_logging_sets_root_logging_level_to_debug_with_vv(self):
        with patch.object(run, 'get_root_logger') as fake_get_logger:
            run.setup_logging(self.verbose_level_vv)
            fake_get_logger.return_value.setLevel.assert_called_with(
                logging.DEBUG
            )

    @patch.object(run.autopilot.globals, 'set_log_verbose')
    def test_setup_logging_calls_set_log_verbose_for_v(self, patch_set_log):
        with patch.object(run, 'get_root_logger'):
            run.setup_logging(self.verbose_level_v)
            patch_set_log.assert_called_once_with(True)

    @patch.object(run.autopilot.globals, 'set_log_verbose')
    def test_setup_logging_calls_set_log_verbose_for_vv(self, patch_set_log):
        with patch.object(run, 'get_root_logger'):
            run.setup_logging(self.verbose_level_vv)
            patch_set_log.assert_called_once_with(True)

    def test_set_null_log_handler(self):
        mock_root_logger = Mock()
        run.set_null_log_handler(mock_root_logger)

        self.assertThat(
            mock_root_logger.addHandler.call_args[0][0],
            IsInstance(logging.NullHandler)
        )

    @patch.object(run, 'get_root_logger')
    def test_verbse_level_zero_sets_null_handler(self, fake_get_logger):
        with patch.object(run, 'set_null_log_handler') as fake_set_null:
            run.setup_logging(0)

            fake_set_null.assert_called_once_with(
                fake_get_logger.return_value
            )

    def test_stderr_handler_sets_stream_handler_with_custom_formatter(self):
        mock_root_logger = Mock()
        run.set_stderr_stream_handler(mock_root_logger)

        self.assertThat(mock_root_logger.addHandler.call_count, Equals(1))
        created_handler = mock_root_logger.addHandler.call_args[0][0]

        self.assertThat(
            created_handler,
            IsInstance(logging.StreamHandler)
        )
        self.assertThat(
            created_handler.formatter,
            IsInstance(run.LogFormatter)
        )

    @patch.object(run, 'get_root_logger')
    def test_verbose_level_one_sets_stream_handler(self, fake_get_logger):
        with patch.object(run, 'set_stderr_stream_handler') as stderr_handler:
            run.setup_logging(1)

            stderr_handler.assert_called_once_with(
                fake_get_logger.return_value
            )

    def test_enable_debug_log_messages_sets_debugFilter_attr(self):
        with patch.object(run, 'DebugLogFilter') as patched_filter:
            patched_filter.debug_log_enabled = False
            run.enable_debug_log_messages()
            self.assertThat(
                patched_filter.debug_log_enabled,
                Equals(True)
            )

    @patch.object(run, 'get_root_logger')
    def test_verbose_level_two_enables_debug_messages(self, fake_get_logger):
        with patch.object(run, 'enable_debug_log_messages') as enable_debug:
            run.setup_logging(2)

            enable_debug.assert_called_once_with()


class OutputStreamTests(TestCase):

    def remove_tree_if_exists(self, path):
        if os.path.exists(path):
            rmtree(path)

    def test_get_log_file_path_returns_file_path(self):
        requested_path = tempfile.mktemp()
        result = run._get_log_file_path(requested_path)

        self.assertThat(result, Equals(requested_path))

    def test_get_log_file_path_creates_nonexisting_directories(self):
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(self.remove_tree_if_exists, temp_dir)
        dir_to_store_logs = os.path.join(temp_dir, 'some_directory')
        requested_path = os.path.join(dir_to_store_logs, 'my_log.txt')

        run._get_log_file_path(requested_path)
        self.assertThat(dir_to_store_logs, DirExists())

    def test_returns_default_filename_when_passed_directory(self):
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(self.remove_tree_if_exists, temp_dir)
        with patch.object(run, '_get_default_log_filename') as _get_default:
            result = run._get_log_file_path(temp_dir)

            _get_default.assert_called_once_with(temp_dir)
            self.assertThat(result, Equals(_get_default.return_value))

    def test_get_default_log_filename_calls_print_fn(self):
        with patch.object(run, '_print_default_log_path') as patch_print:
            run._get_default_log_filename('/some/path')

            self.assertThat(
                patch_print.call_count,
                Equals(1)
            )
            call_arg = patch_print.call_args[0][0]
            # shouldn't print the directory, since the user already explicitly
            # specified that.
            self.assertThat(call_arg, Not(StartsWith('/some/path')))

    @patch.object(run, '_print_default_log_path')
    def test_get_default_filename_returns_sane_string(self, patched_print):
        with patch.object(run, 'node', return_value='hostname'):
            with patch.object(run, 'datetime') as mock_dt:
                mock_dt.now.return_value.strftime.return_value = 'date-part'

                self.assertThat(
                    run._get_default_log_filename('/some/path'),
                    Equals('/some/path/hostname_date-part.log')
                )

    def test_get_output_stream_gets_stdout_with_no_logfile_specified(self):
        output_stream = run.get_output_stream('text', None)
        self.assertThat(output_stream.name, Equals('<stdout>'))

    def test_get_output_stream_opens_correct_file(self):
        format = 'xml'
        output = tempfile.mktemp()
        self.addCleanup(os.unlink, output)

        output_stream = run.get_output_stream(format, output)
        self.assertThat(output_stream.name, Equals(output))

    def test_text_mode_file_stream_opens_in_text_mode(self):
        path = tempfile.mktemp()
        self.addCleanup(os.unlink, path)
        stream = run._get_text_mode_file_stream(path)
        self.assertThat(stream.mode, Equals('wb'))

    def test_text_mode_file_stream_accepts_text_type_only(self):
        path = tempfile.mktemp()
        self.addCleanup(os.unlink, path)
        stream = run._get_text_mode_file_stream(path)
        self.assertThat(
            lambda: stream.write('Text!'),
            Not(Raises())
        )
        self.assertThat(
            lambda: stream.write(b'Bytes'),
            raises(TypeError)
        )

    def test_binary_mode_file_stream_opens_in_binary_mode(self):
        path = tempfile.mktemp()
        self.addCleanup(os.unlink, path)
        stream = run._get_binary_mode_file_stream(path)
        self.assertThat(stream.mode, Equals('wb'))

    def test_binary_mode_file_stream_accepts_text_only(self):
        path = tempfile.mktemp()
        self.addCleanup(os.unlink, path)
        stream = run._get_binary_mode_file_stream(path)
        self.assertThat(
            lambda: stream.write('Text!'),
            Not(Raises())
        )
        self.assertThat(
            lambda: stream.write(b'Bytes'),
            raises(TypeError)
        )

    def test_raw_binary_mode_file_stream_opens_in_binary_mode(self):
        path = tempfile.mktemp()
        self.addCleanup(os.unlink, path)
        stream = run._get_raw_binary_mode_file_stream(path)
        self.assertThat(stream.mode, Equals('wb'))

    def test_raw_binary_mode_file_stream_accepts_bytes_only(self):
        path = tempfile.mktemp()
        self.addCleanup(os.unlink, path)
        stream = run._get_raw_binary_mode_file_stream(path)
        self.assertThat(
            lambda: stream.write(b'Bytes'),
            Not(Raises())
        )
        self.assertThat(
            lambda: stream.write('Text'),
            raises(TypeError)
        )

    def test_xml_format_opens_text_mode_stream(self):
        output = tempfile.mktemp()
        format = 'xml'
        with patch.object(run, '_get_text_mode_file_stream') as pgts:
            run.get_output_stream(format, output)
            pgts.assert_called_once_with(output)

    def test_txt_format_opens_binary_mode_stream(self):
        output = tempfile.mktemp()
        format = 'text'
        with patch.object(run, '_get_binary_mode_file_stream') as pgbs:
            run.get_output_stream(format, output)
            pgbs.assert_called_once_with(output)

    def test_subunit_format_opens_raw_binary_mode_stream(self):
        output = tempfile.mktemp()
        format = 'subunit'
        with patch.object(run, '_get_raw_binary_mode_file_stream') as pgrbs:
            run.get_output_stream(format, output)
            pgrbs.assert_called_once_with(output)

    def test_print_log_file_location_prints_correct_message(self):
        path = self.getUniqueString()

        with patch('sys.stdout', new=StringIO()) as patched_stdout:
            run._print_default_log_path(path)
            output = patched_stdout.getvalue()

        expected = "Using default log filename: %s\n" % path
        self.assertThat(expected, Equals(output))


class TestProgramTests(TestCase):

    """Tests for the TestProgram class.

    These tests are a little ugly at the moment, and will continue to be so
    until we refactor the run module to make it more testable.

    """

    def test_can_provide_args(self):
        fake_args = Namespace()
        program = run.TestProgram(fake_args)

        self.assertThat(program.args, Equals(fake_args))

    def test_calls_parse_args_by_default(self):
        fake_args = Namespace()
        with patch.object(run, '_parse_arguments') as fake_parse_args:
            fake_parse_args.return_value = fake_args
            program = run.TestProgram()

            fake_parse_args.assert_called_once_with()
            self.assertThat(program.args, Equals(fake_args))

    def test_run_calls_setup_logging_with_verbose_arg(self):
        fake_args = Namespace(verbose=1, mode='')
        program = run.TestProgram(fake_args)
        with patch.object(run, 'setup_logging') as patched_setup_logging:
            program.run()

            patched_setup_logging.assert_called_once_with(True)

    def test_list_command_calls_list_tests_method(self):
        fake_args = Namespace(mode='list')
        program = run.TestProgram(fake_args)
        with patch.object(program, 'list_tests') as patched_list_tests:
            program.run()

            patched_list_tests.assert_called_once_with()

    def test_run_command_calls_run_tests_method(self):
        fake_args = Namespace(mode='run')
        program = run.TestProgram(fake_args)
        with patch.object(program, 'run_tests') as patched_run_tests:
            program.run()

            patched_run_tests.assert_called_once_with()

    def test_vis_command_calls_run_vis_method(self):
        fake_args = Namespace(mode='vis')
        program = run.TestProgram(fake_args)
        with patch.object(program, 'run_vis') as patched_run_vis:
            program.run()

            patched_run_vis.assert_called_once_with()

    def test_vis_command_runs_under_profiling_if_profiling_is_enabled(self):
        fake_args = Namespace(
            mode='vis',
            enable_profile=True,
            testability=False,
        )
        program = run.TestProgram(fake_args)
        with patch.object(run, '_run_with_profiling') as patched_run_profile:
            program.run()

            self.assertThat(
                patched_run_profile.call_count,
                Equals(1),
            )

    def test_launch_command_calls_launch_app_method(self):
        fake_args = Namespace(mode='launch')
        program = run.TestProgram(fake_args)
        with patch.object(program, 'launch_app') as patched_launch_app:
            program.run()

            patched_launch_app.assert_called_once_with()

    def test_run_tests_calls_utility_functions(self):
        """The run_tests method must call all the utility functions.

        This test is somewhat ugly, and relies on a lot of mocks. This will be
        cleaned up once run has been completely refactored.

        """
        fake_args = create_default_run_args()
        program = run.TestProgram(fake_args)
        mock_test_result = Mock()
        mock_test_result.wasSuccessful.return_value = True
        mock_test_suite = Mock()
        mock_test_suite.run.return_value = mock_test_result
        mock_construct_test_result = Mock()
        with ExitStack() as stack:
            load_tests = stack.enter_context(
                patch.object(run, 'load_test_suite_from_name')
            )
            fake_construct = stack.enter_context(
                patch.object(run, 'construct_test_result')
            )
            configure_debug = stack.enter_context(
                patch.object(run, '_configure_debug_profile')
            )
            config_timeout = stack.enter_context(
                patch.object(run, '_configure_timeout_profile')
            )
            config_test_timeout = stack.enter_context(
                patch.object(run, '_configure_test_timeout')
            )

            load_tests.return_value = (mock_test_suite, False)
            fake_construct.return_value = mock_construct_test_result
            program.run()

            config_timeout.assert_called_once_with(fake_args)
            configure_debug.assert_called_once_with(fake_args)
            config_test_timeout.assert_called_once_with(fake_args)
            fake_construct.assert_called_once_with(fake_args)
            load_tests.assert_called_once_with(fake_args.suite)

    def test_dont_run_when_zero_tests_loaded(self):
        fake_args = create_default_run_args()
        program = run.TestProgram(fake_args)
        with patch('sys.stdout', new=StringIO()):
            self.assertRaisesRegexp(RuntimeError,
                                    'Did not find any tests',
                                    program.run)


def create_default_run_args(**kwargs):
    """Create a an argparse.Namespace object containing arguments required
    to make autopilot.run.TestProgram run a suite of tests.

    Every feature that can be turned off will be. Individual arguments can be
    specified with keyword arguments to this function.
    """
    defaults = dict(
        random_order=False,
        debug_profile='normal',
        timeout_profile='normal',
        record_directory='',
        record=False,
        record_options='',
        verbose=False,
        mode='run',
        suite='foo',
        test_config='',
        test_timeout=0,
    )
    defaults.update(kwargs)
    return Namespace(**defaults)
