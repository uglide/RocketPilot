# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2014 Canonical
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

import logging

import testtools


class LogHandlerTestCase(testtools.TestCase):

    """A mixin that adds a memento loghandler for testing logging."""

    class MementoHandler(logging.Handler):

        """A handler class which stores logging records in a list."""

        def __init__(self, *args, **kwargs):
            """Create the instance, and add a records attribute."""
            super().__init__(*args, **kwargs)
            self.records = []

        def emit(self, record):
            """Just add the record to self.records."""
            self.records.append(record)

        def check(self, level, msg, check_traceback=False):
            """Check that something is logged."""
            result = False
            for rec in self.records:
                if rec.levelname == level:
                    result = str(msg) in rec.getMessage()
                    if not result and check_traceback:
                        result = str(msg) in rec.exc_text
                    if result:
                        break

            return result

    def setUp(self):
        """Add the memento handler to the root logger."""
        super().setUp()
        self.memento_handler = self.MementoHandler()
        self.root_logger = logging.getLogger()
        self.root_logger.addHandler(self.memento_handler)

    def tearDown(self):
        """Remove the memento handler from the root logger."""
        self.root_logger.removeHandler(self.memento_handler)
        super().tearDown()

    def assertLogLevelContains(self, level, message, check_traceback=False):
        check = self.memento_handler.check(
            level, message, check_traceback=check_traceback)

        msg = ('Expected logging message/s could not be found:\n%s\n'
               'Current logging records are:\n%s')
        expected = '\t%s: %s' % (level, message)
        records = ['\t%s: %s' % (r.levelname, r.getMessage())
                   for r in self.memento_handler.records]
        self.assertTrue(check, msg % (expected, '\n'.join(records)))
