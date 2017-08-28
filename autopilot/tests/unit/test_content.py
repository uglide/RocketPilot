# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2013 Canonical
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

from tempfile import NamedTemporaryFile

from unittest.mock import Mock, patch
import os
from testtools import TestCase
from testtools.matchers import Contains, Equals, Not, Raises

from autopilot.content import follow_file


class FileFollowerTests(TestCase):

    def test_follow_file_adds_addDetail_cleanup(self):
        fake_test = Mock()
        with NamedTemporaryFile() as f:
            follow_file(f.name, fake_test)

        self.assertTrue(fake_test.addCleanup.called)
        fake_test.addCleanup.call_args[0][0]()
        self.assertTrue(fake_test.addDetail.called)

    def test_follow_file_content_object_contains_new_file_data(self):
        fake_test = Mock()
        with NamedTemporaryFile() as f:
            follow_file(f.name, fake_test)
            f.write(b"Hello")
            f.flush()

        fake_test.addCleanup.call_args[0][0]()
        actual = fake_test.addDetail.call_args[0][1].as_text()
        self.assertEqual("Hello", actual)

    def test_follow_file_does_not_contain_old_file_data(self):
        fake_test = Mock()
        with NamedTemporaryFile() as f:
            f.write(b"Hello")
            f.flush()
            follow_file(f.name, fake_test)
            f.write(b"World")
            f.flush()

        fake_test.addCleanup.call_args[0][0]()
        actual = fake_test.addDetail.call_args[0][1].as_text()
        self.assertEqual("World", actual)

    def test_follow_file_uses_filename_by_default(self):
        fake_test = Mock()
        with NamedTemporaryFile() as f:
            follow_file(f.name, fake_test)

            fake_test.addCleanup.call_args[0][0]()
            actual = fake_test.addDetail.call_args[0][0]
            self.assertEqual(f.name, actual)

    def test_follow_file_uses_content_name(self):
        fake_test = Mock()
        content_name = self.getUniqueString()
        with NamedTemporaryFile() as f:
            follow_file(f.name, fake_test, content_name)

            fake_test.addCleanup.call_args[0][0]()
            actual = fake_test.addDetail.call_args[0][0]
            self.assertEqual(content_name, actual)

    def test_follow_file_does_not_raise_on_IOError(self):
        fake_test = Mock()
        content_name = self.getUniqueString()
        with NamedTemporaryFile() as f:
            os.chmod(f.name, 0)

            self.assertThat(
                lambda: follow_file(f.name, fake_test, content_name),
                Not(Raises())
            )

    def test_follow_file_logs_error_on_IOError(self):
        fake_test = Mock()
        content_name = self.getUniqueString()
        with NamedTemporaryFile() as f:
            os.chmod(f.name, 0)

            with patch('autopilot.content._logger') as fake_logger:
                follow_file(f.name, fake_test, content_name)
                fake_logger.error.assert_called_once_with(
                    "Could not add content object '%s' due to IO Error: %s",
                    content_name,
                    "[Errno 13] Permission denied: '%s'" % f.name
                )

    def test_follow_file_returns_empty_content_object_on_error(self):
        fake_test = Mock()
        content_name = self.getUniqueString()
        with NamedTemporaryFile() as f:
            os.chmod(f.name, 0)

            content_obj = follow_file(f.name, fake_test, content_name)
            self.assertThat(content_obj.as_text(), Equals(''))

    def test_real_test_has_detail_added(self):
        with NamedTemporaryFile() as f:
            class FakeTest(TestCase):
                def test_foo(self):
                        follow_file(f.name, self)
                        f.write(b"Hello")
                        f.flush()
            test = FakeTest('test_foo')
            result = test.run()
        self.assertTrue(result.wasSuccessful)
        self.assertThat(test.getDetails(), Contains(f.name))
