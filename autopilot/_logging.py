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

"""Autopilot's logging code."""

import logging
from io import StringIO

from autopilot._fixtures import FixtureWithDirectAddDetail
from autopilot.utilities import (
    LogFormatter,
    safe_text_content,
)


class TestCaseLoggingFixture(FixtureWithDirectAddDetail):

    """A fixture that adds the log to the test case as a detail object."""
    def __init__(self, test_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._test_id = test_id

    def setUp(self):
        super().setUp()
        logging.info("*" * 60)
        logging.info("Starting test %s", self._test_id)

        self._log_buffer = StringIO()
        root_logger = logging.getLogger()
        formatter = LogFormatter()
        self._log_handler = logging.StreamHandler(stream=self._log_buffer)
        self._log_handler.setFormatter(formatter)
        root_logger.addHandler(self._log_handler)
        self.addCleanup(self._tearDownLogging)

    def _tearDownLogging(self):
        root_logger = logging.getLogger()
        self._log_handler.flush()
        self._log_buffer.seek(0)
        self.caseAddDetail(
            'test-log',
            safe_text_content(self._log_buffer.getvalue())
        )
        root_logger.removeHandler(self._log_handler)
        self._log_buffer = None
