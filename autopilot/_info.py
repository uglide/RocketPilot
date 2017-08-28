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

"""Provide version and package availibility information for autopilot."""

import subprocess


__all__ = [
    'get_version_string',
    'have_vis',
    'version',
]

version = '1.6.0'


def have_vis():
    """Return true if the vis package is installed."""
    try:
        from autopilot.vis import vis_main  # flake8: noqa
        return True
    except ImportError:
        return False


def get_version_string():
    """Return the autopilot source and package versions."""
    version_string = "Autopilot Source Version: " + _get_source_version()
    pkg_version = _get_package_version()
    if pkg_version:
        version_string += "\nAutopilot Package Version: " + pkg_version
    return version_string


def _get_source_version():
    return version


def _get_package_version():
    """Get the version of the currently installed package version, or None.

    Only returns the package version if the package is installed, *and* we seem
    to be running the system-wide installed code.
    """
    if _running_in_system():
        return _get_package_installed_version()
    return None


def _running_in_system():
    """Return True if we're running autopilot from the system installation
    dir."""
    return __file__.startswith('/usr/')


def _get_package_installed_version():
    """Get the version string of the system-wide installed package, or None if
    it is not installed.

    """
    try:
        return subprocess.check_output(
            [
                "dpkg-query",
                "--showformat",
                "${Version}",
                "--show",
                "python3-autopilot",
            ],
            universal_newlines=True
        ).strip()
    except subprocess.CalledProcessError:
        return None
