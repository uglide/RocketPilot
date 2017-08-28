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

import logging

from unittest.mock import Mock
import testtools

from autopilot import tests
from autopilot.logging import log_action
from autopilot._logging import TestCaseLoggingFixture


class ObjectWithLogDecorator(object):

    @log_action(logging.info)
    def do_something_without_docstring(self, *args, **kwargs):
        pass

    @log_action(logging.info)
    def do_something_with_docstring(self, *args, **kwargs):
        """Do something with docstring."""
        pass

    @log_action(logging.info)
    def do_something_with_multiline_docstring(self, *args, **kwargs):
        """Do something with a multiline docstring.

        This should not be logged.
        """
        pass


class LoggingTestCase(tests.LogHandlerTestCase):

    def setUp(self):
        super(LoggingTestCase, self).setUp()
        self.root_logger.setLevel(logging.INFO)
        self.logged_object = ObjectWithLogDecorator()

    def test_logged_action_without_docstring(self):
        self.logged_object.do_something_without_docstring(
            'arg1', 'arg2', arg3='arg3', arg4='arg4')
        self.assertLogLevelContains(
            'INFO',
            "ObjectWithLogDecorator: do_something_without_docstring. "
            "Arguments ('arg1', 'arg2'). "
            "Keyword arguments: {'arg3': 'arg3', 'arg4': 'arg4'}.")

    def test_logged_action_with_docstring(self):
        self.logged_object.do_something_with_docstring(
            'arg1', 'arg2', arg3='arg3', arg4='arg4')
        self.assertLogLevelContains(
            'INFO',
            "ObjectWithLogDecorator: Do something with docstring. "
            "Arguments ('arg1', 'arg2'). "
            "Keyword arguments: {'arg3': 'arg3', 'arg4': 'arg4'}.")

    def test_logged_action_with_multiline_docstring(self):
        self.logged_object.do_something_with_multiline_docstring(
            'arg1', 'arg2', arg3='arg3', arg4='arg4')
        self.assertLogLevelContains(
            'INFO',
            "ObjectWithLogDecorator: "
            "Do something with a multiline docstring. "
            "Arguments ('arg1', 'arg2'). "
            "Keyword arguments: {'arg3': 'arg3', 'arg4': 'arg4'}.")


class TestCaseLoggingFixtureTests(testtools.TestCase):

    def test_test_log_is_added(self):
        token = self.getUniqueString()
        add_detail_fn = Mock()
        fixture = TestCaseLoggingFixture("Test.id", add_detail_fn)
        fixture.setUp()
        logging.getLogger(__name__).info(token)
        fixture.cleanUp()

        self.assertEqual(1, add_detail_fn.call_count)
        self.assertEqual('test-log', add_detail_fn.call_args[0][0])
        self.assertIn(token, add_detail_fn.call_args[0][1].as_text())
