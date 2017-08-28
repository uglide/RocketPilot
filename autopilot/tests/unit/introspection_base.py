# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2016 Canonical
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

from unittest.mock import Mock
from collections import namedtuple


X_DEFAULT = 0
Y_DEFAULT = 0
W_DEFAULT = 0
H_DEFAULT = 0

global_rect = namedtuple('globalRect', ['x', 'y', 'w', 'h'])


class MockObject(Mock):
    def __init__(self, *args, **kwargs):
        super().__init__()
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_properties(self):
        return self.__dict__


get_mock_object = MockObject


def get_global_rect(x=X_DEFAULT, y=Y_DEFAULT, w=W_DEFAULT, h=H_DEFAULT):
    return global_rect(x, y, w, h)
