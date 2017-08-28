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
from testtools.matchers import Equals, IsInstance

from autopilot.exceptions import BackendException


class BackendExceptionTests(TestCase):

    def test_must_wrap_exception(self):
        """BackendException must be able to wrap another exception instance."""
        err = BackendException(RuntimeError("Hello World"))
        self.assertThat(err.original_exception, IsInstance(RuntimeError))
        self.assertThat(str(err.original_exception), Equals("Hello World"))

    def test_dunder_str(self):
        err = BackendException(RuntimeError("Hello World"))
        self.assertThat(
            str(err), Equals(
                "Error while initialising backend. Original exception was: "
                "Hello World"))

    def test_dunder_repr(self):
        err = BackendException(RuntimeError("Hello World"))
        self.assertThat(
            repr(err), Equals(
                "BackendException('Error while initialising backend. Original "
                "exception was: Hello World',)"))
