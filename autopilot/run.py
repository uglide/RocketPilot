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


from argparse import ArgumentParser, Action, REMAINDER
from codecs import open
from collections import OrderedDict
import cProfile
from datetime import datetime
from imp import find_module
import logging
import os
import os.path
from platform import node
from random import shuffle
import subprocess
import sys
from unittest import TestLoader, TestSuite

from testtools import iterate_tests

from autopilot import get_version_string, have_vis
import autopilot.globals
from autopilot import _config as test_config
from autopilot._debug import (
    get_all_debug_profiles,
    get_default_debug_profile,
)
from autopilot import _video
from autopilot.testresult import get_default_format, get_output_formats
from autopilot.utilities import DebugLogFilter, LogFormatter
from autopilot.application._launcher import (
    _get_app_env_from_string_hint,
    get_application_launcher_wrapper,
    launch_process,
)


def _get_parser():
    """Return a parser object for handling command line arguments."""
    common_arguments = ArgumentParser(add_help=False)
    common_arguments.add_argument(
        '--enable-profile', required=False, default=False,
        action="store_true", help="Enable collection of profile data for "
        "autopilot itself. If enabled, profile data will be stored in "
        "'autopilot_<pid>.profile' in the current working directory."
    )
    parser = ArgumentParser(
        description="Autopilot test tool.",
        epilog="Each command (run, list, launch etc.) has additional help that"
        " can be viewed by passing the '-h' flag to the command. For "
        "example: 'autopilot run -h' displays further help for the "
        "'run' command."
    )
    parser.add_argument('-v', '--version', action='version',
                        version=get_version_string(),
                        help="Display autopilot version and exit.")
    subparsers = parser.add_subparsers(help='Run modes', dest="mode")

    parser_run = subparsers.add_parser(
        'run', help="Run autopilot tests", parents=[common_arguments]
    )
    parser_run.add_argument('-o', "--output", required=False,
                            help='Write test result report to file.\
                            Defaults to stdout.\
                            If given a directory instead of a file will \
                            write to a file in that directory named: \
                            <hostname>_<dd.mm.yyy_HHMMSS>.log')
    available_formats = get_output_formats().keys()
    parser_run.add_argument('-f', "--format", choices=available_formats,
                            default=get_default_format(),
                            required=False,
                            help='Specify desired output format. \
                            Default is "text".')
    parser_run.add_argument("-ff", "--failfast", action='store_true',
                            required=False, default=False,
                            help="Stop the test run on the first error \
                            or failure.")
    parser_run.add_argument('-r', '--record', action='store_true',
                            default=False, required=False,
                            help="Record failing tests. Required \
                            'recordmydesktop' app to be installed.\
                            Videos are stored in /tmp/autopilot if not \
                            specified with -rd option.")
    parser_run.add_argument("-rd", "--record-directory", required=False,
                            type=str, help="Directory to put recorded tests")
    parser_run.add_argument("--record-options", required=False,
                            type=str, help="Comma separated list of options \
                            to pass to recordmydesktop")
    parser_run.add_argument("-ro", "--random-order", action='store_true',
                            required=False, default=False,
                            help="Run the tests in random order")
    parser_run.add_argument(
        '-v', '--verbose', default=False, required=False, action='count',
        help="If set, autopilot will output test log data to stderr during a "
        "test run. Set twice (i.e. -vv) to also log debug level messages. "
        "(This can be useful for debugging autopilot itself.)")
    parser_run.add_argument(
        "--debug-profile",
        choices=[p.name for p in get_all_debug_profiles()],
        default=get_default_debug_profile().name,
        help="Select a profile for what additional debugging information "
        "should be attached to failed test results."
    )
    parser_run.add_argument(
        "--timeout-profile",
        choices=['normal', 'long'],
        default='normal',
        help="Alter the timeout values Autopilot uses. Selecting 'long' will "
        "make autopilot use longer timeouts for various polling loops. This "
        "can be useful if autopilot is running on very slow hardware"
    )
    parser_run.add_argument(
        "-c", "--config", default="", help="If set, specifies configuration "
        "for the test suite being run. Value should be a comma-separated list "
        "of values, where each value is either of the form 'key', or "
        "'key=value'.", dest="test_config"
    )
    parser_run.add_argument(
        "--test-timeout", default=0, type=int, help="If set, autopilot will "
        "attempt to abort tests that have run longer than <test-timeout> "
        "seconds. This is not guaranteed to succeed - several scenarios exist "
        "which make it impossible to abort a test case. Tests aborted will "
        "raise a 'TimeoutException' error."
    )
    parser_run.add_argument("suite", nargs="+",
                            help="Specify test suite(s) to run.")

    parser_list = subparsers.add_parser(
        'list', help="List autopilot tests", parents=[common_arguments]
    )
    parser_list.add_argument(
        "-ro", "--run-order", required=False, default=False,
        action="store_true",
        help="List tests in run order, rather than alphabetical order (the "
        "default).")
    parser_list.add_argument(
        "--suites", required=False, action='store_true',
        help="Lists only available suites, not tests contained within the "
        "suite.")
    parser_list.add_argument("suite", nargs="+",
                             help="Specify test suite(s) to run.")

    if have_vis():
        parser_vis = subparsers.add_parser(
            'vis', help="Open the Autopilot visualiser tool",
            parents=[common_arguments]
        )
        parser_vis.add_argument(
            '-v', '--verbose', required=False, default=False, action='count',
            help="Show autopilot log messages. Set twice to also log data "
            "useful for debugging autopilot itself.")
        parser_vis.add_argument(
            '-testability', required=False, default=False,
            action='store_true', help="Start the vis tool in testability "
            "mode. Used for self-tests only."
        )

    parser_launch = subparsers.add_parser(
        'launch', help="Launch an application with introspection enabled",
        parents=[common_arguments]
    )
    parser_launch.add_argument(
        '-i', '--interface', choices=('Gtk', 'Qt', 'Auto'), default='Auto',
        help="Specify which introspection interface to load. The default"
        "('Auto') uses ldd to try and detect which interface to load.")
    parser_launch.add_argument(
        '-v', '--verbose', required=False, default=False, action='count',
        help="Show autopilot log messages. Set twice to also log data useful "
        "for debugging autopilot itself.")
    parser_launch.add_argument(
        'application', action=_OneOrMoreArgumentStoreAction, type=str,
        nargs=REMAINDER,
        help="The application to launch. Can be a full path, or just an "
        "application name (in which case Autopilot will search for it in "
        "$PATH).")
    return parser


def _parse_arguments(argv=None):
    """Parse command-line arguments, and return an argparse arguments
    object.
    """
    parser = _get_parser()
    args = parser.parse_args(args=argv)

    # TR - 2013-11-27 - a bug in python3.3 means argparse doesn't fail
    # correctly when no commands are specified.
    # http://bugs.python.org/issue16308
    if args.mode is None:
        parser.error("too few arguments")

    if 'suite' in args:
        args.suite = [suite.rstrip('/') for suite in args.suite]

    return args


class _OneOrMoreArgumentStoreAction(Action):

    def __call__(self, parser, namespace, values, option_string=None):
        if len(values) == 0:
            parser.error(
                "Must specify at least one argument to the 'launch' command")
        setattr(namespace, self.dest, values)


def setup_logging(verbose):
    """Configure the root logger and verbose logging to stderr."""
    root_logger = get_root_logger()
    root_logger.setLevel(logging.INFO)
    if verbose == 0:
        set_null_log_handler(root_logger)
    if verbose >= 1:
        autopilot.globals.set_log_verbose(True)
        set_stderr_stream_handler(root_logger)
    if verbose >= 2:
        root_logger.setLevel(logging.DEBUG)
        enable_debug_log_messages()


def log_autopilot_version():
    root_logger = get_root_logger()
    root_logger.info(get_version_string())


def get_root_logger():
    return logging.getLogger()


def set_null_log_handler(root_logger):
    root_logger.addHandler(logging.NullHandler())


def set_stderr_stream_handler(root_logger):
    formatter = LogFormatter()
    stderr_handler = logging.StreamHandler(stream=sys.stderr)
    stderr_handler.setFormatter(formatter)
    root_logger.addHandler(stderr_handler)


def enable_debug_log_messages():
    DebugLogFilter.debug_log_enabled = True


def construct_test_result(args):
    formats = get_output_formats()
    return formats[args.format](
        stream=get_output_stream(args.format, args.output),
        failfast=args.failfast,
    )


def get_output_stream(format, path):
    """Get an output stream pointing to 'path' that's appropriate for format
    'format'.

    :param format: A string that describes one of the output formats supported
        by autopilot.
    :param path: A path to the file you wish to write, or None to write to
        stdout.

    """
    if path:
        log_file = _get_log_file_path(path)
        if format == 'xml':
            return _get_text_mode_file_stream(log_file)
        elif format == 'text':
            return _get_binary_mode_file_stream(log_file)
        else:
            return _get_raw_binary_mode_file_stream(log_file)
    else:
        return sys.stdout


def _get_text_mode_file_stream(log_file):
    return open(
        log_file,
        'w',
        encoding='utf-8',
    )


def _get_binary_mode_file_stream(log_file):
    return open(
        log_file,
        'w',
        encoding='utf-8',
        errors='backslashreplace'
    )


def _get_raw_binary_mode_file_stream(log_file):
    return open(
        log_file,
        'wb'
    )


def _get_log_file_path(requested_path):
    dirname = os.path.dirname(requested_path)
    if dirname != '' and not os.path.exists(dirname):
        os.makedirs(dirname)
    if os.path.isdir(requested_path):
        return _get_default_log_filename(requested_path)
    return requested_path


def _get_default_log_filename(target_directory):
    """Return a filename that's likely to be unique to this test run."""
    default_log_filename = "%s_%s.log" % (
        node(),
        datetime.now().strftime("%d.%m.%y-%H%M%S")
    )
    _print_default_log_path(default_log_filename)
    log_file = os.path.join(target_directory, default_log_filename)
    return log_file


def _print_default_log_path(default_log_filename):
    print("Using default log filename: %s" % default_log_filename)


def get_package_location(import_name):
    """Get the on-disk location of a package from a test id name.

    :raises ImportError: if the name could not be found.
    :returns: path as a string
    """
    top_level_pkg = import_name.split('.')[0]
    _, path, _ = find_module(top_level_pkg, [os.getcwd()] + sys.path)
    return os.path.abspath(
        os.path.join(
            path,
            '..'
        )
    )


def _is_testing_autopilot_module(test_names):
    return (
        os.path.basename(sys.argv[0]) == 'autopilot'
        and any(t.startswith('autopilot') for t in test_names)
    )


def _reexecute_autopilot_using_module():
    autopilot_command = [sys.executable, '-m', 'autopilot.run'] + sys.argv[1:]
    try:
        subprocess.check_call(autopilot_command)
    except subprocess.CalledProcessError as e:
        return e.returncode
    return 0


def _discover_test(test_name):
    """Return tuple of (TestSuite of found test, top_level_dir of test).

    :raises ImportError: if test_name isn't a valid module or test name

    """
    loader = TestLoader()
    top_level_dir = get_package_location(test_name)
    # no easy way to figure out if test_name is a module or a test, so we
    # try to do the discovery first=...
    try:
        test = loader.discover(
            start_dir=test_name,
            top_level_dir=top_level_dir
        )
    except ImportError:
        # and if that fails, we try it as a test id.
        test = loader.loadTestsFromName(test_name)

    return (test, top_level_dir)


def _discover_requested_tests(test_names):
    """Return a collection of tests that are under test_names.

    returns a tuple containig a TestSuite of tests found and a boolean
    depicting wherether any difficulties were encountered while searching
    (namely un-importable module names).

    """
    all_tests = []
    test_package_locations = []
    error_occured = False
    for name in test_names:
        try:
            test, top_level_dir = _discover_test(name)
            all_tests.append(test)
            test_package_locations.append(top_level_dir)
        except ImportError as e:
            _handle_discovery_error(name, e)
            error_occured = True

    _show_test_locations(test_package_locations)

    return (TestSuite(all_tests), error_occured)


def _handle_discovery_error(test_name, exception):
    print("could not import package %s: %s" % (test_name, str(exception)))


def _filter_tests(all_tests, test_names):
    """Filter a given TestSuite for tests starting with any name contained
    within test_names.

    """
    requested_tests = {}
    for test in iterate_tests(all_tests):
        # The test loader returns tests that start with 'unittest.loader' if
        # for whatever reason the test failed to load. We run the tests without
        # the built-in exception catching turned on, so we can get at the
        # raised exception, which we print, so the user knows that something in
        # their tests is broken.
        if test.id().startswith('unittest.loader'):
            test_id = test._testMethodName
            try:
                test.debug()
            except Exception as e:
                print(e)
        else:
            test_id = test.id()
        if any([test_id.startswith(name) for name in test_names]):
            requested_tests[test_id] = test

    return requested_tests


def load_test_suite_from_name(test_names):
    """Return a test suite object given a dotted test names.

    Returns a tuple containing the TestSuite and a boolean indicating wherever
    any issues where encountered during the loading process.

    """
    # The 'autopilot' program cannot be used to run the autopilot test suite,
    # since setuptools needs to import 'autopilot.run', and that grabs the
    # system autopilot package. After that point, the module is loaded and
    # cached in sys.modules, and there's no way to unload a module in python
    # once it's been loaded.
    #
    # The solution is to detect whether we've been started with the 'autopilot'
    # application, *and* whether we're running the autopilot test suite itself,
    # and ≡ that's the case, we re-call autopilot using the standard
    # autopilot.run entry method, and exit with the sub-process' return code.
    if _is_testing_autopilot_module(test_names):
        exit(_reexecute_autopilot_using_module())

    if isinstance(test_names, str):
        test_names = [test_names]
    elif not isinstance(test_names, list):
        raise TypeError("test_names must be either a string or list, not %r"
                        % (type(test_names)))

    all_tests, error_occured = _discover_requested_tests(test_names)
    filtered_tests = _filter_tests(all_tests, test_names)

    return (TestSuite(filtered_tests.values()), error_occured)


def _show_test_locations(test_directories):
    """Print the test directories tests have been loaded from."""
    print("Loading tests from: %s\n" % ",".join(sorted(test_directories)))


def _configure_debug_profile(args):
    for fixture_class in get_all_debug_profiles():
        if args.debug_profile == fixture_class.name:
            autopilot.globals.set_debug_profile_fixture(fixture_class)
            break


def _configure_timeout_profile(args):
    if args.timeout_profile == 'long':
        autopilot.globals.set_default_timeout_period(20.0)
        autopilot.globals.set_long_timeout_period(30.0)


def _configure_test_timeout(args):
    autopilot.globals.set_test_timeout(args.test_timeout)


def _prepare_application_for_launch(application, interface):
    app_path, app_arguments = _get_application_path_and_arguments(application)
    return _prepare_launcher_environment(
        interface,
        app_path,
        app_arguments
    )


def _get_application_path_and_arguments(application):

    app_name, app_arguments = _get_app_name_and_args(application)

    try:
        app_path = _get_applications_full_path(app_name)
    except ValueError as e:
        raise RuntimeError(str(e))

    return app_path, app_arguments


def _get_app_name_and_args(argument_list):
    """Return a tuple of (app_name, [app_args])."""
    return argument_list[0], argument_list[1:]


def _get_applications_full_path(app_name):
    if not _application_name_is_full_path(app_name):
        try:
            app_name = subprocess.check_output(
                ["which", app_name],
                universal_newlines=True
            ).strip()
        except subprocess.CalledProcessError:
            raise ValueError(
                "Cannot find application '%s'" % (app_name)
            )
    return app_name


def _application_name_is_full_path(app_name):
    return os.path.isabs(app_name) or os.path.exists(app_name)


def _prepare_launcher_environment(interface, app_path, app_arguments):
    launcher_env = _get_application_launcher_env(interface, app_path)
    _raise_if_launcher_is_none(launcher_env, app_path)
    return launcher_env.prepare_environment(app_path, app_arguments)


def _raise_if_launcher_is_none(launcher_env, app_path):
    if launcher_env is None:
        raise RuntimeError(
            "Could not determine introspection type to use for "
            "application '{app_path}'.\n"
            "(Perhaps use the '-i' argument to specify an interface.)".format(
                app_path=app_path
            )
        )


def _get_application_launcher_env(interface, application_path):
    launcher_env = None
    if interface == 'Auto':
        launcher_env = _try_determine_launcher_env_or_raise(application_path)
    else:
        launcher_env = _get_app_env_from_string_hint(interface)

    return launcher_env


def _try_determine_launcher_env_or_raise(app_name):
    try:
        return get_application_launcher_wrapper(app_name)
    except RuntimeError as e:
        # Re-format the runtime error to be more user friendly.
        raise RuntimeError(
            "Error detecting launcher: {err}\n"
            "(Perhaps use the '-i' argument to specify an interface.)".format(
                err=str(e)
            )
        )


def _print_message_and_exit_error(msg):
    print(msg)
    exit(1)


def _run_with_profiling(callable, output_file=None):
    if output_file is None:
        output_file = 'autopilot_%d.profile' % (os.getpid())
    cProfile.runctx(
        'callable()',
        globals(),
        locals(),
        filename=output_file,
    )


class TestProgram(object):

    def __init__(self, defined_args=None):
        """Create a new TestProgram instance.

        :param defined_args: If specified, must be an object representing
            command line arguments, as returned by the ``_parse_arguments``
            function. Passing in arguments prevents argparse from parsing
            sys.argv. Used in testing.

        """
        self.args = defined_args or _parse_arguments()

    def run(self):
        setup_logging(getattr(self.args, 'verbose', False))

        log_autopilot_version()

        action = None
        if self.args.mode == 'list':
            action = self.list_tests
        elif self.args.mode == 'run':
            action = self.run_tests
        elif self.args.mode == 'vis':
            action = self.run_vis
        elif self.args.mode == 'launch':
            action = self.launch_app

        if action is not None:
            if getattr(self.args, 'enable_profile', False):
                _run_with_profiling(action)
            else:
                action()

    def run_vis(self):
        # importing this requires that DISPLAY is set. Since we don't always
        # want that requirement, do the import here:
        from autopilot.vis import vis_main

        # XXX - in quantal, overlay scrollbars make this process consume 100%
        # of the CPU. It's a known bug:
        #
        # bugs.launchpad.net/ubuntu/quantal/+source/qt4-x11/+bug/1005677
        #
        # Once that's been fixed we can remove the following line:
        #
        os.putenv('LIBOVERLAY_SCROLLBAR', '0')
        args = ['-testability'] if self.args.testability else []
        vis_main(args)

    def launch_app(self):
        """Launch an application, with introspection support."""

        try:
            app_path, app_arguments = _prepare_application_for_launch(
                self.args.application,
                self.args.interface
            )

            launch_process(
                app_path,
                app_arguments,
                capture_output=False
            )
        except RuntimeError as e:
            _print_message_and_exit_error("Error: " + str(e))

    def run_tests(self):
        """Run tests, using input from `args`."""

        _configure_debug_profile(self.args)
        _configure_timeout_profile(self.args)
        _configure_test_timeout(self.args)

        try:
            _video.configure_video_recording(self.args)
        except RuntimeError as e:
            print("Error: %s" % str(e))
            exit(1)

        test_config.set_configuration_string(self.args.test_config)

        test_suite, error_encountered = load_test_suite_from_name(
            self.args.suite
        )

        if not test_suite.countTestCases():
            raise RuntimeError('Did not find any tests')

        if self.args.random_order:
            shuffle(test_suite._tests)
            print("Running tests in random order")

        result = construct_test_result(self.args)
        result.startTestRun()
        try:
            test_result = test_suite.run(result)
        finally:
            result.stopTestRun()

        if not test_result.wasSuccessful() or error_encountered:
            exit(1)

    def list_tests(self):
        """Print a list of tests we find inside autopilot.tests."""
        num_tests = 0
        total_title = "tests"
        test_suite, error_encountered = load_test_suite_from_name(
            self.args.suite
        )

        if self.args.run_order:
            test_list_fn = lambda: iterate_tests(test_suite)
        else:
            test_list_fn = lambda: sorted(iterate_tests(test_suite), key=id)

        # only show test suites, not test cases. TODO: Check if this is still
        # a requirement.
        if self.args.suites:
            suite_names = ["%s.%s" % (t.__module__, t.__class__.__name__)
                           for t in test_list_fn()]
            unique_suite_names = list(OrderedDict.fromkeys(suite_names).keys())
            num_tests = len(unique_suite_names)
            total_title = "suites"
            print("    %s" % ("\n    ".join(unique_suite_names)))
        else:
            for test in test_list_fn():
                has_scenarios = (hasattr(test, "scenarios")
                                 and type(test.scenarios) is list)
                if has_scenarios:
                    num_tests += len(test.scenarios)
                    print(" *%d %s" % (len(test.scenarios), test.id()))
                else:
                    num_tests += 1
                    print("    " + test.id())
        print("\n\n %d total %s." % (num_tests, total_title))

        if error_encountered:
            exit(1)


def main():
    test_app = TestProgram()
    try:
        test_app.run()
    except RuntimeError as e:
        print(e)
        exit(1)


if __name__ == "__main__":
    main()
