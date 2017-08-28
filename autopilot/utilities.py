# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
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


"""Various utility classes and functions that are useful when running tests."""

from contextlib import contextmanager
from decorator import decorator
import functools
import inspect
import logging
import os
import psutil
import time
import timeit
from testtools.content import text_content
from unittest.mock import Mock
from functools import wraps

from autopilot.exceptions import BackendException


logger = logging.getLogger(__name__)


def safe_text_content(text):
    """Return testtools.content.Content object.

    Safe in the sense that it will catch any attempt to attach NoneType
    objects.

    :raises ValueError: If `text` is not a text-type object.

    """
    if not isinstance(text, str):
        raise TypeError(
            'text argument must be string not {}'.format(
                type(text).__name__
            )
        )

    return text_content(text)


def _pick_backend(backends, preferred_backend):
    """Pick a backend and return an instance of it."""
    possible_backends = list(backends.keys())
    get_debug_logger().debug(
        "Possible backends: %s", ','.join(possible_backends))
    if preferred_backend:
        if preferred_backend in possible_backends:
            # make preferred_backend the first list item
            possible_backends.remove(preferred_backend)
            possible_backends.insert(0, preferred_backend)
        else:
            raise RuntimeError("Unknown backend '%s'" % (preferred_backend))
    failure_reasons = []
    for be in possible_backends:
        try:
            return backends[be]()
        except Exception as e:
            get_debug_logger().warning("Can't create backend %s: %r", be, e)
            failure_reasons.append('%s: %r' % (be, e))
            if preferred_backend != '':
                raise BackendException(e)
    raise RuntimeError(
        "Unable to instantiate any backends\n%s" % '\n'.join(failure_reasons))


# Taken from http://ur1.ca/eqapv
# licensed under the MIT license.
class Silence(object):

    """Context manager which uses low-level file descriptors to suppress
    output to stdout/stderr, optionally redirecting to the named file(s).

    Example::

        with Silence():
            # do something that prints to stdout or stderr

    """

    def __init__(self, stdout=os.devnull, stderr=os.devnull, mode='wb'):
        self.outfiles = stdout, stderr
        self.combine = (stdout == stderr)
        self.mode = mode

    def __enter__(self):
        import sys
        self.sys = sys
        # save previous stdout/stderr
        self.saved_streams = saved_streams = sys.__stdout__, sys.__stderr__
        self.fds = fds = [s.fileno() for s in saved_streams]
        self.saved_fds = map(os.dup, fds)
        # flush any pending output
        for s in saved_streams:
            s.flush()

        # open surrogate files
        if self.combine:
            null_streams = [open(self.outfiles[0], self.mode, 0)] * 2
            if self.outfiles[0] != os.devnull:
                # disable buffering so output is merged immediately
                sys.stdout, sys.stderr = map(os.fdopen, fds, ['w']*2, [0]*2)
        else:
            null_streams = [open(f, self.mode, 0) for f in self.outfiles]
        self.null_fds = null_fds = [s.fileno() for s in null_streams]
        self.null_streams = null_streams

        # overwrite file objects and low-level file descriptors
        map(os.dup2, null_fds, fds)

    def __exit__(self, *args):
        sys = self.sys
        # flush any pending output
        for s in self.saved_streams:
            s.flush()
        # restore original streams and file descriptors
        map(os.dup2, self.saved_fds, self.fds)
        sys.stdout, sys.stderr = self.saved_streams
        # clean up
        for s in self.null_streams:
            s.close()
        for fd in self.saved_fds:
            os.close(fd)
        return False


class LogFormatter(logging.Formatter):

    # this is the default format to use for logging
    log_format = (
        "%(asctime)s %(levelname)s %(module)s:%(lineno)d - %(message)s")

    def __init__(self):
        super(LogFormatter, self).__init__(self.log_format)

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            t = time.strftime("%H:%M:%S", ct)
            s = "%s.%03d" % (t, record.msecs)
        return s


class Timer(object):

    """A context-manager that times a block of code, writing the results to
    the log."""

    def __init__(self, code_name, log_level=logging.DEBUG):
        self.code_name = code_name
        self.log_level = log_level
        self.start = 0
        self.logger = get_debug_logger()

    def __enter__(self):
        self.start = timeit.default_timer()

    def __exit__(self, *args):
        self.end = timeit.default_timer()
        elapsed = self.end - self.start
        self.logger.log(
            self.log_level, "'%s' took %.3fs", self.code_name, elapsed)


class StagnantStateDetector(object):

    """Detect when the state of something doesn't change over many iterations.


    Example of use::

        state_check = StagnantStateDetector(threshold=5)
        x, y = get_current_position()
        while not at_position(target_x, target_y):
            move_toward_position(target_x, target_y)
            x, y = get_current_position()
            try:
                # this will raise an exception after the current position
                # hasn't changed on the 6th time the check is performed.
                loop_detector.check_state(x, y)
            except StagnantStateDetector.StagnantState as e:
                e.args = ("Position has not moved.", )
                raise
    """

    class StagnantState(Exception):
        pass

    def __init__(self, threshold):
        """
        :param threshold: Amount of times the updated state can fail to
          differ consecutively before raising an exception.

        :raises ValueError: if *threshold* isn't a positive integer.

        """
        if type(threshold) is not int or threshold <= 0:
            raise ValueError("Threshold must be a positive integer.")
        self._threshold = threshold
        self._stagnant_count = 0
        self._previous_state_hash = -1

    def check_state(self, *state):
        """Check if there is a difference between the previous state and
        state.

        :param state: Hashable state argument to compare against the previous
          iteration

        :raises TypeError: when state is unhashable

        """
        state_hash = hash(state)
        if state_hash == self._previous_state_hash:
            self._stagnant_count += 1
            if self._stagnant_count >= self._threshold:
                raise StagnantStateDetector.StagnantState(
                    "State has been the same for %d iterations"
                    % self._threshold
                )
        else:
            self._stagnant_count = 0
            self._previous_state_hash = state_hash


def get_debug_logger():
    """Get a logging object to be used as a debug logger only.

    :returns: logger object from logging module

    """
    logger = logging.getLogger("autopilot.debug")
    logger.addFilter(DebugLogFilter())
    return logger


class DebugLogFilter(object):

    """A filter class for the logging framework that allows us to turn off the
    debug log.

    """

    debug_log_enabled = False

    def filter(self, record):
        return int(self.debug_log_enabled)


def deprecated(alternative):
    """Write a deprecation warning to the logging framework."""

    def fdec(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            outerframe_details = inspect.getouterframes(
                inspect.currentframe())[1]
            filename, line_number, function_name = outerframe_details[1:4]

            logger.warning(
                "WARNING: in file \"{0}\", line {1} in {2}\n"
                "This function is deprecated. Please use '{3}' instead.\n"
                .format(filename, line_number, function_name, alternative)
            )
            return fn(*args, **kwargs)
        return wrapped
    return fdec


class _CleanupWrapper(object):

    """Support for calling 'addCleanup' outside the test case."""

    def __init__(self):
        self._test_instance = None

    def __call__(self, callable, *args, **kwargs):
        if self._test_instance is None:
            raise RuntimeError(
                "Out-of-test addCleanup can only be called while an autopilot "
                "test case is running!")
        self._test_instance.addCleanup(callable, *args, **kwargs)

    def set_test_instance(self, test_instance):
        self._test_instance = test_instance
        test_instance.addCleanup(self._on_test_ended)

    def _on_test_ended(self):
        self._test_instance = None


addCleanup = _CleanupWrapper()


_cleanup_objects = []


class _TestCleanupMeta(type):

    """Metaclass to inject the object into on test start/end functionality."""

    def __new__(cls, classname, bases, classdict):
        class EmptyStaticMethod(object):
            """Class used to give us 'default classmethods' for those that
            don't provide them.

            """
            def __get__(self, obj, klass=None):
                if klass is None:
                    klass = type(obj)

                def place_holder_method(*args):
                    pass

                return place_holder_method

        default_methods = {
            'on_test_start': EmptyStaticMethod(),
            'on_test_end': EmptyStaticMethod(),
        }

        default_methods.update(classdict)

        class_object = type.__new__(cls, classname, bases, default_methods)
        _cleanup_objects.append(class_object)

        return class_object


CleanupRegistered = _TestCleanupMeta('CleanupRegistered', (object,), {})


def action_on_test_start(test_instance):
    import sys
    for obj in _cleanup_objects:
        try:
            obj.on_test_start(test_instance)
        except KeyboardInterrupt:
            raise
        except:
            test_instance._report_traceback(sys.exc_info())


def action_on_test_end(test_instance):
    import sys
    for obj in _cleanup_objects:
        try:
            obj.on_test_end(test_instance)
        except KeyboardInterrupt:
            raise
        except:
            test_instance._report_traceback(sys.exc_info())


def on_test_started(test_case_instance):
    test_case_instance.addCleanup(action_on_test_end, test_case_instance)
    action_on_test_start(test_case_instance)
    addCleanup.set_test_instance(test_case_instance)


class MockableSleep(object):

    """Delay execution for a certain number of seconds.

    Functionally identical to `time.sleep`, except we can replace it during
    unit tests.

    To delay execution for 10 seconds, use it like this::

        from autopilot.utilities import sleep
        sleep(10)

    To mock out all calls to sleep, one might do this instead::

        from autopilot.utilities import sleep

        with sleep.mocked() as mock_sleep:
            sleep(10) # actually does nothing!
            self.assertEqual(mock_sleep.total_time_slept(), 10.0)

    """

    def __init__(self):
        self._mock_count = 0.0
        self._mocked = False

    def __call__(self, t):
        if not self._mocked:
            time.sleep(t)
        else:
            self._mock_count += t

    @contextmanager
    def mocked(self):
        self.enable_mock()
        try:
            yield self
        finally:
            self.disable_mock()

    def enable_mock(self):
        self._mocked = True
        self._mock_count = 0.0

    def disable_mock(self):
        self._mocked = False

    def total_time_slept(self):
        return self._mock_count


sleep = MockableSleep()


@decorator
def compatible_repr(f, *args, **kwargs):
    result = f(*args, **kwargs)
    if not isinstance(result, str):
        return result.decode('utf-8')
    return result


def _raise_on_unknown_kwargs(kwargs):
    """Raise ValueError on unknown keyword arguments.

    The standard use case is to warn callers that they've passed an unknown
    keyword argument. For example::

        def my_function(**kwargs):
            known_option = kwargs.pop('known_option')
            _raise_on_unknown_kwargs(kwargs)

    Given the code above, this will not raise any exceptions::

        my_function(known_option=123)

    ...but this code *will* raise a ValueError::

        my_function(known_option=123, other_option=456)

    """
    if kwargs:
        arglist = [repr(k) for k in kwargs.keys()]
        arglist.sort()
        raise ValueError(
            "Unknown keyword arguments: %s." % (', '.join(arglist))
        )


class cached_result(object):

    """A simple caching decorator.

    This class is deliberately simple. It does not handle unhashable types,
    keyword arguments, and has no built-in size control.

    """

    def __init__(self, f):
        functools.update_wrapper(self, f)
        self.f = f
        self._cache = {}

    def __call__(self, *args):
        try:
            return self._cache[args]
        except KeyError:
            result = self.f(*args)
            self._cache[args] = result
            return result
        except TypeError:
            raise TypeError(
                "The '%r' function can only be called with hashable arguments."
            )

    def reset_cache(self):
        self._cache.clear()


class EventDelay(object):

    """Delay execution of a subsequent event for a certain period
    of time.

    To delay the execution of a subsequent event for two seconds
    use it like this::

        from autopilot.utilities import EventDelay

        event_delayer = EventDelay()

        def print_something():
            event_delayer.delay(2)
            print("Hi! I am an event.")

        print_something()
        # It will take 2 seconds for second print()
        # to happen.
        print_something()

    """

    def __init__(self):
        self._last_event = 0.0

    @contextmanager
    def mocked(self):
        """Enable mocking for the EventDelay class

        Also mocks all calls to autopilot.utilities.sleep.
        One my use it like::

            from autopilot.utilities import EventDelay

            event_delayer = EventDelay()
            with event_delayer.mocked() as mocked_delay:
                event_delayer.delay(3)
                # This call will return instantly as the sleep
                # is mocked, just updating the _last_event variable.
                event_delayer.delay(10)
                self.assertThat(mocked_delay._last_event, GreaterThan(0.0))

        """
        sleep.enable_mock()
        try:
            yield self
        finally:
            sleep.disable_mock()

    def last_event_time(self):
        """return the time when delay() was last called."""
        return self._last_event

    def delay(self, duration, current_time=time.monotonic):
        """Delay the next event for a given amount of time.

        To humanize events, so that if a certain action is repeated
        continuously, there is a delay between each subsequent action.

        :param duration: Time interval between events.
        :param current_time: Specify the block of time to use as relative
          time. It is a float, representing time with precision of
          microseconds. Only for testing purpose. Default value is the
          monotonic time. 0.1 is the tenth part of a second.
        :raises ValueError: If the time stopped or went back since last
          event.

        """
        monotime = current_time()
        _raise_if_time_delta_not_sane(monotime, self._last_event)
        time_slept = 0.0
        if monotime < (self._last_event + duration):
            time_slept = _sleep_for_calculated_delta(
                monotime,
                self._last_event,
                duration
            )

        self._last_event = monotime + time_slept


def _raise_if_time_delta_not_sane(current_time, last_event_time):
    """Will raise a ValueError exception if current_time is before
    the last event or equal to it.

    """
    if current_time == last_event_time:
        raise ValueError(
            'current_time must be more than the last event time.'
        )
    elif current_time < last_event_time:
        raise ValueError(
            'current_time must not be behind the last event time.'
        )


def _sleep_for_calculated_delta(current_time, last_event_time, gap_duration):
    """Sleep for the remaining time between the last event time
    and duration.

    Given a duration in fractional seconds, ensure that at least
    that given amount of time occurs since the last event time.
    e.g. If 4 seconds have elapsed since the last event and the
    requested gap duration was 10 seconds, sleep for 6 seconds.

    :param float current_timestamp: Current monotonic time,
      in fractional seconds, used to calculate the time delta
      since last event.
    :param float last_event_timestamp: The last timestamp that
      the previous delay occured.
    :param float gap_duration: Maximum time, in fractional seconds,
      to be slept between two events.
    :return: Time, in fractional seconds, for which sleep happened.
    :raises ValueError: If last_event_time equals current_time or
      is ahead of current_time.

    """
    _raise_if_time_delta_not_sane(current_time, last_event_time)
    time_delta = (last_event_time + gap_duration) - current_time
    if time_delta > 0.0:
        sleep(time_delta)
        return time_delta
    else:
        return 0.0


class MockableProcessIter:
    def __init__(self):
        self._mocked = False
        self._fake_processes = []

    def __call__(self):
        if not self._mocked:
            return psutil.process_iter()
        else:
            return self.mocked_process_iter()

    @contextmanager
    def mocked(self, fake_processes):
        self.enable_mock(fake_processes)
        try:
            yield self
        finally:
            self.disable_mock()

    def enable_mock(self, fake_processes):
        self._mocked = True
        self._fake_processes = fake_processes

    def disable_mock(self):
        self._mocked = False
        self._fake_processes = []

    def create_mock_process(self, name, pid):
        mock_process = Mock()
        mock_process.name = lambda: name
        mock_process.pid = pid
        return mock_process

    def mocked_process_iter(self):
        for process in self._fake_processes:
            yield self.create_mock_process(
                process.get('name'),
                process.get('pid')
            )


process_iter = MockableProcessIter()
