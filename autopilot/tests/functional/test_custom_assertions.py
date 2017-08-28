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


from autopilot.testcase import AutopilotTestCase
from testtools.matchers import Equals, raises, Not

import logging
logger = logging.getLogger(__name__)


class TestObject(object):

    test_property = 123

    another_property = "foobar"

    none_prop = None

    def test_method(self):
        return 456


class AssertionTests(AutopilotTestCase):

    test_object = TestObject()

    def test_assertProperty_raises_valueerror_on_empty_test(self):
        """assertProperty must raise ValueError if called without any
        kwargs."""

        self.assertThat(
            lambda: self.assertProperty(self.test_object), raises(ValueError))

    def test_assertProperty_raises_valueerror_on_callable(self):
        """assertProperty must raise ValueError when called with a callable
        property name.

        """

        self.assertThat(
            lambda: self.assertProperty(self.test_object, test_method=456),
            raises(ValueError))

    def test_assertProperty_raises_assert_with_single_property(self):
        """assertProperty must raise an AssertionError when called with a
        single property.

        """
        self.assertThat(
            lambda: self.assertProperty(self.test_object, test_property=234),
            raises(AssertionError))

    def test_assertProperty_doesnt_raise(self):
        """assertProperty must not raise an exception if called with correct
        parameters.

        """

        self.assertThat(
            lambda: self.assertProperty(self.test_object, test_property=123),
            Not(raises(AssertionError)))

    def test_assertProperty_doesnt_raise_multiples(self):
        """assertProperty must not raise an exception if called with correct
        parameters.

        """

        self.assertThat(
            lambda: self.assertProperty(
                self.test_object, test_property=123,
                another_property="foobar"),
            Not(raises(AssertionError)))

    def test_assertProperty_raises_assert_with_double_properties(self):
        """assertProperty must raise an AssertionError when called with
        multiple properties.

        """
        self.assertThat(
            lambda: self.assertProperty(
                self.test_object, test_property=234, another_property=123),
            raises(AssertionError))

    def test_assertProperties_works(self):
        """Asserts that the assertProperties method is a synonym for
        assertProperty."""
        self.assertThat(callable(self.assertProperties), Equals(True))
        self.assertThat(
            lambda: self.assertProperties(
                self.test_object, test_property=123,
                another_property="foobar"),
            Not(raises(AssertionError)))

    def test_assertProperty_raises_assertionerror_on_no_such_property(self):
        """AssertProperty must rise an AssertionError if the property is not
        found."""
        self.assertThat(
            lambda: self.assertProperty(self.test_object, foo="bar"),
            raises(AssertionError))

    def test_assertProperty_works_for_None_properties(self):
        """Must be able to match properties whose values are None."""
        self.assertThat(
            lambda: self.assertProperties(self.test_object, none_prop=None),
            Not(raises(AssertionError)))
