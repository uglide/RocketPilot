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


from testtools import TestCase
from testtools.matchers import Equals

from autopilot.utilities import addCleanup, on_test_started


log = ''


class AddCleanupTests(TestCase):

    def test_addCleanup_called_with_args_and_kwargs(self):
        """Test that out-of-test addClenaup works as expected, and is passed
        both args and kwargs.

        """
        class InnerTest(TestCase):
            def write_to_log(self, *args, **kwargs):
                global log
                log = "Hello %r %r" % (args, kwargs)

            def test_foo(self):
                on_test_started(self)
                addCleanup(self.write_to_log, "arg1", 2, foo='bar')

        InnerTest('test_foo').run()
        self.assertThat(log, Equals("Hello ('arg1', 2) {'foo': 'bar'}"))
