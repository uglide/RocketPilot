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

"""Support for debug profiles.

Debug profiles are used to attach various items of debug information to
a test result. Profiles are named, but the names are for human
consumption only, and have no other significance.

Each piece of debug information is also a fixture, so debug profiles are
fixtures of fixtures!

"""

from autopilot.content import follow_file
from autopilot._fixtures import FixtureWithDirectAddDetail


class CaseAddDetailToNormalAddDetailDecorator(object):

    """A decorator object to turn a FixtureWithDirectAddDetail object into
    an object that supports addDetail.
    """

    def __init__(self, decorated):
        self.decorated = decorated

    def addDetail(self, name, content):
        return self.decorated.caseAddDetail(name, content)

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.decorated)

    def __getattr__(self, name):
        return getattr(self.decorated, name)


class DebugProfile(FixtureWithDirectAddDetail):

    """A debug profile that contains manny debug objects."""

    name = ""

    def __init__(self, caseAddDetail, debug_fixtures=[]):
        """Create a debug profile.

        :param caseAddDetail: A closure over the testcase's addDetail
            method, or a similar substitution method.
        :param debug_fixtures: a list of fixture class objects, each one will
            be set up when this debug profile is used.
        """
        super(DebugProfile, self).__init__(caseAddDetail)
        self.debug_fixtures = debug_fixtures

    def setUp(self):
        super(DebugProfile, self).setUp()
        for FixtureClass in self.debug_fixtures:
            self.useFixture(FixtureClass(self.caseAddDetail))


class NormalDebugProfile(DebugProfile):

    name = "normal"

    def __init__(self, caseAddDetail):
        super(NormalDebugProfile, self).__init__(
            caseAddDetail,
            [
                SyslogDebugObject,
            ],
        )


class VerboseDebugProfile(DebugProfile):

    name = "verbose"

    def __init__(self, caseAddDetail):
        super(VerboseDebugProfile, self).__init__(
            caseAddDetail,
            [
                SyslogDebugObject,
            ],
        )


def get_default_debug_profile():
    return NormalDebugProfile


def get_all_debug_profiles():
    return {
        NormalDebugProfile,
        VerboseDebugProfile,
    }


class DebugObject(FixtureWithDirectAddDetail):

    """A single piece of debugging information."""


class LogFileDebugObject(DebugObject):

    """Monitors a log file on disk."""

    def __init__(self, caseAddDetail, log_path):
        """Create a debug object that will monitor the contents of a log
        file on disk.

        :param caseAddDetail: A closure over the testcase's addDetail
            method, or a similar substitution method.
        :param log_path: The path to monitor.
        """
        super(LogFileDebugObject, self).__init__(caseAddDetail)
        self.log_path = log_path

    def setUp(self):
        super(LogFileDebugObject, self).setUp()
        follow_file(
            self.log_path,
            CaseAddDetailToNormalAddDetailDecorator(self)
        )


def SyslogDebugObject(caseAddDetail):
    return LogFileDebugObject(caseAddDetail, "/var/log/syslog")
