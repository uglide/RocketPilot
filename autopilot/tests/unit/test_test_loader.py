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

import os
import os.path
import random
import string
from testtools import TestCase
from testtools.matchers import Not, Raises
from contextlib import contextmanager
from unittest.mock import patch
import shutil
import tempfile

from autopilot.run import (
    _discover_test,
    get_package_location,
    load_test_suite_from_name
)


@contextmanager
def working_dir(directory):
    original_directory = os.getcwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(original_directory)


class TestLoaderTests(TestCase):

    _previous_module_names = []

    def setUp(self):
        super(TestLoaderTests, self).setUp()
        self.sandbox_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.sandbox_dir)

        self.test_module_name = self._unique_module_name()

    def _unique_module_name(self):
        generator = lambda: ''.join(
            random.choice(string.ascii_letters) for letter in range(8)
        )
        name = generator()
        while name in self._previous_module_names:
            name = generator()
        self._previous_module_names.append(name)

        return name

    def create_empty_package_file(self, filename):
        full_filename = os.path.join(self.test_module_name, filename)
        with self.open_sandbox_file(full_filename) as f:
            f.write('')

    def create_package_file_with_contents(self, filename, contents):
        full_filename = os.path.join(self.test_module_name, filename)
        with self.open_sandbox_file(full_filename) as f:
            f.write(contents)

    @contextmanager
    def open_sandbox_file(self, relative_path):
        full_path = os.path.join(self.sandbox_dir, relative_path)
        dirname = os.path.dirname(full_path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(full_path, 'w') as f:
            yield f

    @contextmanager
    def simple_file_setup(self):
        with self.open_sandbox_file('test_foo.py') as f:
            f.write('')
        with working_dir(self.sandbox_dir):
            yield

    def test_get_package_location_can_import_file(self):
        with self.simple_file_setup():
            self.assertThat(
                lambda: get_package_location('test_foo'),
                Not(Raises())
            )

    def test_get_package_location_returns_correct_directory(self):
        with self.simple_file_setup():
            actual = get_package_location('test_foo')

        self.assertEqual(self.sandbox_dir, actual)

    def test_get_package_location_can_import_package(self):
        self.create_empty_package_file('__init__.py')

        with working_dir(self.sandbox_dir):
            self.assertThat(
                lambda: get_package_location(self.test_module_name),
                Not(Raises()),
                verbose=True
            )

    def test_get_package_location_returns_correct_directory_for_package(self):
        self.create_empty_package_file('__init__.py')

        with working_dir(self.sandbox_dir):
            actual = get_package_location(self.test_module_name)

        self.assertEqual(self.sandbox_dir, actual)

    def test_get_package_location_can_import_nested_module(self):
        self.create_empty_package_file('__init__.py')
        self.create_empty_package_file('foo.py')

        with working_dir(self.sandbox_dir):
            self.assertThat(
                lambda: get_package_location('%s.foo' % self.test_module_name),
                Not(Raises()),
                verbose=True
            )

    def test_get_package_location_returns_correct_directory_for_nested_module(self):  # noqa
        self.create_empty_package_file('__init__.py')
        self.create_empty_package_file('foo.py')

        with working_dir(self.sandbox_dir):
            actual = get_package_location('%s.foo' % self.test_module_name)

        self.assertEqual(self.sandbox_dir, actual)

    @patch('autopilot.run._show_test_locations', new=lambda a: True)
    def test_load_test_suite_from_name_can_load_file(self):
        with self.open_sandbox_file('test_foo.py') as f:
            f.write(SIMPLE_TESTCASE)
        with working_dir(self.sandbox_dir):
            suite, _ = load_test_suite_from_name('test_foo')

        self.assertEqual(1, len(suite._tests))

    @patch('autopilot.run._show_test_locations', new=lambda a: True)
    def test_load_test_suite_from_name_can_load_nested_module(self):
        self.create_empty_package_file('__init__.py')
        self.create_package_file_with_contents('test_foo.py', SIMPLE_TESTCASE)
        with working_dir(self.sandbox_dir):
            suite, _ = load_test_suite_from_name(
                '%s.test_foo' % self.test_module_name
            )

        self.assertEqual(1, suite.countTestCases())

    @patch('autopilot.run._show_test_locations', new=lambda a: True)
    def test_load_test_suite_from_name_only_loads_requested_suite(self):
        self.create_empty_package_file('__init__.py')
        self.create_package_file_with_contents('test_foo.py', SIMPLE_TESTCASE)
        self.create_package_file_with_contents('test_bar.py', SIMPLE_TESTCASE)
        with working_dir(self.sandbox_dir):
            suite, _ = load_test_suite_from_name(
                '%s.test_bar' % self.test_module_name
            )

        self.assertEqual(1, suite.countTestCases())

    @patch('autopilot.run._show_test_locations', new=lambda a: True)
    def test_load_test_suite_from_name_loads_requested_test_from_suite(self):
        self.create_empty_package_file('__init__.py')
        self.create_package_file_with_contents('test_foo.py', SAMPLE_TESTCASES)
        self.create_package_file_with_contents('test_bar.py', SAMPLE_TESTCASES)
        with working_dir(self.sandbox_dir):
            suite, _ = load_test_suite_from_name(
                '%s.test_bar.SampleTests.test_passes_again'
                % self.test_module_name
            )

        self.assertEqual(1, suite.countTestCases())

    @patch('autopilot.run._handle_discovery_error')
    @patch('autopilot.run._show_test_locations', new=lambda a: True)
    def test_loading_nonexistent_test_suite_doesnt_error(self, err_handler):
        self.assertThat(
            lambda: load_test_suite_from_name('nonexistent'),
            Not(Raises())
        )

    def test_loading_nonexistent_test_suite_indicates_error(self):
        self.assertRaises(
            ImportError,
            lambda: _discover_test('nonexistent')
        )

    @patch('autopilot.run._reexecute_autopilot_using_module')
    @patch('autopilot.run._is_testing_autopilot_module', new=lambda *a: True)
    def test_testing_autopilot_is_redirected(self, patched_executor):
        patched_executor.return_value = 0
        self.assertRaises(
            SystemExit,
            lambda: load_test_suite_from_name('autopilot')
        )
        self.assertTrue(patched_executor.called)


SIMPLE_TESTCASE = """\

from unittest import TestCase


class SimpleTests(TestCase):

    def test_passes(self):
        self.assertEqual(1, 1)
"""

SAMPLE_TESTCASES = """\

from unittest import TestCase


class SampleTests(TestCase):

    def test_passes(self):
        self.assertEqual(1, 1)

    def test_passes_again(self):
        self.assertEqual(1, 1)
"""
