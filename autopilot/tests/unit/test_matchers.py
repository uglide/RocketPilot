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


from contextlib import contextmanager
import dbus
from testscenarios import TestWithScenarios
from testtools import TestCase
from testtools.matchers import (
    Contains,
    Equals,
    Is,
    IsInstance,
    Mismatch,
    raises,
)

from autopilot.introspection import backends
from autopilot.introspection.dbus import DBusIntrospectionObject
from autopilot.introspection.types import Color, ValueType
from autopilot.matchers import Eventually
from autopilot.utilities import sleep


def make_fake_attribute_with_result(result, attribute_type='wait_for',
                                    typeid=None):
    """Make a fake attribute with the given result.

    This will either return a callable, or an attribute patched with a
    wait_for method, according to the current test scenario.

    """
    class FakeObject(DBusIntrospectionObject):
        def __init__(self, props):
            super(FakeObject, self).__init__(
                props,
                b"/FakeObject",
                backends.FakeBackend(
                    [(dbus.String('/FakeObject'), props)]
                )
            )

    if attribute_type == 'callable':
        return lambda: result
    elif attribute_type == 'wait_for':
        if isinstance(result, str):
            obj = FakeObject(dict(id=[0, 123], attr=[0, dbus.String(result)]))
            return obj.attr
        elif isinstance(result, bytes):
            obj = FakeObject(
                dict(id=[0, 123], attr=[0, dbus.UTF8String(result)])
            )
            return obj.attr
        elif typeid is not None:
            obj = FakeObject(dict(id=[0, 123], attr=[typeid] + result))
            return obj.attr
        else:
            obj = FakeObject(dict(id=[0, 123], attr=[0, dbus.Boolean(result)]))
            return obj.attr


class ObjectPatchingMatcherTests(TestCase):
    """Ensure the core functionality the matchers use is correct."""

    def test_default_wait_for_args(self):
        """Ensure we can call wait_for with the correct arg."""
        intro_obj = make_fake_attribute_with_result(False)
        intro_obj.wait_for(False)


class MockedSleepTests(TestCase):

    def setUp(self):
        super(MockedSleepTests, self).setUp()
        sleep.enable_mock()
        self.addCleanup(sleep.disable_mock)

    @contextmanager
    def expected_runtime(self, tmin, tmax):
        try:
            yield
        finally:
            elapsed_time = sleep.total_time_slept()
            if not tmin <= elapsed_time <= tmax:
                raise AssertionError(
                    "Runtime of %f is not between %f and %f"
                    % (elapsed_time, tmin, tmax))


class EventuallyMatcherTests(TestWithScenarios, MockedSleepTests):

    scenarios = [
        ('callable', dict(attribute_type='callable')),
        ('wait_for', dict(attribute_type='wait_for')),
    ]

    def test_eventually_matcher_returns_mismatch(self):
        """Eventually matcher must return a Mismatch."""
        attr = make_fake_attribute_with_result(False, self.attribute_type)
        e = Eventually(Equals(True)).match(attr)

        self.assertThat(e, IsInstance(Mismatch))

    def test_eventually_default_timeout(self):
        """Eventually matcher must default to 10 second timeout."""
        attr = make_fake_attribute_with_result(False, self.attribute_type)
        with self.expected_runtime(9.5, 11.0):
            Eventually(Equals(True)).match(attr)

    def test_eventually_passes_immeadiately(self):
        """Eventually matcher must not wait if the assertion passes
        initially."""
        attr = make_fake_attribute_with_result(True, self.attribute_type)
        with self.expected_runtime(0.0, 1.0):
            Eventually(Equals(True)).match(attr)

    def test_eventually_matcher_allows_non_default_timeout(self):
        """Eventually matcher must allow a non-default timeout value."""
        attr = make_fake_attribute_with_result(False, self.attribute_type)
        with self.expected_runtime(4.5, 6.0):
            Eventually(Equals(True), timeout=5).match(attr)

    def test_mismatch_message_has_correct_timeout_value(self):
        """The mismatch value must have the correct timeout value in it."""
        attr = make_fake_attribute_with_result(False, self.attribute_type)
        mismatch = Eventually(Equals(True), timeout=1).match(attr)
        self.assertThat(
            mismatch.describe(), Contains("After 1.0 seconds test"))

    def test_eventually_matcher_works_with_list_type(self):
        attr = make_fake_attribute_with_result(
            Color(
                dbus.Int32(1),
                dbus.Int32(2),
                dbus.Int32(3),
                dbus.Int32(4)
            ),
            self.attribute_type,
            typeid=ValueType.COLOR,
        )

        mismatch = Eventually(Equals([1, 2, 3, 4])).match(attr)
        self.assertThat(mismatch, Is(None))


class EventuallyNonScenariodTests(MockedSleepTests):

    def test_eventually_matcher_raises_ValueError_on_unknown_kwargs(self):
        self.assertThat(
            lambda: Eventually(Equals(True), foo=123),
            raises(ValueError("Unknown keyword arguments: foo"))
        )

    def test_eventually_matcher_raises_TypeError_on_non_matcher_argument(self):
        self.assertThat(
            lambda: Eventually(None),
            raises(
                TypeError(
                    "Eventually must be called with a testtools "
                    "matcher argument."
                )
            )
        )

    def test_match_raises_TypeError_when_called_with_plain_attribute(self):
        eventually = Eventually(Equals(True))
        self.assertThat(
            lambda: eventually.match(False),
            raises(
                TypeError(
                    "Eventually is only usable with attributes that "
                    "have a wait_for function or callable objects."
                )
            )
        )

    def test_repr(self):
        eventually = Eventually(Equals(True))
        self.assertEqual("Eventually Equals(True)", str(eventually))

    def test_match_with_expected_value_unicode(self):
        """The expected unicode value matches new value string."""
        attr = make_fake_attribute_with_result(
            '\u963f\u5e03\u4ece', 'wait_for')
        with self.expected_runtime(0.0, 1.0):
            Eventually(Equals("阿布从")).match(attr)

    def test_match_with_new_value_unicode(self):
        """new value with unicode must match expected value string."""
        attr = make_fake_attribute_with_result(str("阿布从"), 'wait_for')
        with self.expected_runtime(0.0, 1.0):
            Eventually(Equals('\u963f\u5e03\u4ece')).match(attr)

    def test_mismatch_with_bool(self):
        """The mismatch value must fail boolean values."""
        attr = make_fake_attribute_with_result(False, 'wait_for')
        mismatch = Eventually(Equals(True), timeout=1).match(attr)
        self.assertThat(
            mismatch.describe(), Contains("failed"))

    def test_mismatch_with_unicode(self):
        """The mismatch value must fail with str and unicode mix."""
        attr = make_fake_attribute_with_result(str("阿布从1"), 'wait_for')
        mismatch = Eventually(Equals(
            '\u963f\u5e03\u4ece'), timeout=.5).match(attr)
        self.assertThat(
            mismatch.describe(), Contains('failed'))

    def test_mismatch_output_utf8(self):
        """The mismatch has utf output."""
        self.skip("mismatch Contains returns ascii error")
        attr = make_fake_attribute_with_result(str("阿布从1"), 'wait_for')
        mismatch = Eventually(Equals(
            '\u963f\u5e03\u4ece'), timeout=.5).match(attr)
        self.assertThat(
            mismatch.describe(), Contains("阿布从11"))
