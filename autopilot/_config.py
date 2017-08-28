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

import collections.abc


_test_config_string = ""


def set_configuration_string(config_string):
    """Set the test configuration string.

    This must be a text string that specifies the test configuration. The
    string is a comma separated list of 'key=value' or 'key' tokens.

    """
    global _test_config_string
    _test_config_string = config_string


def get_test_configuration():
    """Get the test configuration dictionary.

    Tests can be configured from the command line when the ``autopilot`` tool
    is invoked. Typical use cases involve configuring the test suite to use
    a particular binary (perhaps a locally built binary or one installed to
    the system), or configuring which external services are faked.

    This dictionary is populated from the ``--config`` option to the
    ``autopilot run`` command. For example:

    ``autopilot run --config use_local some.test.id``

    Will result in a dictionary where the key ``use_local`` is present, and
    evaluates to true, e.g.-::

        from autopilot import get_test_configuration
        if get_test_configuration['use_local']: print("Using local binary")

    Values can also be specified. The following command:

    ``autopilot run --config fake_services=login some.test.id``

    ...will result in the key 'fake_services' having the value 'login'.

    Autopilot itself does nothing with the conents of this dictionary. It is
    entirely up to test authors to populate it, and to use the values as they
    see fit.

    """
    return ConfigDict(_test_config_string)


class ConfigDict(collections.abc.Mapping):

    def __init__(self, config_string):
        self._data = {}
        config_items = (item for item in config_string.split(',') if item)
        for item in config_items:
            parts = item.split('=', 1)
            safe_key = parts[0].lstrip()
            if len(parts) == 1 and safe_key != '':
                self._data[safe_key] = '1'
            elif len(parts) == 2 and safe_key != '':
                self._data[safe_key] = parts[1]
            else:
                raise ValueError(
                    "Invalid configuration string '{}'".format(config_string)
                )

    def __getitem__(self, key):
        return self._data.__getitem__(key)

    def __iter__(self):
        return self._data.__iter__()

    def __len__(self):
        return self._data.__len__()
