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


from testtools import TestCase
from testtools.matchers import Equals, Contains
from unittest.mock import patch, Mock

from autopilot.utilities import (
    CleanupRegistered,
    _cleanup_objects,
    action_on_test_start,
    action_on_test_end,
)
from autopilot.utilities import on_test_started


class StartFinalExecutionTests(TestCase):

    def test_conformant_class_is_added(self):
        class Conformant(CleanupRegistered):
            pass

        self.assertThat(_cleanup_objects, Contains(Conformant))

    def test_on_test_start_and_end_methods_called(self):
        class Conformant(CleanupRegistered):
            """This class defines the classmethods to be called at test
            start/end.

            """

            _on_start_test = False
            _on_end_test = False

            @classmethod
            def on_test_start(cls, test_instance):
                cls._on_start_test = True

            @classmethod
            def on_test_end(cls, test_instance):
                cls._on_end_test = True

        class InnerTest(TestCase):
            def setUp(self):
                super().setUp()
                on_test_started(self)

            def test_foo(self):
                pass

        test_run = InnerTest('test_foo').run()

        InnerTest('test_foo').run()
        self.assertThat(test_run.wasSuccessful(), Equals(True))
        self.assertThat(Conformant._on_start_test, Equals(True))
        self.assertThat(Conformant._on_end_test, Equals(True))

    def test_action_on_test_start_reports_raised_exception(self):
        """Any Exceptions raised during action_on_test_start must be caught and
        reported.

        """
        class Cleanup(object):

            def on_test_start(self, test_instance):
                raise IndexError

        obj = Cleanup()
        mockTestCase = Mock(spec=TestCase)

        with patch('autopilot.utilities._cleanup_objects', new=[obj]):
            action_on_test_start(mockTestCase)

        self.assertThat(mockTestCase._report_traceback.call_count, Equals(1))

    def test_action_on_test_end_reports_raised_exception(self):
        """Any Exceptions raised during action_on_test_end must be caught and
        reported.

        """

        class Cleanup(object):

            def on_test_end(self, test_instance):
                raise IndexError

        obj = Cleanup()
        mockTestCase = Mock(spec=TestCase)

        with patch('autopilot.utilities._cleanup_objects', new=[obj]):
            action_on_test_end(mockTestCase)

        self.assertThat(mockTestCase._report_traceback.call_count, Equals(1))
