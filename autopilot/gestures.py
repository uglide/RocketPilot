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


"""Gestural support for autopilot.

This module contains functions that can generate touch and multi-touch gestures
for you. This is a convenience for the test author - there is nothing to
prevent you from generating your own gestures!

"""

from autopilot.input import Touch
from autopilot.utilities import sleep


def pinch(center, vector_start, vector_end):
    """Perform a two finger pinch (zoom) gesture.

    :param center: The coordinates (x,y) of the center of the pinch gesture.
    :param vector_start: The (x,y) values to move away from the center for the
     start.
    :param vector_end: The (x,y) values to move away from the center for the
     end.

    The fingers will move in 100 steps between the start and the end points.
    If start is smaller than end, the gesture will zoom in, otherwise it
    will zoom out.

    """

    finger_1_start = [center[0] - vector_start[0], center[1] - vector_start[1]]
    finger_2_start = [center[0] + vector_start[0], center[1] + vector_start[1]]
    finger_1_end = [center[0] - vector_end[0], center[1] - vector_end[1]]
    finger_2_end = [center[0] + vector_end[0], center[1] + vector_end[1]]

    dx = 1.0 * (finger_1_end[0] - finger_1_start[0]) / 100
    dy = 1.0 * (finger_1_end[1] - finger_1_start[1]) / 100

    finger_1 = Touch.create()
    finger_2 = Touch.create()

    finger_1.press(*finger_1_start)
    finger_2.press(*finger_2_start)

    finger_1_cur = [finger_1_start[0] + dx, finger_1_start[1] + dy]
    finger_2_cur = [finger_2_start[0] - dx, finger_2_start[1] - dy]

    for i in range(0, 100):
        finger_1.move(*finger_1_cur)
        finger_2.move(*finger_2_cur)
        sleep(0.005)

        finger_1_cur = [finger_1_cur[0] + dx, finger_1_cur[1] + dy]
        finger_2_cur = [finger_2_cur[0] - dx, finger_2_cur[1] - dy]

    finger_1.move(*finger_1_end)
    finger_2.move(*finger_2_end)
    finger_1.release()
    finger_2.release()
