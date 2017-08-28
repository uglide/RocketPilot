# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2015 Canonical
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

"""Fixtures to be used in autopilot's unit test suite."""

from fixtures import Fixture

from autopilot import globals as _g


class AutopilotVerboseLogging(Fixture):
    """Set the autopilot verbose log flag."""

    def __init__(self, verbose_logging=True):
        super().__init__()
        self._desired_state = verbose_logging

    def setUp(self):
        super().setUp()
        if _g.get_log_verbose() != self._desired_state:
            self.addCleanup(
                _g.set_log_verbose,
                _g.get_log_verbose()
            )
            _g.set_log_verbose(self._desired_state)
