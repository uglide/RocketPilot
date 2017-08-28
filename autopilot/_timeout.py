# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2014 Canonical
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

"""Autopilot timeout functions.

Autopilot frequently needs to repeatedly run code within a certain timeout
period. Historically this was done with a simple ``for`` loop and a ``sleep``
statement, like this::

    for i in range(10):
        # do some polling code here
        time.sleep(1)

The problem with this approach is that we hard-code both the absolute timeout
value (10 seconds in this case), as well as the time to sleep after each poll.

When Autopilot runs on certain platforms, we need to globally increase the
timeout period. We'd also like to be able to avoid the common pitfall of
forgetting to call ``time.sleep``.

Finally, we support mocking out the ``sleep`` call, so autopilot tests can
run quickly and verify the polling behavior of low-level function calls.

"""

from autopilot.utilities import sleep
from autopilot.globals import (
    get_default_timeout_period,
    get_long_timeout_period,
)


class Timeout(object):

    """Class for starting different timeout loops.

    This class contains two static methods. Each method is a generator, and
    provides a timeout for a different period of time. For example, to
    generate a short polling timeout, the code would look like this::

        for elapsed_time in Timeout.default():
            # polling code goes here

    the ``elapsed_time`` variable will contain the amount of time elapsed, in
    seconds, since the beginning of the loop, although this is not guaranteed
    to be accurate.
    """

    @staticmethod
    def default():
        """Start a polling loop with the default timeout.

        This is the polling loop that should be used by default (hence the
        name) unless the operation is known to take a very long time,
        especially on slow or virtualised hardware.

        """
        timeout = float(get_default_timeout_period())
        # Once we only support py3.3, replace this with
        # yield from _do_timeout(timeout)
        for i in _do_timeout(timeout):
            yield i

    @staticmethod
    def long():
        """Start a polling loop with a long timeout.

        This is the polling loop that should be used for operations that are
        known to take extra long on slow, or virtualised hardware.

        """
        timeout = float(get_long_timeout_period())
        # Once we only support py3.3, replace this with
        # yield from _do_timeout(timeout)
        for i in _do_timeout(timeout):
            yield i


def _do_timeout(timeout):
    time_elapsed = 0.0
    while timeout - time_elapsed > 0.0:
        yield time_elapsed
        time_to_sleep = min(timeout - time_elapsed, 1.0)
        sleep(time_to_sleep)
        time_elapsed += time_to_sleep
    yield time_elapsed
