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


"""Autopilot test result classes"""

import logging

from testtools import (
    ExtendedToOriginalDecorator,
    ExtendedToStreamDecorator,
    TestResultDecorator,
    TextTestResult,
    try_import,
)

from autopilot.globals import get_log_verbose
from autopilot.utilities import _raise_on_unknown_kwargs


class LoggedTestResultDecorator(TestResultDecorator):

    """A decorator that logs messages to python's logging system."""

    def _log(self, level, message):
        """Perform the actual message logging."""
        if get_log_verbose():
            logging.getLogger().log(level, message)

    def _log_details(self, level, test):
        """Log the relavent test details."""
        if hasattr(test, "getDetails"):
            details = test.getDetails()
            for detail in details:
                # Skip the test-log as it was logged while the test executed
                if detail == "test-log":
                    continue
                detail_content = details[detail]
                if detail_content.content_type.type == "text":
                    text = "%s: {{{\n%s}}}" % (
                        detail,
                        detail_content.as_text()
                    )
                else:
                    text = "Binary attachment: \"%s\" (%s)" % (
                        detail,
                        detail_content.content_type
                    )
                self._log(level, text)

    def addSuccess(self, test, details=None):
        self._log(logging.INFO, "OK: %s" % (test.id()))
        return super().addSuccess(test, details)

    def addError(self, test, err=None, details=None):
        self._log(logging.ERROR, "ERROR: %s" % (test.id()))
        self._log_details(logging.ERROR, test)
        return super().addError(test, err, details)

    def addFailure(self, test, err=None, details=None):
        """Called for a test which failed an assert."""
        self._log(logging.ERROR, "FAIL: %s" % (test.id()))
        self._log_details(logging.ERROR, test)
        return super().addFailure(test, err, details)

    def addSkip(self, test, reason=None, details=None):
        self._log(logging.INFO, "SKIP: %s" % test.id())
        return super().addSkip(test, reason, details)

    def addUnexpectedSuccess(self, test, details=None):
        self._log(logging.ERROR, "UNEXPECTED SUCCESS: %s" % test.id())
        self._log_details(logging.ERROR, test)
        return super().addUnexpectedSuccess(test, details)

    def addExpectedFailure(self, test, err=None, details=None):
        self._log(logging.INFO, "EXPECTED FAILURE: %s" % test.id())
        return super().addExpectedFailure(test, err, details)


def get_output_formats():
    """Get information regarding the different output formats supported.

    :returns: dict of supported formats and appropriate construct functions

    """
    supported_formats = {}

    supported_formats['text'] = _construct_text

    if try_import('junitxml'):
        supported_formats['xml'] = _construct_xml
    if try_import('subunit'):
        supported_formats['subunit'] = _construct_subunit
    return supported_formats


def get_default_format():
    return 'text'


def _construct_xml(**kwargs):
    from junitxml import JUnitXmlResult
    stream = kwargs.pop('stream')
    failfast = kwargs.pop('failfast')
    _raise_on_unknown_kwargs(kwargs)
    result_object = LoggedTestResultDecorator(
        ExtendedToOriginalDecorator(
            JUnitXmlResult(stream)
        )
    )
    result_object.failfast = failfast
    return result_object


def _construct_text(**kwargs):
    stream = kwargs.pop('stream')
    failfast = kwargs.pop('failfast')
    _raise_on_unknown_kwargs(kwargs)
    return LoggedTestResultDecorator(TextTestResult(stream, failfast))


def _construct_subunit(**kwargs):
    from subunit import StreamResultToBytes
    stream = kwargs.pop('stream')
    failfast = kwargs.pop('failfast')
    _raise_on_unknown_kwargs(kwargs)
    result_object = LoggedTestResultDecorator(
        ExtendedToStreamDecorator(
            StreamResultToBytes(stream)
        )
    )
    result_object.failfast = failfast
    return result_object
