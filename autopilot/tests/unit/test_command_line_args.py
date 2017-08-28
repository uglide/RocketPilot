#!/usr/bin/env python
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


"Unit tests for the command line parser in autopilot."


from unittest.mock import patch

from io import StringIO

from testscenarios import WithScenarios
from testtools import TestCase
from testtools.matchers import Equals

from autopilot.run import _parse_arguments


class InvalidArguments(Exception):
    pass


def parse_args(args):
    if isinstance(args, str):
        args = args.split()
    try:
        return _parse_arguments(args)
    except SystemExit as e:
        raise InvalidArguments("%s" % e)


class CommandLineArgsTests(TestCase):

    def test_launch_command_accepts_application(self):
        args = parse_args("launch app")
        self.assertThat(args.mode, Equals("launch"))

    def test_launch_command_has_correct_default_interface(self):
        args = parse_args("launch app")
        self.assertThat(args.interface, Equals("Auto"))

    def test_launch_command_can_specify_Qt_interface(self):
        args = parse_args("launch -i Qt app")
        self.assertThat(args.interface, Equals("Qt"))

    def test_launch_command_can_specify_Gtk_interface(self):
        args = parse_args("launch -i Gtk app")
        self.assertThat(args.interface, Equals("Gtk"))

    @patch('sys.stderr', new=StringIO())
    def test_launch_command_fails_on_unknown_interface(self):
        self.assertRaises(
            InvalidArguments, parse_args, "launch -i unknown app")

    def test_launch_command_has_correct_default_verbosity(self):
        args = parse_args("launch app")
        self.assertThat(args.verbose, Equals(False))

    def test_launch_command_can_specify_verbosity(self):
        args = parse_args("launch -v app")
        self.assertThat(args.verbose, Equals(1))

    def test_launch_command_can_specify_extra_verbosity(self):
        args = parse_args("launch -vv app")
        self.assertThat(args.verbose, Equals(2))
        args = parse_args("launch -v -v app")
        self.assertThat(args.verbose, Equals(2))

    def test_launch_command_stores_application(self):
        args = parse_args("launch app")
        self.assertThat(args.application, Equals(["app"]))

    def test_launch_command_stores_application_with_args(self):
        args = parse_args("launch app arg1 arg2")
        self.assertThat(args.application, Equals(["app", "arg1", "arg2"]))

    def test_launch_command_accepts_different_app_arg_formats(self):
        args = parse_args("launch app -s --long --key=val arg1 arg2")
        self.assertThat(
            args.application,
            Equals(["app", "-s", "--long", "--key=val", "arg1", "arg2"]))

    @patch('sys.stderr', new=StringIO())
    def test_launch_command_must_specify_app(self):
        self.assertRaises(InvalidArguments, parse_args, "launch")

    @patch('autopilot.run.have_vis', new=lambda: True)
    def test_vis_present_when_vis_module_installed(self):
        args = parse_args('vis')
        self.assertThat(args.mode, Equals("vis"))

    @patch('autopilot.run.have_vis', new=lambda: False)
    @patch('sys.stderr', new=StringIO())
    def test_vis_not_present_when_vis_module_not_installed(self):
        self.assertRaises(InvalidArguments, parse_args, 'vis')

    @patch('autopilot.run.have_vis', new=lambda: True)
    def test_vis_default_verbosity(self):
        args = parse_args('vis')
        self.assertThat(args.verbose, Equals(False))

    @patch('autopilot.run.have_vis', new=lambda: True)
    def test_vis_single_verbosity(self):
        args = parse_args('vis -v')
        self.assertThat(args.verbose, Equals(1))

    @patch('autopilot.run.have_vis', new=lambda: True)
    def test_vis_double_verbosity(self):
        args = parse_args('vis -vv')
        self.assertThat(args.verbose, Equals(2))
        args = parse_args('vis -v -v')
        self.assertThat(args.verbose, Equals(2))

    @patch('autopilot.run.have_vis', new=lambda: True)
    def test_vis_default_testability_flag(self):
        args = parse_args('vis')
        self.assertThat(args.testability, Equals(False))

    @patch('autopilot.run.have_vis', new=lambda: True)
    def test_vis_can_set_testability_flag(self):
        args = parse_args('vis -testability')
        self.assertThat(args.testability, Equals(True))

    @patch('autopilot.run.have_vis', new=lambda: True)
    def test_vis_default_profile_flag(self):
        args = parse_args('vis')
        self.assertThat(args.enable_profile, Equals(False))

    @patch('autopilot.run.have_vis', new=lambda: True)
    def test_vis_can_enable_profiling(self):
        args = parse_args('vis --enable-profile')
        self.assertThat(args.enable_profile, Equals(True))

    def test_list_mode(self):
        args = parse_args('list foo')
        self.assertThat(args.mode, Equals("list"))

    def test_list_mode_accepts_suite_name(self):
        args = parse_args('list foo')
        self.assertThat(args.suite, Equals(["foo"]))

    def test_list_mode_accepts_many_suite_names(self):
        args = parse_args('list foo bar baz')
        self.assertThat(args.suite, Equals(["foo", "bar", "baz"]))

    def test_list_run_order_long_option(self):
        args = parse_args('list --run-order foo')
        self.assertThat(args.run_order, Equals(True))

    def test_list_run_order_short_option(self):
        args = parse_args('list -ro foo')
        self.assertThat(args.run_order, Equals(True))

    def test_list_no_run_order(self):
        args = parse_args('list foo')
        self.assertThat(args.run_order, Equals(False))

    def test_list_suites_option(self):
        args = parse_args('list --suites foo')
        self.assertThat(args.suites, Equals(True))

    def test_list_not_suites_option(self):
        args = parse_args('list foo')
        self.assertThat(args.suites, Equals(False))

    def test_run_mode(self):
        args = parse_args('run foo')
        self.assertThat(args.mode, Equals("run"))

    def test_run_mode_accepts_suite_name(self):
        args = parse_args('run foo')
        self.assertThat(args.suite, Equals(["foo"]))

    def test_run_mode_accepts_many_suite_names(self):
        args = parse_args('run foo bar baz')
        self.assertThat(args.suite, Equals(["foo", "bar", "baz"]))

    def test_run_command_default_output(self):
        args = parse_args('run foo')
        self.assertThat(args.output, Equals(None))

    def test_run_command_path_output_short(self):
        args = parse_args('run -o /path/to/file foo')
        self.assertThat(args.output, Equals("/path/to/file"))

    def test_run_command_path_output_long(self):
        args = parse_args('run --output ../file foo')
        self.assertThat(args.output, Equals("../file"))

    def test_run_command_default_format(self):
        args = parse_args('run foo')
        self.assertThat(args.format, Equals("text"))

    def test_run_command_text_format_short_version(self):
        args = parse_args('run -f text foo')
        self.assertThat(args.format, Equals("text"))

    def test_run_command_text_format_long_version(self):
        args = parse_args('run --format text foo')
        self.assertThat(args.format, Equals("text"))

    def test_run_command_xml_format_short_version(self):
        args = parse_args('run -f xml foo')
        self.assertThat(args.format, Equals("xml"))

    def test_run_command_xml_format_long_version(self):
        args = parse_args('run --format xml foo')
        self.assertThat(args.format, Equals("xml"))

    def test_run_command_default_failfast_off(self):
        args = parse_args('run foo')
        self.assertThat(args.failfast, Equals(False))

    def test_run_command_accepts_failfast_short(self):
        args = parse_args('run -ff foo')
        self.assertThat(args.failfast, Equals(True))

    def test_run_command_accepts_failfast_long(self):
        args = parse_args('run --failfast foo')
        self.assertThat(args.failfast, Equals(True))

    @patch('sys.stderr', new=StringIO())
    def test_run_command_unknown_format_short_version(self):
        self.assertRaises(
            InvalidArguments, parse_args, 'run -f unknown foo')

    @patch('sys.stderr', new=StringIO())
    def test_run_command_unknown_format_long_version(self):
        self.assertRaises(
            InvalidArguments, parse_args, 'run --format unknown foo')

    def test_run_command_record_flag_default(self):
        args = parse_args("run foo")
        self.assertThat(args.record, Equals(False))

    def test_run_command_record_flag_short(self):
        args = parse_args("run -r foo")
        self.assertThat(args.record, Equals(True))

    def test_run_command_record_flag_long(self):
        args = parse_args("run --record foo")
        self.assertThat(args.record, Equals(True))

    def test_run_command_record_dir_flag_short(self):
        args = parse_args("run -rd /path/to/dir foo")
        self.assertThat(args.record_directory, Equals("/path/to/dir"))

    def test_run_command_record_dir_flag_long(self):
        args = parse_args("run --record-directory /path/to/dir foo")
        self.assertThat(args.record_directory, Equals("/path/to/dir"))

    def test_run_command_record_options_flag_long(self):
        args = parse_args(
            "run --record-options=--fps=6,--no-wm-check foo")
        self.assertThat(args.record_options, Equals("--fps=6,--no-wm-check"))

    def test_run_command_random_order_flag_short(self):
        args = parse_args("run -ro foo")
        self.assertThat(args.random_order, Equals(True))

    def test_run_command_random_order_flag_long(self):
        args = parse_args("run --random-order foo")
        self.assertThat(args.random_order, Equals(True))

    def test_run_command_random_order_flag_default(self):
        args = parse_args("run foo")
        self.assertThat(args.random_order, Equals(False))

    def test_run_default_verbosity(self):
        args = parse_args('run foo')
        self.assertThat(args.verbose, Equals(False))

    def test_run_single_verbosity(self):
        args = parse_args('run -v foo')
        self.assertThat(args.verbose, Equals(1))

    def test_run_double_verbosity(self):
        args = parse_args('run -vv foo')
        self.assertThat(args.verbose, Equals(2))
        args = parse_args('run -v -v foo')
        self.assertThat(args.verbose, Equals(2))

    def test_fails_with_no_arguments_supplied(self):
        with patch('sys.stderr', new=StringIO()) as patched_err:
            try:
                _parse_arguments([])
            except SystemExit as e:
                self.assertThat(e.code, Equals(2))
                stderr_lines = patched_err.getvalue().split('\n')
                self.assertTrue(
                    stderr_lines[-2].endswith("error: too few arguments")
                )
                self.assertThat(stderr_lines[-1], Equals(""))
            else:
                self.fail("Argument parser unexpectedly passed")

    def test_default_debug_profile_is_normal(self):
        args = parse_args('run foo')
        self.assertThat(args.debug_profile, Equals('normal'))

    def test_can_select_normal_profile(self):
        args = parse_args('run --debug-profile normal foo')
        self.assertThat(args.debug_profile, Equals('normal'))

    def test_can_select_verbose_profile(self):
        args = parse_args('run --debug-profile verbose foo')
        self.assertThat(args.debug_profile, Equals('verbose'))

    @patch('sys.stderr', new=StringIO())
    def test_cannot_select_other_debug_profile(self):
        self.assertRaises(
            InvalidArguments,
            parse_args,
            'run --debug-profile nonexistant foo'
        )

    def test_default_timeout_profile_is_normal(self):
        args = parse_args('run foo')
        self.assertThat(args.timeout_profile, Equals('normal'))

    def test_can_select_long_timeout_profile(self):
        args = parse_args('run --timeout-profile long foo')
        self.assertThat(args.timeout_profile, Equals('long'))

    @patch('sys.stderr', new=StringIO())
    def test_cannot_select_other_timeout_profile(self):
        self.assertRaises(
            InvalidArguments,
            parse_args,
            'run --timeout-profile nonexistant foo'
        )

    def test_list_mode_strips_single_suite_slash(self):
        args = parse_args('list foo/')
        self.assertThat(args.suite, Equals(["foo"]))

    def test_list_mode_strips_multiple_suite_slash(self):
        args = parse_args('list foo/ bar/')
        self.assertThat(args.suite, Equals(["foo", "bar"]))

    def test_run_mode_strips_single_suite_slash(self):
        args = parse_args('run foo/')
        self.assertThat(args.suite, Equals(["foo"]))

    def test_run_mode_strips_multiple_suite_slash(self):
        args = parse_args('run foo/ bar/')
        self.assertThat(args.suite, Equals(["foo", "bar"]))

    def test_accepts_config_string(self):
        args = parse_args('run --config foo test_id')
        self.assertThat(args.test_config, Equals('foo'))

    def test_accepts_long_config_string(self):
        args = parse_args('run --config bar=foo,baz test_id')
        self.assertThat(args.test_config, Equals('bar=foo,baz'))

    def test_default_config_string(self):
        args = parse_args('run foo')
        self.assertThat(args.test_config, Equals(""))

    def test_default_test_timeout(self):
        args = parse_args('run foo')
        self.assertThat(args.test_timeout, Equals(0))

    def test_can_set_test_timeout(self):
        args = parse_args('run --test-timeout 42 foo')
        self.assertThat(args.test_timeout, Equals(42))


class GlobalProfileOptionTests(WithScenarios, TestCase):

    scenarios = [
        ('run', dict(command='run', args='foo')),
        ('list', dict(command='list', args='foo')),
        ('launch', dict(command='launch', args='foo')),
        ('vis', dict(command='vis', args='')),
    ]

    @patch('autopilot.run.have_vis', new=lambda: True)
    def test_all_commands_support_profile_option(self):
        command_parts = [self.command, '--enable-profile']
        if self.args:
            command_parts.append(self.args)
        args = parse_args(' '.join(command_parts))
        self.assertThat(args.enable_profile, Equals(True))
