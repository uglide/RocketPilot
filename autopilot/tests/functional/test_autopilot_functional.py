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


from fixtures import TempDir
import glob
import os
import os.path
import re
from tempfile import mktemp
from testtools import skipIf
from testtools.matchers import Contains, Equals, MatchesRegex, Not, NotEquals
from textwrap import dedent
from unittest.mock import Mock

from autopilot import platform
from autopilot.matchers import Eventually
from autopilot.tests.functional import AutopilotRunTestBase, remove_if_exists
from autopilot._video import RMDVideoLogFixture


class AutopilotFunctionalTestsBase(AutopilotRunTestBase):

    """A collection of functional tests for autopilot."""

    def run_autopilot_list(self, list_spec='tests', extra_args=[]):
        """Run 'autopilot list' in the specified base path.

        This patches the environment to ensure that it's *this* version of
        autopilot that's run.

        returns a tuple containing: (exit_code, stdout, stderr)

        """
        args_list = ["list"] + extra_args + [list_spec]
        return self.run_autopilot(args_list)

    def assertTestsInOutput(self, tests, output, total_title='tests'):
        """Asserts that 'tests' are all present in 'output'.

        This assertion is intelligent enough to know that tests are not always
        printed in alphabetical order.

        'tests' can either be a list of test ids, or a list of tuples
        containing (scenario_count, test_id), in the case of scenarios.

        """

        if type(tests) is not list:
            raise TypeError("tests must be a list, not %r" % type(tests))
        if not isinstance(output, str):
            raise TypeError("output must be a string, not %r" % type(output))

        expected_heading = 'Loading tests from: %s\n\n' % self.base_path
        expected_tests = []
        expected_total = 0
        for test in tests:
            if type(test) == tuple:
                expected_tests.append(' *%d %s' % test)
                expected_total += test[0]
            else:
                expected_tests.append('    %s' % test)
                expected_total += 1
        expected_footer = ' %d total %s.' % (expected_total, total_title)

        parts = output.split('\n')
        observed_heading = '\n'.join(parts[:2]) + '\n'
        observed_test_list = parts[2:-4]
        observed_footer = parts[-2]

        self.assertThat(expected_heading, Equals(observed_heading))
        self.assertThat(
            sorted(expected_tests),
            Equals(sorted(observed_test_list))
        )
        self.assertThat(expected_footer, Equals(observed_footer))


class FunctionalTestMain(AutopilotFunctionalTestsBase):

    def test_config_available_in_decorator(self):
        """Any commandline config values must be available for decorators."""
        unique_config_value = self.getUniqueString()
        self.create_test_file(
            'test_config_skip.py', dedent("""\
            from testtools import skipIf
            import autopilot
            from autopilot.testcase import AutopilotTestCase

            class ConfigTest(AutopilotTestCase):
                @skipIf(
                    autopilot.get_test_configuration().get('skipme', None)
                    == '{unique_config_value}',
                    'Skipping Test')
                def test_config(self):
                    self.fail('Should not run.')
            """.format(unique_config_value=unique_config_value))
        )

        config_string = 'skipme={}'.format(unique_config_value)
        code, output, error = self.run_autopilot(
            ['run', 'tests', '--config', config_string])

        self.assertThat(code, Equals(0))

    def test_can_list_empty_test_dir(self):
        """Autopilot list must report 0 tests found with an empty test
        module."""
        code, output, error = self.run_autopilot_list()

        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertTestsInOutput([], output)

    def test_can_list_tests(self):
        """Autopilot must find tests in a file."""
        self.create_test_file(
            'test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )

        # ideally these would be different tests, but I'm lazy:
        valid_test_specs = [
            'tests',
            'tests.test_simple',
            'tests.test_simple.SimpleTest',
            'tests.test_simple.SimpleTest.test_simple',
        ]
        for test_spec in valid_test_specs:
            code, output, error = self.run_autopilot_list(test_spec)
            self.assertThat(code, Equals(0))
            self.assertThat(error, Equals(''))
            self.assertTestsInOutput(
                ['tests.test_simple.SimpleTest.test_simple'], output)

    def test_list_tests_with_import_error(self):
        self.create_test_file(
            'test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase
            # create an import error:
            import asdjkhdfjgsdhfjhsd

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )
        code, output, error = self.run_autopilot_list()
        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertThat(
            output,
            MatchesRegex(
                ".*ImportError: No module named [']?asdjkhdfjgsdhfjhsd[']?.*",
                re.DOTALL
            )
        )

    def test_list_tests_with_syntax_error(self):
        self.create_test_file(
            'test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase
            # create a syntax error:
            ..

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )
        code, output, error = self.run_autopilot_list()
        expected_error = 'SyntaxError: invalid syntax'
        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertThat(output, Contains(expected_error))

    def test_list_nonexistent_test_returns_nonzero(self):
        code, output, error = self.run_autopilot_list(list_spec='1234')
        expected_msg = "could not import package 1234: No module"
        expected_result = "0 total tests"
        self.assertThat(code, Equals(1))
        self.assertThat(output, Contains(expected_msg))
        self.assertThat(output, Contains(expected_result))

    def test_can_list_scenariod_tests(self):
        """Autopilot must show scenario counts next to tests that have
        scenarios."""
        self.create_test_file(
            'test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                scenarios = [
                    ('scenario one', {'key': 'value'}),
                    ]

                def test_simple(self):
                    pass
            """)
        )

        expected_output = '''\
Loading tests from: %s

 *1 tests.test_simple.SimpleTest.test_simple


 1 total tests.
''' % self.base_path

        code, output, error = self.run_autopilot_list()
        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertThat(output, Equals(expected_output))

    def test_can_list_scenariod_tests_with_multiple_scenarios(self):
        """Autopilot must show scenario counts next to tests that have
        scenarios.

        Tests multiple scenarios on a single test suite with multiple test
        cases.

        """
        self.create_test_file(
            'test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                scenarios = [
                    ('scenario one', {'key': 'value'}),
                    ('scenario two', {'key': 'value2'}),
                    ]

                def test_simple(self):
                    pass

                def test_simple_two(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot_list()
        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertTestsInOutput(
            [
                (2, 'tests.test_simple.SimpleTest.test_simple'),
                (2, 'tests.test_simple.SimpleTest.test_simple_two'),
            ],
            output
        )

    def test_can_list_invalid_scenarios(self):
        """Autopilot must ignore scenarios that are not lists."""
        self.create_test_file(
            'test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                scenarios = None

                def test_simple(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot_list()
        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertTestsInOutput(
            ['tests.test_simple.SimpleTest.test_simple'], output)

    def test_local_module_loaded_and_not_system_module(self):
        module_path1 = self.create_empty_test_module()
        module_path2 = self.create_empty_test_module()

        self.base_path = module_path2

        retcode, stdout, stderr = self.run_autopilot(
            ["run", "tests"],
            pythonpath=module_path1,
            use_script=True
        )

        self.assertThat(stdout, Contains(module_path2))

    def test_can_list_just_suites(self):
        """Must only list available suites, not the contained tests."""
        self.create_test_file(
            'test_simple_suites.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass

            class AnotherSimpleTest(AutopilotTestCase):

                def test_another_simple(self):
                    pass

                def test_yet_another_simple(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot_list(extra_args=['--suites'])
        self.assertThat(code, Equals(0))
        self.assertThat(error, Equals(''))
        self.assertTestsInOutput(
            ['tests.test_simple_suites.SimpleTest',
             'tests.test_simple_suites.AnotherSimpleTest'],
            output, total_title='suites')

    @skipIf(platform.model() != "Desktop", "Only suitable on Desktop (VidRec)")
    def test_record_flag_works(self):
        """Must be able to record videos when the -r flag is present."""
        video_dir = mktemp()
        ap_dir = '/tmp/autopilot'
        video_session_pattern = '/tmp/rMD-session*'
        self.addCleanup(remove_if_exists, video_dir)
        self.addCleanup(
            remove_if_exists,
            '%s/Dummy_Description.ogv' % (ap_dir)
        )
        self.addCleanup(remove_if_exists, ap_dir)

        mock_test_case = Mock()
        mock_test_case.shortDescription.return_value = 'Dummy_Description'
        orig_sessions = glob.glob(video_session_pattern)

        video_logger = RMDVideoLogFixture(video_dir, mock_test_case)
        video_logger.setUp()
        video_logger._test_passed = False

        # We use Eventually() to avoid the case where recordmydesktop does not
        # create a file because it gets stopped before it's even started
        # capturing anything.
        self.assertThat(
            lambda: glob.glob(video_session_pattern),
            Eventually(NotEquals(orig_sessions))
        )

        video_logger._stop_video_capture(mock_test_case)

        self.assertTrue(os.path.exists(video_dir))
        self.assertTrue(os.path.exists(
            '%s/Dummy_Description.ogv' % (video_dir)))
        self.assertFalse(os.path.exists(
            '%s/Dummy_Description.ogv' % (ap_dir)))

    @skipIf(platform.model() != "Desktop", "Only suitable on Desktop (VidRec)")
    def test_record_dir_option_and_record_works(self):
        """Must be able to specify record directory flag and record."""

        # The sleep is to avoid the case where recordmydesktop does not create
        # a file because it gets stopped before it's even started capturing
        # anything.
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from time import sleep


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    sleep(1)
                    self.fail()
            """)
        )
        video_dir = mktemp()
        ap_dir = '/tmp/autopilot'
        self.addCleanup(remove_if_exists, video_dir)

        should_delete = not os.path.exists(ap_dir)
        if should_delete:
            self.addCleanup(remove_if_exists, ap_dir)
        else:
            self.addCleanup(
                remove_if_exists,
                '%s/tests.test_simple.SimpleTest.test_simple.ogv' % (ap_dir))

        code, output, error = self.run_autopilot(
            ["run", "-r", "-rd", video_dir, "tests"])

        self.assertThat(code, Equals(1))
        self.assertTrue(os.path.exists(video_dir))
        self.assertTrue(os.path.exists(
            '%s/tests.test_simple.SimpleTest.test_simple.ogv' % (video_dir)))
        self.assertFalse(
            os.path.exists(
                '%s/tests.test_simple.SimpleTest.test_simple.ogv' % (ap_dir)))

    @skipIf(platform.model() != "Desktop", "Only suitable on Desktop (VidRec)")
    def test_record_dir_option_works(self):
        """Must be able to specify record directory flag."""

        # The sleep is to avoid the case where recordmydesktop does not create
        # a file because it gets stopped before it's even started capturing
        # anything.
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from time import sleep


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    sleep(1)
                    self.fail()
            """)
        )
        video_dir = mktemp()
        self.addCleanup(remove_if_exists, video_dir)

        code, output, error = self.run_autopilot(
            ["run", "-rd", video_dir, "tests"])

        self.assertThat(code, Equals(1))
        self.assertTrue(os.path.exists(video_dir))
        self.assertTrue(
            os.path.exists(
                '%s/tests.test_simple.SimpleTest.test_simple.ogv' %
                (video_dir)))

    @skipIf(platform.model() != "Desktop", "Only suitable on Desktop (VidRec)")
    def test_no_videos_saved_when_record_option_is_not_present(self):
        """Videos must not be saved if the '-r' option is not specified."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from time import sleep

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    sleep(1)
                    self.fail()
            """)
        )
        self.addCleanup(
            remove_if_exists,
            '/tmp/autopilot/tests.test_simple.SimpleTest.test_simple.ogv')

        code, output, error = self.run_autopilot(["run", "tests"])

        self.assertThat(code, Equals(1))
        self.assertFalse(os.path.exists(
            '/tmp/autopilot/tests.test_simple.SimpleTest.test_simple.ogv'))

    @skipIf(platform.model() != "Desktop", "Only suitable on Desktop (VidRec)")
    def test_no_videos_saved_for_skipped_test(self):
        """Videos must not be saved if the test has been skipped (not
        failed).

        """
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from time import sleep

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    sleep(1)
                    self.skip("Skipping Test")
            """)
        )

        video_file_path = (
            '/tmp/autopilot/tests.test_simple.SimpleTest.test_simple.ogv')
        self.addCleanup(remove_if_exists, video_file_path)

        code, output, error = self.run_autopilot(["run", "-r", "tests"])

        self.assertThat(code, Equals(0))
        self.assertThat(os.path.exists(video_file_path), Equals(False))

    @skipIf(platform.model() != "Desktop", "Only suitable on Desktop (VidRec)")
    def test_no_video_session_dir_saved_for_passed_test(self):
        """RecordMyDesktop should clean up its session files in tmp dir."""
        with TempDir() as tmp_dir_fixture:
            dir_pattern = os.path.join(tmp_dir_fixture.path, 'rMD-session*')
            original_session_dirs = set(glob.glob(dir_pattern))
            get_new_sessions = lambda: \
                set(glob.glob(dir_pattern)) - original_session_dirs
            mock_test_case = Mock()
            mock_test_case.shortDescription.return_value = "Dummy_Description"
            logger = RMDVideoLogFixture(tmp_dir_fixture.path, mock_test_case)
            logger.set_recording_dir(tmp_dir_fixture.path)
            logger._recording_opts = ['--workdir', tmp_dir_fixture.path] \
                + logger._recording_opts
            logger.setUp()
            self.assertThat(get_new_sessions, Eventually(NotEquals(set())))
            logger._stop_video_capture(mock_test_case)
        self.assertThat(get_new_sessions, Eventually(Equals(set())))

    @skipIf(platform.model() != "Desktop", "Only suitable on Desktop (VidRec)")
    def test_no_video_for_nested_testcase_when_parent_and_child_fail(self):
        """Test recording must not create a new recording for nested testcases
        where both the parent and the child testcase fail.

        """
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            import os

            class OuterTestCase(AutopilotTestCase):

                def test_nested_classes(self):
                    class InnerTestCase(AutopilotTestCase):

                        def test_will_fail(self):
                            self.assertTrue(False)

                    InnerTestCase("test_will_fail").run()
                    self.assertTrue(False)
            """)
        )

        expected_video_file = (
            '/tmp/autopilot/tests.test_simple.OuterTestCase.'
            'test_nested_classes.ogv')
        erroneous_video_file = (
            '/tmp/autopilot/tests.test_simple.OuterTestCase.'
            'test_nested_classes.InnerTestCase.test_will_fail.ogv')

        self.addCleanup(remove_if_exists, expected_video_file)
        self.addCleanup(remove_if_exists, erroneous_video_file)

        code, output, error = self.run_autopilot(["run", "-v", "-r", "tests"])

        self.assertThat(code, Equals(1))
        self.assertThat(os.path.exists(expected_video_file), Equals(True))
        self.assertThat(os.path.exists(erroneous_video_file), Equals(False))

    def test_runs_with_import_errors_fail(self):
        """Import errors inside a test must be considered a test failure."""
        self.create_test_file(
            'test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase
            # create an import error:
            import asdjkhdfjgsdhfjhsd

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot(["run", "tests"])

        self.assertThat(code, Equals(1))
        self.assertThat(error, Equals(''))
        self.assertThat(
            output,
            MatchesRegex(
                ".*ImportError: No module named [']?asdjkhdfjgsdhfjhsd[']?.*",
                re.DOTALL
            )
        )
        self.assertThat(output, Contains("FAILED (failures=1)"))

    def test_runs_with_syntax_errors_fail(self):
        """Import errors inside a test must be considered a test failure."""
        self.create_test_file(
            'test_simple.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase
            # create a syntax error:
            ..

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot(["run", "tests"])

        expected_error = '''\
tests/test_simple.py", line 4
    ..
    ^
SyntaxError: invalid syntax

'''

        self.assertThat(code, Equals(1))
        self.assertThat(error, Equals(''))
        self.assertThat(output, Contains(expected_error))
        self.assertThat(output, Contains("FAILED (failures=1)"))

    def test_can_create_subunit_result_file(self):
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass

            """)
        )
        output_file_path = mktemp()
        self.addCleanup(remove_if_exists, output_file_path)

        code, output, error = self.run_autopilot([
            "run",
            "-o", output_file_path,
            "-f", "subunit",
            "tests"])

        self.assertThat(code, Equals(0))
        self.assertTrue(os.path.exists(output_file_path))

    def test_launch_needs_arguments(self):
        """Autopilot launch must complain if not given an application to
        launch."""
        rc, _, _ = self.run_autopilot(["launch"])
        self.assertThat(rc, Equals(2))

    def test_complains_on_unknown_introspection_type(self):
        """Launching a binary that does not support an introspection type we
        are familiar with must result in a nice error message.

        """
        rc, stdout, _ = self.run_autopilot(["launch", "yes"])

        self.assertThat(rc, Equals(1))
        self.assertThat(
            stdout,
            Contains(
                "Error: Could not determine introspection type to use for "
                "application '/usr/bin/yes'"))

    def test_complains_on_missing_file(self):
        """Must give a nice error message if we try and launch a binary that's
        missing."""
        rc, stdout, _ = self.run_autopilot(["launch", "DoEsNotExist"])

        self.assertThat(rc, Equals(1))
        self.assertThat(
            stdout, Contains("Error: Cannot find application 'DoEsNotExist'"))

    def test_complains_on_non_dynamic_binary(self):
        """Must give a nice error message when passing in a non-dynamic
        binary."""
        # tzselect is a bash script, and is in the base system, so should
        # always exist.
        rc, stdout, _ = self.run_autopilot(["launch", "tzselect"])

        self.assertThat(rc, Equals(1))
        self.assertThat(
            stdout, Contains(
                "Error detecting launcher: Command '['ldd', "
                "'/usr/bin/tzselect']' returned non-zero exit status 1\n"
                "(Perhaps use the '-i' argument to specify an interface.)\n")
        )

    def test_run_random_order_flag_works(self):
        """Must run tests in random order when -ro is used"""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from time import sleep

            class SimpleTest(AutopilotTestCase):

                def test_simple_one(self):
                    pass
                def test_simple_two(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot(["run", "-ro", "tests"])

        self.assertThat(code, Equals(0))
        self.assertThat(output, Contains('Running tests in random order'))

    def test_run_random_flag_not_used(self):
        """Must not run tests in random order when -ro is not used"""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from time import sleep

            class SimpleTest(AutopilotTestCase):

                def test_simple_one(self):
                    pass
                def test_simple_two(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot(["run", "tests"])

        self.assertThat(code, Equals(0))
        self.assertThat(output, Not(Contains('Running tests in random order')))

    def test_get_test_configuration_from_command_line(self):
        self.create_test_file(
            'test_config.py', dedent("""\

                from autopilot import get_test_configuration
                from autopilot.testcase import AutopilotTestCase

                class Tests(AutopilotTestCase):

                    def test_foo(self):
                        c = get_test_configuration()
                        print(c['foo'])
            """)
        )
        code, output, error = self.run_autopilot(
            ["run", "--config", "foo=This is a test", "tests"]
        )
        self.assertThat(code, Equals(0))
        self.assertIn("This is a test", output)


class AutopilotVerboseFunctionalTests(AutopilotFunctionalTestsBase):

    """Scenarioed functional tests for autopilot's verbose logging."""

    scenarios = [
        ('text_format', dict(output_format='text')),
        ('xml_format', dict(output_format='xml'))
    ]

    def test_verbose_flag_works(self):
        """Verbose flag must log to stderr."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(code, Equals(0))
        self.assertThat(
            error, Contains(
                "Starting test tests.test_simple.SimpleTest.test_simple"))

    def test_verbose_flag_shows_timestamps(self):
        """Verbose log must include timestamps."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(error, MatchesRegex("^\d\d:\d\d:\d\d\.\d\d\d"))

    def test_verbose_flag_shows_success(self):
        """Verbose log must indicate successful tests (text format)."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(
            error, Contains("OK: tests.test_simple.SimpleTest.test_simple"))

    def test_verbose_flag_shows_error(self):
        """Verbose log must indicate test error with a traceback."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    raise RuntimeError("Intentionally fail test.")
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(
            error, Contains("ERROR: tests.test_simple.SimpleTest.test_simple"))
        self.assertThat(error, Contains("traceback:"))
        self.assertThat(
            error,
            Contains("RuntimeError: Intentionally fail test.")
        )

    def test_verbose_flag_shows_failure(self):
        """Verbose log must indicate a test failure with a traceback (xml
        format)."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    self.assertTrue(False)
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertIn("FAIL: tests.test_simple.SimpleTest.test_simple", error)
        self.assertIn("traceback:", error)
        self.assertIn("AssertionError: False is not true", error)

    def test_verbose_flag_captures_nested_autopilottestcase_classes(self):
        """Verbose log must contain the log details of both the nested and
        parent testcase."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            import os

            class OuterTestCase(AutopilotTestCase):

                def test_nested_classes(self):
                    class InnerTestCase(AutopilotTestCase):

                        def test_produce_log_output(self):
                            self.assertTrue(True)

                    InnerTestCase("test_produce_log_output").run()
                    self.assertTrue(True)
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(code, Equals(0))
        self.assertThat(
            error,
            Contains(
                "Starting test tests.test_simple.OuterTestCase."
                "test_nested_classes"
            )
        )
        self.assertThat(
            error,
            Contains(
                "Starting test tests.test_simple.InnerTestCase."
                "test_produce_log_output"
            )
        )

    def test_can_enable_debug_output(self):
        """Verbose log must show debug messages if we specify '-vv'."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from autopilot.utilities import get_debug_logger


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    get_debug_logger().debug("Hello World")
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-vv", "tests"])

        self.assertThat(error, Contains("Hello World"))

    def test_debug_output_not_shown_by_default(self):
        """Verbose log must not show debug messages unless we specify '-vv'."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase
            from autopilot.utilities import get_debug_logger


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    get_debug_logger().debug("Hello World")
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(error, Not(Contains("Hello World")))

    def test_debug_output_not_shown_by_default_normal_logger(self):
        """Verbose log must not show logger.debug level details with -v."""
        debug_string = self.getUniqueString()
        self.create_test_file(
            "test_simple.py", dedent("""\

            import logging
            from autopilot.testcase import AutopilotTestCase

            logger = logging.getLogger(__name__)

            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    logger.debug('{debug_string}')
            """.format(debug_string=debug_string))
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])

        self.assertThat(error, Not(Contains(debug_string)))

    def test_verbose_flag_shows_autopilot_version(self):
        from autopilot import get_version_string
        """Verbose log must indicate successful tests (text format)."""
        self.create_test_file(
            "test_simple.py", dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_simple(self):
                    pass
            """)
        )

        code, output, error = self.run_autopilot(["run",
                                                  "-f", self.output_format,
                                                  "-v", "tests"])
        self.assertThat(
            error, Contains(get_version_string()))

    def test_failfast(self):
        """Run stops after first error encountered."""
        self.create_test_file(
            'test_failfast.py', dedent("""\

            from autopilot.testcase import AutopilotTestCase


            class SimpleTest(AutopilotTestCase):

                def test_one(self):
                    raise Exception

                def test_two(self):
                    raise Exception
            """)
        )
        code, output, error = self.run_autopilot(["run",
                                                  "--failfast",
                                                  "tests"])
        self.assertThat(code, Equals(1))
        self.assertIn("Ran 1 test", output)
        self.assertIn("FAILED (failures=1)", output)
