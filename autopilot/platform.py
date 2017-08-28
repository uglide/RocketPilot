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


import os

"""
Platform identification utilities for Autopilot.
================================================

This module provides functions that give test authors hints as to which
platform their tests are currently running on. This is useful when a test
needs to test slight different behavior depending on the system it's running
on. For example::

    from autopilot import platform

    ...

    def test_something(self):
        if platform.model() == "Galaxy Nexus":
            # do something
        elif platform.model() == "Desktop":
            # do something else

    def test_something_else(self):
        if platform.is_tablet():
            # run a tablet test
        else:
            # run a non-tablet test

Skipping tests based on Platform
++++++++++++++++++++++++++++++++

Sometimes you want a test to not run on certain platforms, or only run on
certain platforms. This can be easily achieved with a combination of the
functions in this module and the ``skipIf`` and ``skipUnless`` decorators. For
example, to define a test that only runs on the galaxy nexus device, write
this::

    from testtools import skipUnless

    ...

    @skipUnless(
        platform.model() == 'Galaxy Nexus',
        "Test is only for Galaxy Nexus"
    )
    def test_something(self):
        # test things!

The inverse is possible as well. To define a test that will run on every device
except the Galaxy Nexus, write this::

    from testtools import skipIf

    ...

    @skipIf(
        platform.model() == 'Galaxy Nexus',
        "Test not available for Galaxy Nexus"
    )
    def test_something(self):
        # test things!

Tuples of values can be used as well, to select more than one platform. For
example::

    @skipIf(
        platform.model() in ('Model One', 'Model Two'),
        "Test not available for Models One and Two"
    )
        def test_something(self):
            # test things!


"""


def model():
    """Get the model name of the current platform.

    For desktop / laptop installations, this will return "Desktop".
    Otherwise, the current hardware model will be returned. For example::

        platform.model()

        ... "Galaxy Nexus"

    """
    return _PlatformDetector.create().model


def image_codename():
    """Get the image codename.

    For desktop / laptop installations this will return "Desktop".
    Otherwise, the codename of the image that was installed will be
    returned. For example:

    platform.image_codename()

    ... "maguro"

    """
    return _PlatformDetector.create().image_codename


def is_tablet():
    """Indicate whether system is a tablet.

    The 'ro.build.characteristics' property is checked for 'tablet'.
    For example:

    platform.tablet()

    ... True

    :returns: boolean indicating whether this is a tablet

    """
    return _PlatformDetector.create().is_tablet


def get_display_server():
    """Returns display server type.

    :returns: string indicating display server type.

    """
    return os.environ.get('XDG_SESSION_TYPE', 'UNKNOWN').upper()


# Different vers. of psutil across Trusty and Utopic have name as either a
# string or a method.
def _get_process_name(proc):
    if callable(proc):
        return proc()
    elif isinstance(proc, str):
        return proc
    else:
        raise ValueError("Unknown process name format.")


class _PlatformDetector(object):

    _cached_detector = None

    @staticmethod
    def create():
        """Create a platform detector object, or return one we baked
        earlier."""
        if _PlatformDetector._cached_detector is None:
            _PlatformDetector._cached_detector = _PlatformDetector()
        return _PlatformDetector._cached_detector

    def __init__(self):
        self.model = "Desktop"
        self.image_codename = "Desktop"
        self.is_tablet = False

        property_file = _get_property_file()
        if property_file is not None:
            self.update_values_from_build_file(property_file)

    def update_values_from_build_file(self, property_file):
        """Read build.prop file and parse it."""
        properties = _parse_build_properties_file(property_file)
        self.model = properties.get('ro.product.model', "Desktop")
        self.image_codename = properties.get('ro.product.name', "Desktop")
        self.is_tablet = ('ro.build.characteristics' in properties and
                          'tablet' in properties['ro.build.characteristics'])


def _get_property_file_path():
    return '/system/build.prop'


def _get_property_file():
    """Return a file-like object that contains the contents of the build
    properties file, if it exists, or None.

    """
    path = _get_property_file_path()
    try:
        return open(path)
    except IOError:
        return None


def _parse_build_properties_file(property_file):
    """Parse 'property_file', which must be a file-like object containing the
    system build properties.

    Returns a dictionary of key,value pairs.

    """
    properties = {}
    for line in property_file:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        split_location = line.find('=')
        if split_location == -1:
            continue
        key = line[:split_location]
        value = line[split_location + 1:]

        properties[key] = value
    return properties
