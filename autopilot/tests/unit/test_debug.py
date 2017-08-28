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

from autopilot import _debug as d

from unittest.mock import Mock, patch
from tempfile import NamedTemporaryFile
from testtools import TestCase
from testtools.matchers import (
    Equals,
    Not,
    Raises,
)


class CaseAddDetailToNormalAddDetailDecoratorTests(TestCase):

    def test_sets_decorated_ivar(self):
        fake_detailed = Mock()
        decorated = d.CaseAddDetailToNormalAddDetailDecorator(fake_detailed)

        self.assertThat(decorated.decorated, Equals(fake_detailed))

    def test_addDetail_calls_caseAddDetail(self):
        fake_detailed = Mock()
        decorated = d.CaseAddDetailToNormalAddDetailDecorator(fake_detailed)
        content_name = self.getUniqueString()
        content_object = object()

        decorated.addDetail(content_name, content_object)

        fake_detailed.caseAddDetail.assert_called_once_with(
            content_name,
            content_object
        )

    def test_all_other_attrs_are_passed_through(self):
        fake_detailed = Mock()
        decorated = d.CaseAddDetailToNormalAddDetailDecorator(fake_detailed)

        decorated.some_method()
        fake_detailed.some_method.assert_called_once_with()

    def test_repr(self):
        fake_detailed = Mock()
        decorated = d.CaseAddDetailToNormalAddDetailDecorator(fake_detailed)

        self.assertThat(
            repr(decorated),
            Equals(
                '<CaseAddDetailToNormalAddDetailDecorator {}>'.format(
                    repr(fake_detailed)
                )
            )
        )


class DebugProfileTests(TestCase):

    def setUp(self):
        super(DebugProfileTests, self).setUp()
        self.fake_caseAddDetail = Mock()

    def test_can_construct_debug_profile(self):
        d.DebugProfile(self.fake_caseAddDetail)

    def test_debug_profile_sets_caseAddDetail(self):
        profile = d.DebugProfile(self.fake_caseAddDetail)

        self.assertThat(
            profile.caseAddDetail,
            Equals(self.fake_caseAddDetail)
        )

    def test_default_debug_profile_is_normal(self):
        self.assertThat(
            d.get_default_debug_profile().name,
            Equals("normal")
        )

    def test_normal_profile_name(self):
        self.assertThat(
            d.NormalDebugProfile(self.fake_caseAddDetail).name,
            Equals("normal")
        )

    def test_verbose_profile_name(self):
        self.assertThat(
            d.VerboseDebugProfile(self.fake_caseAddDetail).name,
            Equals("verbose")
        )

    def test_all_profiles(self):
        self.assertThat(
            d.get_all_debug_profiles(),
            Equals({d.VerboseDebugProfile, d.NormalDebugProfile})
        )

    def test_debug_profile_uses_fixtures_in_setup(self):

        class DebugObjectDouble(d.DebugObject):

            init_called = False
            setup_called = False

            def __init__(self, *args, **kwargs):
                super(DebugObjectDouble, self).__init__(*args, **kwargs)
                DebugObjectDouble.init_called = True

            def setUp(self, *args, **kwargs):
                super(DebugObjectDouble, self).setUp(*args, **kwargs)
                DebugObjectDouble.setup_called = True

        class TestDebugProfile(d.DebugProfile):

            name = "test"

            def __init__(self, caseAddDetail):
                super(TestDebugProfile, self).__init__(
                    caseAddDetail,
                    [DebugObjectDouble]
                )

        profile = TestDebugProfile(Mock())
        profile.setUp()

        self.assertTrue(DebugObjectDouble.init_called)
        self.assertTrue(DebugObjectDouble.setup_called)


class LogFollowerTests(TestCase):

    def setUp(self):
        super(LogFollowerTests, self).setUp()
        self.fake_caseAddDetail = Mock()

    def test_can_construct_log_debug_object(self):
        path = self.getUniqueString()
        log_debug_object = d.LogFileDebugObject(
            self.fake_caseAddDetail,
            path
        )

        self.assertThat(log_debug_object.log_path, Equals(path))

    def test_calls_follow_file_with_correct_parameters(self):
        path = self.getUniqueString()
        with patch.object(d, 'follow_file') as patched_follow_file:
            log_debug_object = d.LogFileDebugObject(
                self.fake_caseAddDetail,
                path
            )
            log_debug_object.setUp()

            self.assertThat(patched_follow_file.call_count, Equals(1))
            args, _ = patched_follow_file.call_args
            self.assertThat(args[0], Equals(path))
            self.assertTrue(callable(getattr(args[1], 'addDetail', None)))
            self.assertTrue(callable(getattr(args[1], 'addCleanup', None)))

    def test_reads_new_file_lines(self):
        open_args = dict(buffering=0)
        with NamedTemporaryFile(**open_args) as temp_file:
            temp_file.write("Hello\n".encode())
            log_debug_object = d.LogFileDebugObject(
                self.fake_caseAddDetail,
                temp_file.name
            )
            log_debug_object.setUp()
            temp_file.write("World\n".encode())
            log_debug_object.cleanUp()

            self.assertThat(self.fake_caseAddDetail.call_count, Equals(1))
            args, _ = self.fake_caseAddDetail.call_args
            self.assertThat(args[0], Equals(temp_file.name))
            self.assertThat(args[1].as_text(), Equals("World\n"))

    def test_can_follow_file_with_binary_content(self):
        open_args = dict(buffering=0)
        with NamedTemporaryFile(**open_args) as temp_file:
            log_debug_object = d.LogFileDebugObject(
                self.fake_caseAddDetail,
                temp_file.name
            )
            log_debug_object.setUp()
            temp_file.write("Hello\x88World".encode())
            log_debug_object.cleanUp()

        args, _ = self.fake_caseAddDetail.call_args
        self.assertThat(args[1].as_text, Not(Raises()))

    def test_can_create_syslog_follower(self):
        debug_obj = d.SyslogDebugObject(Mock())
        self.assertThat(debug_obj.log_path, Equals("/var/log/syslog"))
