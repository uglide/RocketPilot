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

from unittest.mock import patch
import subprocess
from testtools import TestCase
from testtools.matchers import Equals

from autopilot._info import (
    _get_package_installed_version,
    _get_package_version,
    get_version_string,
)


class VersionFnTests(TestCase):

    def test_package_version_returns_none_when_running_from_source(self):
        """_get_package_version must return None if we're not running in the
        system.

        """
        with patch('autopilot._info._running_in_system', new=lambda: False):
            self.assertThat(_get_package_version(), Equals(None))

    def test_get_package_installed_version_returns_None_on_error(self):
        """The _get_package_installed_version function must return None when
        subprocess raises an error while calling dpkg-query.
        """
        def raise_error(*args, **kwargs):
            raise subprocess.CalledProcessError(1, "dpkg-query")
        with patch('subprocess.check_output', new=raise_error):
            self.assertThat(_get_package_installed_version(), Equals(None))

    def test_get_package_installed_version_strips_command_output(self):
        """The _get_package_installed_version function must strip the output of
        the dpkg-query function.

        """
        with patch('subprocess.check_output',
                   new=lambda *a, **kwargs: "1.3daily13.05.22\n"):
            self.assertThat(
                _get_package_installed_version(), Equals("1.3daily13.05.22"))

    def test_get_version_string_shows_source_version(self):
        """The get_version_string function must only show the source version if
        the system version returns None.

        """
        with patch('autopilot._info._get_package_version', new=lambda: None):
            with patch('autopilot._info._get_source_version',
                       new=lambda: "1.3.1"):
                version_string = get_version_string()
        self.assertThat(
            version_string, Equals("Autopilot Source Version: 1.3.1"))

    def test_get_version_string_shows_both_versions(self):
        """The get_version_string function must show both source and package
        versions, when the package version is avaialble.capitalize
        """
        with patch('autopilot._info._get_package_version',
                   new=lambda: "1.3.1daily13.05.22"):
            with patch('autopilot._info._get_source_version',
                       new=lambda: "1.3.1"):
                version_string = get_version_string()
        self.assertThat(
            version_string,
            Equals("Autopilot Source Version: 1.3.1\nAutopilot Package "
                   "Version: 1.3.1daily13.05.22"))
