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
import unittest
from unittest.mock import patch
from autopilot.display import Display


class DisplayTestCase(unittest.TestCase):

    @patch('autopilot.display._pick_backend')
    def test_input_backends_default_order(self, pick_backend):
        d = Display()
        d.create()

        backends = list(pick_backend.call_args[0][0].items())
        self.assertTrue(backends[0][0] == 'X11')
        self.assertTrue(backends[1][0] == 'UPA')
