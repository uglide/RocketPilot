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

from autopilot.tests.functional.fixtures import (
    ExecutableScript,
    Timezone,
    TempDesktopFile,
)

import os
import os.path
import stat
from unittest.mock import patch
from shutil import rmtree
import tempfile
from testtools import TestCase
from testtools.matchers import Contains, EndsWith, Equals, FileContains


class TempDesktopFileTests(TestCase):
    def test_setUp_creates_desktop_file(self):
        desktop_file_dir = tempfile.mkdtemp(dir="/tmp")
        self.addCleanup(rmtree, desktop_file_dir)

        with patch.object(
            TempDesktopFile, '_desktop_file_dir', return_value=desktop_file_dir
        ):
            temp_desktop_file = TempDesktopFile()
            temp_desktop_file.setUp()
            desktop_file_path = temp_desktop_file.get_desktop_file_path()

            self.assertTrue(os.path.exists(desktop_file_path))
            temp_desktop_file.cleanUp()
            self.assertFalse(os.path.exists(desktop_file_path))

    def test_desktop_file_dir_returns_expected_directory(self):
        expected_directory = os.path.join(
            os.getenv('HOME'),
            '.local',
            'share',
            'applications'
        )
        self.assertThat(
            TempDesktopFile._desktop_file_dir(),
            Equals(expected_directory)
        )

    def test_ensure_desktop_dir_exists_returns_empty_string_when_exists(self):
        desktop_file_dir = tempfile.mkdtemp(dir="/tmp")
        self.addCleanup(rmtree, desktop_file_dir)

        with patch.object(
            TempDesktopFile, '_desktop_file_dir', return_value=desktop_file_dir
        ):
            self.assertThat(
                TempDesktopFile._ensure_desktop_dir_exists(),
                Equals("")
            )

    def test_ensure_desktop_dir_exists_creates_dir_when_needed(self):
        tmp_dir = tempfile.mkdtemp(dir="/tmp")
        self.addCleanup(rmtree, tmp_dir)
        desktop_file_dir = os.path.join(
            tmp_dir, '.local', 'share', 'applications'
        )

        with patch.object(
            TempDesktopFile, '_desktop_file_dir', return_value=desktop_file_dir
        ):
            TempDesktopFile._ensure_desktop_dir_exists()
            self.assertTrue(os.path.exists(desktop_file_dir))

    def test_ensure_desktop_dir_exists_returns_path_to_delete(self):
        tmp_dir = tempfile.mkdtemp(dir="/tmp")
        self.addCleanup(rmtree, tmp_dir)
        desktop_file_dir = os.path.join(
            tmp_dir, '.local', 'share', 'applications'
        )
        expected_to_remove = os.path.join(tmp_dir, '.local')

        with patch.object(
            TempDesktopFile, '_desktop_file_dir', return_value=desktop_file_dir
        ):
            self.assertThat(
                TempDesktopFile._ensure_desktop_dir_exists(),
                Equals(expected_to_remove)
            )

    def test_create_desktop_file_dir_returns_path_to_delete(self):
        tmp_dir = tempfile.mkdtemp(dir="/tmp")
        self.addCleanup(rmtree, tmp_dir)
        desktop_file_dir = os.path.join(
            tmp_dir, '.local', 'share', 'applications'
        )
        expected_to_remove = os.path.join(tmp_dir, '.local')

        self.assertThat(
            TempDesktopFile._create_desktop_file_dir(desktop_file_dir),
            Equals(expected_to_remove)
        )

    def test_create_desktop_file_dir_returns_empty_str_when_path_exists(self):
        desktop_file_dir = tempfile.mkdtemp(dir="/tmp")
        self.addCleanup(rmtree, desktop_file_dir)

        self.assertThat(
            TempDesktopFile._create_desktop_file_dir(desktop_file_dir),
            Equals("")
        )

    def test_remove_desktop_file_removes_created_file_when_path_exists(self):
        test_created_path = self.getUniqueString()
        with patch('autopilot.tests.functional.fixtures.rmtree') as p_rmtree:
            TempDesktopFile._remove_desktop_file_components(
                test_created_path, ""
            )
            p_rmtree.assert_called_once_with(test_created_path)

    def test_remove_desktop_file_removes_created_path(self):
        test_created_file = self.getUniqueString()
        with patch('autopilot.tests.functional.os.remove') as p_remove:
            TempDesktopFile._remove_desktop_file_components(
                "", test_created_file
            )
            p_remove.assert_called_once_with(test_created_file)

    def test_create_desktop_file_creates_file_in_correct_place(self):
        desktop_file_dir = tempfile.mkdtemp(dir="/tmp")
        self.addCleanup(rmtree, desktop_file_dir)

        with patch.object(
            TempDesktopFile, '_desktop_file_dir', return_value=desktop_file_dir
        ):
            desktop_file = TempDesktopFile._create_desktop_file("")
            path, head = os.path.split(desktop_file)
            self.assertThat(path, Equals(desktop_file_dir))

    def test_create_desktop_file_writes_correct_data(self):
        desktop_file_dir = tempfile.mkdtemp(dir="/tmp")
        self.addCleanup(rmtree, desktop_file_dir)
        token = self.getUniqueString()

        with patch.object(
            TempDesktopFile, '_desktop_file_dir', return_value=desktop_file_dir
        ):
            desktop_file = TempDesktopFile._create_desktop_file(token)
            self.assertTrue(desktop_file.endswith('.desktop'))
            self.assertThat(desktop_file, FileContains(token))

    def do_parameter_contents_test(self, matcher, **kwargs):
        fixture = self.useFixture(TempDesktopFile(**kwargs))
        self.assertThat(
            fixture.get_desktop_file_path(),
            FileContains(matcher=matcher),
        )

    def test_can_specify_exec_path(self):
        token = self.getUniqueString()
        self.do_parameter_contents_test(
            Contains("Exec="+token),
            exec_=token
        )

    def test_can_specify_type(self):
        token = self.getUniqueString()
        self.do_parameter_contents_test(
            Contains("Type="+token),
            type=token
        )

    def test_can_specify_name(self):
        token = self.getUniqueString()
        self.do_parameter_contents_test(
            Contains("Name="+token),
            name=token
        )

    def test_can_specify_icon(self):
        token = self.getUniqueString()
        self.do_parameter_contents_test(
            Contains("Icon="+token),
            icon=token
        )


class ExecutableScriptTests(TestCase):

    def test_creates_file_with_content(self):
        token = self.getUniqueString()
        fixture = self.useFixture(ExecutableScript(script=token))
        self.assertThat(fixture.path, FileContains(token))

    def test_creates_file_with_correct_extension(self):
        token = self.getUniqueString()
        fixture = self.useFixture(ExecutableScript(script="", extension=token))
        self.assertThat(fixture.path, EndsWith(token))

    def test_creates_file_with_execute_bit_set(self):
        fixture = self.useFixture(ExecutableScript(script=""))
        self.assertTrue(os.stat(fixture.path).st_mode & stat.S_IXUSR)


class TimezoneFixtureTests(TestCase):

    def test_sets_environment_variable_to_timezone(self):
        token = self.getUniqueString()

        self.useFixture(Timezone(token))

        self.assertEqual(os.environ.get('TZ'), token)

    def test_resets_timezone_back_to_original(self):
        original_tz = os.environ.get('TZ', None)
        token = self.getUniqueString()

        with Timezone(token):
            pass  # Trigger cleanup

        self.assertEqual(os.environ.get('TZ', None), original_tz)
