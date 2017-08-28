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
import subprocess

from autopilot.display import Display as DisplayBase
from autopilot.platform import get_display_server, image_codename

DISPLAY_SERVER_X11 = 'X11'
DISPLAY_SERVER_MIR = 'MIR'
ENV_MIR_SOCKET = 'MIR_SERVER_HOST_SOCKET'


def query_resolution():
    display_server = get_display_server()
    if display_server == DISPLAY_SERVER_X11:
        return _get_resolution_from_xrandr()
    elif display_server == DISPLAY_SERVER_MIR:
        return _get_resolution_from_mirout()
    else:
        return _get_hardcoded_resolution()


def _get_hardcoded_resolution():
    name = image_codename()

    resolutions = {
        "Aquaris_M10_HD": (800, 1280),
        "Desktop": (1920, 1080)
    }

    if name not in resolutions:
        raise NotImplementedError(
            'Device "{}" is not supported by Autopilot.'.format(name))

    return resolutions[name]


def _get_stdout_for_command(command, *args):
    full_command = [command]
    full_command.extend(args)
    return subprocess.check_output(
        full_command,
        universal_newlines=True,
        stderr=subprocess.DEVNULL,
    ).split('\n')


def _get_resolution(server_output):
    relevant_line = list(filter(lambda line: '*' in line, server_output))[0]
    if relevant_line:
        return tuple([int(i) for i in relevant_line.split()[0].split('x')])
    raise ValueError(
        'Failed to get display resolution, is a display connected?'
    )


def _get_resolution_from_xrandr():
    return _get_resolution(_get_stdout_for_command('xrandr', '--current'))


def _get_resolution_from_mirout():
    return _get_resolution(
        _get_stdout_for_command('mirout', os.environ.get(ENV_MIR_SOCKET))
    )


class Display(DisplayBase):
    """The base class/inteface for the display devices"""

    def __init__(self):
        super(Display, self).__init__()
        self._X, self._Y = query_resolution()

    def get_num_screens(self):
        """Get the number of screens attached to the PC."""
        return 1

    def get_primary_screen(self):
        """Returns an integer of which screen is considered the primary"""
        return 0

    def get_screen_width(self):
        return self._X

    def get_screen_height(self):
        return self._Y

    def get_screen_geometry(self, screen_number):
        """Get the geometry for a particular screen.

        :return: Tuple containing (x, y, width, height).

        """
        return 0, 0, self._X, self._Y
