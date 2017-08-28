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


from autopilot._debug import DebugProfile

import logging

logger = logging.getLogger(__name__)
_log_verbose = False


def get_log_verbose():
    """Return true if the user asked for verbose logging."""
    global _log_verbose
    return _log_verbose


def set_log_verbose(verbose):
    """Set whether or not we should log verbosely."""
    global _log_verbose
    if type(verbose) is not bool:
        raise TypeError("Verbose flag must be a boolean.")
    _log_verbose = verbose


_debug_profile_fixture = DebugProfile


def set_debug_profile_fixture(fixture_class):
    global _debug_profile_fixture
    _debug_profile_fixture = fixture_class


def get_debug_profile_fixture():
    global _debug_profile_fixture
    return _debug_profile_fixture


_default_timeout_value = 10


def set_default_timeout_period(new_timeout):
    global _default_timeout_value
    _default_timeout_value = new_timeout


def get_default_timeout_period():
    global _default_timeout_value
    return _default_timeout_value


_long_timeout_value = 30


def set_long_timeout_period(new_timeout):
    global _long_timeout_value
    _long_timeout_value = new_timeout


def get_long_timeout_period():
    global _long_timeout_value
    return _long_timeout_value


# The timeout to apply to each test. 0 means no timeout. Value is in seconds.
_test_timeout = 0


def set_test_timeout(new_timeout):
    global _test_timeout
    _test_timeout = new_timeout


def get_test_timeout():
    global _test_timeout
    return _test_timeout
