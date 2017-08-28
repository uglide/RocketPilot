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

from unittest.mock import Mock, patch
import re
from testtools import TestCase
from testtools.content import Content
from testtools.matchers import (
    Equals,
    IsInstance,
    LessThan,
    MatchesRegex,
    Not,
    raises,
    Raises,
)
import timeit

from autopilot.utilities import (
    _raise_if_time_delta_not_sane,
    _raise_on_unknown_kwargs,
    _sleep_for_calculated_delta,
    cached_result,
    compatible_repr,
    deprecated,
    EventDelay,
    safe_text_content,
    sleep,
)


class ElapsedTimeCounter(object):

    """A simple utility to count the amount of real time that passes."""

    def __enter__(self):
        self._start_time = timeit.default_timer()
        return self

    def __exit__(self, *args):
        pass

    @property
    def elapsed_time(self):
        return timeit.default_timer() - self._start_time


class MockableSleepTests(TestCase):

    def test_mocked_sleep_contextmanager(self):
        with ElapsedTimeCounter() as time_counter:
            with sleep.mocked():
                sleep(10)
            self.assertThat(time_counter.elapsed_time, LessThan(2))

    def test_mocked_sleep_methods(self):
        with ElapsedTimeCounter() as time_counter:
            sleep.enable_mock()
            self.addCleanup(sleep.disable_mock)

            sleep(10)
            self.assertThat(time_counter.elapsed_time, LessThan(2))

    def test_total_time_slept_starts_at_zero(self):
        with sleep.mocked() as sleep_counter:
            self.assertThat(sleep_counter.total_time_slept(), Equals(0.0))

    def test_total_time_slept_accumulates(self):
        with sleep.mocked() as sleep_counter:
            sleep(1)
            self.assertThat(sleep_counter.total_time_slept(), Equals(1.0))
            sleep(0.5)
            self.assertThat(sleep_counter.total_time_slept(), Equals(1.5))
            sleep(0.5)
            self.assertThat(sleep_counter.total_time_slept(), Equals(2.0))

    def test_unmocked_sleep_calls_real_time_sleep_function(self):
        with patch('autopilot.utilities.time') as patched_time:
            sleep(1.0)

            patched_time.sleep.assert_called_once_with(1.0)


class EventDelayTests(TestCase):

    def test_mocked_event_delayer_contextmanager(self):
        event_delayer = EventDelay()
        with event_delayer.mocked():
            # The first call of delay() only stores the last time
            # stamp, it is only the second call where the delay
            # actually happens. So we call delay() twice here to
            # ensure mocking is working as expected.
            event_delayer.delay(duration=0)
            event_delayer.delay(duration=3)
            self.assertAlmostEqual(sleep.total_time_slept(), 3, places=1)

    def test_last_event_start_at_zero(self):
        event_delayer = EventDelay()
        self.assertThat(event_delayer.last_event_time(), Equals(0.0))

    def test_last_event_delay_counter_updates_on_first_call(self):
        event_delayer = EventDelay()
        event_delayer.delay(duration=1.0, current_time=lambda: 10)

        self.assertThat(event_delayer._last_event, Equals(10.0))

    def test_first_call_to_delay_causes_no_sleep(self):
        event_delayer = EventDelay()
        with sleep.mocked() as mocked_sleep:
            event_delayer.delay(duration=0.0)
            self.assertThat(mocked_sleep.total_time_slept(), Equals(0.0))

    def test_second_call_to_delay_causes_sleep(self):
        event_delayer = EventDelay()
        with sleep.mocked() as mocked_sleep:
            event_delayer.delay(duration=0, current_time=lambda: 100)
            event_delayer.delay(duration=10, current_time=lambda: 105)
            self.assertThat(mocked_sleep.total_time_slept(), Equals(5.0))

    def test_no_delay_if_time_jumps_since_last_event(self):
        event_delayer = EventDelay()
        with sleep.mocked() as mocked_sleep:
            event_delayer.delay(duration=2, current_time=lambda: 100)
            event_delayer.delay(duration=2, current_time=lambda: 110)
            self.assertThat(mocked_sleep.total_time_slept(), Equals(0.0))

    def test_no_delay_if_given_delay_time_negative(self):
        event_delayer = EventDelay()
        with sleep.mocked() as mocked_sleep:
            event_delayer.delay(duration=-2, current_time=lambda: 100)
            event_delayer.delay(duration=-2, current_time=lambda: 101)
            self.assertThat(mocked_sleep.total_time_slept(), Equals(0.0))

    def test_sleep_delta_calculator_returns_zero_if_time_delta_negative(self):
        result = _sleep_for_calculated_delta(100, 97, 2)
        self.assertThat(result, Equals(0.0))

    def test_sleep_delta_calculator_doesnt_sleep_if_time_delta_negative(self):
        with sleep.mocked() as mocked_sleep:
            _sleep_for_calculated_delta(100, 97, 2)
            self.assertThat(mocked_sleep.total_time_slept(), Equals(0.0))

    def test_sleep_delta_calculator_returns_zero_if_time_delta_zero(self):
        result = _sleep_for_calculated_delta(100, 98, 2)
        self.assertThat(result, Equals(0.0))

    def test_sleep_delta_calculator_doesnt_sleep_if_time_delta_zero(self):
        with sleep.mocked() as mocked_sleep:
            _sleep_for_calculated_delta(100, 98, 2)
            self.assertThat(mocked_sleep.total_time_slept(), Equals(0.0))

    def test_sleep_delta_calculator_returns_non_zero_if_delta_not_zero(self):
        with sleep.mocked():
            result = _sleep_for_calculated_delta(101, 100, 2)
            self.assertThat(result, Equals(1.0))

    def test_sleep_delta_calc_returns_zero_if_gap_duration_negative(self):
        result = _sleep_for_calculated_delta(100, 99, -2)
        self.assertEquals(result, 0.0)

    def test_sleep_delta_calc_raises_if_last_event_ahead_current_time(self):
        self.assertRaises(
            ValueError,
            _sleep_for_calculated_delta,
            current_time=100,
            last_event_time=110,
            gap_duration=2
        )

    def test_sleep_delta_calc_raises_if_last_event_equals_current_time(self):
        self.assertRaises(
            ValueError,
            _sleep_for_calculated_delta,
            current_time=100,
            last_event_time=100,
            gap_duration=2
        )

    def test_sleep_delta_calc_raises_if_current_time_negative(self):
        self.assertRaises(
            ValueError,
            _sleep_for_calculated_delta,
            current_time=-100,
            last_event_time=10,
            gap_duration=10
        )

    def test_time_sanity_checker_raises_if_time_smaller_than_last_event(self):
        self.assertRaises(
            ValueError,
            _raise_if_time_delta_not_sane,
            current_time=90,
            last_event_time=100
        )

    def test_time_sanity_checker_raises_if_time_equal_last_event_time(self):
        self.assertRaises(
            ValueError,
            _raise_if_time_delta_not_sane,
            current_time=100,
            last_event_time=100
        )

    def test_time_sanity_checker_raises_if_time_negative_last_event_not(self):
        self.assertRaises(
            ValueError,
            _raise_if_time_delta_not_sane,
            current_time=-100,
            last_event_time=100
        )


class CompatibleReprTests(TestCase):

    def test_py3_unicode_is_untouched(self):
        repr_fn = compatible_repr(lambda: "unicode")
        result = repr_fn()
        self.assertThat(result, IsInstance(str))
        self.assertThat(result, Equals('unicode'))

    def test_py3_bytes_are_returned_as_unicode(self):
        repr_fn = compatible_repr(lambda: b"bytes")
        result = repr_fn()
        self.assertThat(result, IsInstance(str))
        self.assertThat(result, Equals('bytes'))


class UnknownKWArgsTests(TestCase):

    def test_raise_if_not_empty_raises_on_nonempty_dict(self):
        populated_dict = dict(testing=True)
        self.assertThat(
            lambda: _raise_on_unknown_kwargs(populated_dict),
            raises(ValueError("Unknown keyword arguments: 'testing'."))
        )

    def test_raise_if_not_empty_does_not_raise_on_empty(self):
        empty_dict = dict()
        self.assertThat(
            lambda: _raise_on_unknown_kwargs(empty_dict),
            Not(Raises())
        )


class DeprecatedDecoratorTests(TestCase):

    def test_deprecated_logs_warning(self):

        @deprecated('Testing')
        def not_testing():
            pass

        with patch('autopilot.utilities.logger') as patched_log:
            not_testing()

            self.assertThat(
                patched_log.warning.call_args[0][0],
                MatchesRegex(
                    "WARNING: in file \".*.py\", line \d+ in "
                    "test_deprecated_logs_warning\nThis "
                    "function is deprecated. Please use 'Testing' instead.\n",
                    re.DOTALL
                )
            )


class CachedResultTests(TestCase):

    def get_wrapped_mock_pair(self):
        inner = Mock()
        # Mock() under python 2 does not support __name__. When we drop py2
        # support we can obviously delete this hack:
        return inner, cached_result(inner)

    def test_can_be_used_as_decorator(self):
        @cached_result
        def foo():
            pass

    def test_adds_reset_cache_callable_to_function(self):
        @cached_result
        def foo():
            pass

        self.assertTrue(hasattr(foo, 'reset_cache'))

    def test_retains_docstring(self):
        @cached_result
        def foo():
            """xxXX super docstring XXxx"""
            pass

        self.assertThat(foo.__doc__, Equals("xxXX super docstring XXxx"))

    def test_call_passes_through_once(self):
        inner, wrapped = self.get_wrapped_mock_pair()
        wrapped()
        inner.assert_called_once_with()

    def test_call_passes_through_only_once(self):
        inner, wrapped = self.get_wrapped_mock_pair()
        wrapped()
        wrapped()
        inner.assert_called_once_with()

    def test_first_call_returns_actual_result(self):
        inner, wrapped = self.get_wrapped_mock_pair()
        self.assertThat(
            wrapped(),
            Equals(inner.return_value)
        )

    def test_subsequent_calls_return_actual_results(self):
        inner, wrapped = self.get_wrapped_mock_pair()
        wrapped()
        self.assertThat(
            wrapped(),
            Equals(inner.return_value)
        )

    def test_can_pass_hashable_arguments(self):
        inner, wrapped = self.get_wrapped_mock_pair()
        wrapped(1, True, 2.0, "Hello", tuple(), )
        inner.assert_called_once_with(1, True, 2.0, "Hello", tuple())

    def test_passing_kwargs_raises_TypeError(self):
        inner, wrapped = self.get_wrapped_mock_pair()
        self.assertThat(
            lambda: wrapped(foo='bar'),
            raises(TypeError)
        )

    def test_passing_unhashable_args_raises_TypeError(self):
        inner, wrapped = self.get_wrapped_mock_pair()
        self.assertThat(
            lambda: wrapped([]),
            raises(TypeError)
        )

    def test_resetting_cache_works(self):
        inner, wrapped = self.get_wrapped_mock_pair()
        wrapped()
        wrapped.reset_cache()
        wrapped()
        self.assertThat(inner.call_count, Equals(2))


class SafeTextContentTests(TestCase):

    def test_raises_TypeError_on_non_texttype(self):
        self.assertThat(
            lambda: safe_text_content(None),
            raises(TypeError)
        )

    def test_returns_text_content_object(self):
        example_string = self.getUniqueString()
        content_obj = safe_text_content(example_string)
        self.assertTrue(isinstance(content_obj, Content))
