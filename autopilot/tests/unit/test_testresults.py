# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2013 Canonical
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

import codecs
from unittest.mock import Mock, patch
import os
import tempfile

from fixtures import FakeLogger
from testtools import TestCase, PlaceHolder
from testtools.content import Content, ContentType, text_content
from testtools.matchers import Contains, raises, NotEquals
from testscenarios import WithScenarios
import unittest

from autopilot import testresult
from autopilot import run
from autopilot.testcase import multiply_scenarios
from autopilot.tests.unit.fixtures import AutopilotVerboseLogging


class LoggedTestResultDecoratorTests(TestCase):

    def construct_simple_content_object(self):
        return text_content(self.getUniqueString())

    def test_can_construct(self):
        testresult.LoggedTestResultDecorator(Mock())

    def test_addSuccess_calls_decorated_test(self):
        wrapped = Mock()
        result = testresult.LoggedTestResultDecorator(wrapped)
        fake_test = PlaceHolder('fake_test')
        fake_details = self.construct_simple_content_object()

        result.addSuccess(fake_test, fake_details)

        wrapped.addSuccess.assert_called_once_with(
            fake_test,
            details=fake_details
        )

    def test_addError_calls_decorated_test(self):
        wrapped = Mock()
        result = testresult.LoggedTestResultDecorator(wrapped)
        fake_test = PlaceHolder('fake_test')
        fake_error = object()
        fake_details = self.construct_simple_content_object()

        result.addError(fake_test, fake_error, fake_details)

        wrapped.addError.assert_called_once_with(
            fake_test,
            fake_error,
            details=fake_details
        )

    def test_addFailure_calls_decorated_test(self):
        wrapped = Mock()
        result = testresult.LoggedTestResultDecorator(wrapped)
        fake_test = PlaceHolder('fake_test')
        fake_error = object()
        fake_details = self.construct_simple_content_object()

        result.addFailure(fake_test, fake_error, fake_details)

        wrapped.addFailure.assert_called_once_with(
            fake_test,
            fake_error,
            details=fake_details
        )

    def test_log_details_handles_binary_data(self):
        fake_details = dict(
            TestBinary=Content(ContentType('image', 'png'), lambda: b'')
        )

        result = testresult.LoggedTestResultDecorator(None)
        result._log_details(0, fake_details)

    def test_log_details_logs_binary_attachment_details(self):
        fake_test = Mock()
        fake_test.getDetails = lambda: dict(
            TestBinary=Content(ContentType('image', 'png'), lambda: b'')
        )

        result = testresult.LoggedTestResultDecorator(None)
        with patch.object(result, '_log') as p_log:
            result._log_details(0, fake_test)

            p_log.assert_called_once_with(
                0,
                "Binary attachment: \"{name}\" ({type})".format(
                    name="TestBinary",
                    type="image/png"
                )
            )


class TestResultLogMessageTests(WithScenarios, TestCase):

    scenarios = multiply_scenarios(
        # Scenarios for each format we support:
        [(f, dict(format=f)) for f in testresult.get_output_formats().keys()],
        # Scenarios for each test outcome:
        [
            ('success', dict(outcome='addSuccess', log='OK: %s')),
            ('error', dict(outcome='addError', log='ERROR: %s')),
            ('fail', dict(outcome='addFailure', log='FAIL: %s')),
            (
                'unexpected success',
                dict(
                    outcome='addUnexpectedSuccess',
                    log='UNEXPECTED SUCCESS: %s',
                )
            ),
            ('skip', dict(outcome='addSkip', log='SKIP: %s')),
            (
                'expected failure',
                dict(
                    outcome='addExpectedFailure',
                    log='EXPECTED FAILURE: %s',
                )
            ),

        ]
    )

    def make_result_object(self):
        output_path = tempfile.mktemp()
        self.addCleanup(remove_if_exists, output_path)
        result_constructor = testresult.get_output_formats()[self.format]
        return result_constructor(
            stream=run.get_output_stream(self.format, output_path),
            failfast=False,
        )

    def test_outcome_logs(self):
        test_id = self.getUniqueString()
        test = PlaceHolder(test_id, outcome=self.outcome)
        result = self.make_result_object()
        result.startTestRun()
        self.useFixture(AutopilotVerboseLogging())
        with FakeLogger() as log:
            test.run(result)
            self.assertThat(log.output, Contains(self.log % test_id))


class OutputFormatFactoryTests(TestCase):

    def test_has_text_format(self):
        self.assertTrue('text' in testresult.get_output_formats())

    def test_has_xml_format(self):
        self.assertTrue('xml' in testresult.get_output_formats())

    def test_has_subunit_format(self):
        self.assertTrue('subunit' in testresult.get_output_formats())

    def test_default_format_is_available(self):
        self.assertThat(
            testresult.get_output_formats(),
            Contains(testresult.get_default_format())
        )


class TestResultOutputStreamTests(WithScenarios, TestCase):

    scenarios = [
        (f, dict(format=f)) for f in testresult.get_output_formats().keys()
    ]

    def get_supported_options(self, **kwargs):
        """Get a dictionary of all supported keyword arguments for the current
        result class.

        Pass in keyword arguments to override default options.
        """
        output_path = tempfile.mktemp()
        self.addCleanup(remove_if_exists, output_path)
        options = {
            'stream': run.get_output_stream(self.format, output_path),
            'failfast': False
        }
        options.update(kwargs)
        return options

    def run_test_with_result(self, test_suite, **kwargs):
        """Run the given test with the current result object.

        Returns the test result and output file path.
        Use keyword arguments to alter result object options.

        """
        ResultClass = testresult.get_output_formats()[self.format]
        result_options = self.get_supported_options(**kwargs)
        output_path = result_options['stream'].name
        result = ResultClass(**result_options)
        result.startTestRun()
        test_result = test_suite.run(result)
        result.stopTestRun()
        result_options['stream'].flush()
        return test_result, output_path

    def test_factory_function_is_a_callable(self):
        self.assertTrue(
            callable(testresult.get_output_formats()[self.format])
        )

    def test_factory_callable_raises_on_unknown_kwargs(self):
        factory_fn = testresult.get_output_formats()[self.format]
        options = self.get_supported_options()
        options['unknown_kwarg'] = True

        self.assertThat(
            lambda: factory_fn(**options),
            raises(ValueError)
        )

    def test_creates_non_empty_file_on_passing_test(self):
        class PassingTests(TestCase):

            def test_passes(self):
                pass

        test_result, output_path = self.run_test_with_result(
            PassingTests('test_passes')
        )
        self.assertTrue(test_result.wasSuccessful())
        self.assertThat(open(output_path, 'rb').read(), NotEquals(b''))

    def test_creates_non_empty_file_on_failing_test(self):
        class FailingTests(TestCase):

            def test_fails(self):
                self.fail("Failing Test: ")

        test_result, output_path = self.run_test_with_result(
            FailingTests('test_fails')
        )
        self.assertFalse(test_result.wasSuccessful())
        self.assertThat(open(output_path, 'rb').read(), NotEquals(b''))

    def test_creates_non_empty_file_on_erroring_test(self):
        class ErroringTests(TestCase):

            def test_errors(self):
                raise RuntimeError("Uncaught Exception!")

        test_result, output_path = self.run_test_with_result(
            ErroringTests('test_errors')
        )
        self.assertFalse(test_result.wasSuccessful())
        self.assertThat(open(output_path, 'rb').read(), NotEquals(b''))

    def test_creates_non_empty_log_file_when_failing_with_unicode(self):
        class FailingTests(TestCase):

            def test_fails_unicode(self):
                self.fail(
                    '\xa1pl\u0279oM \u01ddpo\u0254\u0131u\u2229 oll\u01ddH'
                )
        test_result, output_path = self.run_test_with_result(
            FailingTests('test_fails_unicode')
        )
        # We need to specify 'errors="ignore"' because subunit write non-valid
        # unicode data.
        log_contents = codecs.open(
            output_path,
            'r',
            encoding='utf-8',
            errors='ignore'
        ).read()
        self.assertFalse(test_result.wasSuccessful())
        self.assertThat(
            log_contents,
            Contains('\xa1pl\u0279oM \u01ddpo\u0254\u0131u\u2229 oll\u01ddH')
        )

    def test_result_object_supports_many_tests(self):
        class ManyFailingTests(TestCase):

            def test_fail1(self):
                self.fail("Failing test")

            def test_fail2(self):
                self.fail("Failing test")
        suite = unittest.TestSuite(
            tests=(
                ManyFailingTests('test_fail1'),
                ManyFailingTests('test_fail2'),
            )
        )
        test_result, output_path = self.run_test_with_result(suite)
        self.assertFalse(test_result.wasSuccessful())
        self.assertEqual(2, test_result.testsRun)

    def test_result_object_supports_failfast(self):
        class ManyFailingTests(TestCase):

            def test_fail1(self):
                self.fail("Failing test")

            def test_fail2(self):
                self.fail("Failing test")
        suite = unittest.TestSuite(
            tests=(
                ManyFailingTests('test_fail1'),
                ManyFailingTests('test_fail2'),
            )
        )
        test_result, output_path = self.run_test_with_result(
            suite,
            failfast=True
        )
        self.assertFalse(test_result.wasSuccessful())
        self.assertEqual(1, test_result.testsRun)


def remove_if_exists(path):
    if os.path.exists(path):
        os.remove(path)
