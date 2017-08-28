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

"""Tests for the autopilot platform code."""


from io import StringIO
from testtools import TestCase
from testtools.matchers import Equals
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import autopilot.platform as platform


class PublicAPITests(TestCase):

    def setUp(self):
        super().setUp()

    @patch('autopilot.platform._PlatformDetector')
    def test_model_creates_platform_detector(self, mock_detector):
        platform.model()
        mock_detector.create.assert_called_once_with()

    @patch('autopilot.platform._PlatformDetector._cached_detector')
    def test_model_returns_correct_value(self, mock_detector):
        mock_detector.model = "test123"
        self.assertThat(platform.model(), Equals('test123'))

    @patch('autopilot.platform._PlatformDetector')
    def test_image_codename_creates_platform_detector(self, mock_detector):
        platform.image_codename()
        mock_detector.create.assert_called_once_with()

    @patch('autopilot.platform._PlatformDetector._cached_detector')
    def test_image_codename_returns_correct_value(self, mock_detector):
        mock_detector.image_codename = "test123"
        self.assertThat(platform.image_codename(), Equals('test123'))


class PlatformGetProcessNameTests(TestCase):

    def test_returns_callable_value(self):
        test_callable = lambda: "foo"
        self.assertEqual("foo", platform._get_process_name(test_callable))

    def test_returns_string(self):
        self.assertEqual("foo", platform._get_process_name("foo"))

    def test_raises_exception_if_unsupported_passed(self):
        self.assertRaises(ValueError, platform._get_process_name, 0)


class PlatformDetectorTests(TestCase):

    def setUp(self):
        super(PlatformDetectorTests, self).setUp()
        # platform detector is cached, so make sure we destroy the cache before
        # each test runs, and after each test completes.
        self._destroy_platform_detector_cache()
        self.addCleanup(self._destroy_platform_detector_cache)

    def _destroy_platform_detector_cache(self):
        platform._PlatformDetector._cached_detector = None

    def test_platform_detector_is_cached(self):
        """Test that the platform detector is only created once."""
        detector1 = platform._PlatformDetector.create()
        detector2 = platform._PlatformDetector.create()
        self.assertThat(id(detector1), Equals(id(detector2)))

    @patch('autopilot.platform._get_property_file')
    def test_default_model(self, mock_get_property_file):
        """The default model name must be 'Desktop'."""
        mock_get_property_file.return_value = None

        detector = platform._PlatformDetector.create()
        self.assertThat(detector.model, Equals('Desktop'))

    @patch('autopilot.platform._get_property_file')
    def test_default_image_codename(self, mock_get_property_file):
        """The default image codename must be 'Desktop'."""
        mock_get_property_file.return_value = None

        detector = platform._PlatformDetector.create()
        self.assertThat(detector.image_codename, Equals('Desktop'))

    @patch('autopilot.platform._get_property_file')
    def test_model_is_set_from_property_file(self, mock_get_property_file):
        """Detector must read product model from android properties file."""
        mock_get_property_file.return_value = StringIO(
            "ro.product.model=test123")

        detector = platform._PlatformDetector.create()
        self.assertThat(detector.model, Equals('test123'))

    @patch('autopilot.platform._get_property_file', new=lambda: StringIO(""))
    def test_model_has_default_when_not_in_property_file(self):
        """Detector must use 'Desktop' as a default value for the model name
        when the property file exists, but does not contain a model
        description.

        """
        detector = platform._PlatformDetector.create()
        self.assertThat(detector.model, Equals('Desktop'))

    @patch('autopilot.platform._get_property_file')
    def test_product_codename_is_set_from_property_file(
            self, mock_get_property_file):
        """Detector must read product model from android properties file."""
        mock_get_property_file.return_value = StringIO(
            "ro.product.name=test123")

        detector = platform._PlatformDetector.create()
        self.assertThat(detector.image_codename, Equals('test123'))

    @patch('autopilot.platform._get_property_file', new=lambda: StringIO(""))
    def test_product_codename_has_default_when_not_in_property_file(self):
        """Detector must use 'Desktop' as a default value for the product
        codename when the property file exists, but does not contain a model
        description.

        """
        detector = platform._PlatformDetector.create()
        self.assertThat(detector.image_codename, Equals('Desktop'))

    def test_has_correct_file_name(self):
        observed = platform._get_property_file_path()
        self.assertEqual("/system/build.prop", observed)

    def test_get_property_file_opens_path(self):
        token = self.getUniqueString()
        with NamedTemporaryFile(mode='w+') as f:
            f.write(token)
            f.flush()
            with patch('autopilot.platform._get_property_file_path') as p:
                p.return_value = f.name
                observed = platform._get_property_file().read()
        self.assertEqual(token, observed)

    @patch('autopilot.platform._get_property_file')
    def test_get_tablet_from_property_file(
            self, mock_get_property_file):
        """Detector must read tablet from android properties file."""
        mock_get_property_file.return_value = StringIO(
            "ro.build.characteristics=tablet")

        detector = platform._PlatformDetector.create()
        self.assertThat(detector.is_tablet, Equals(True))

    @patch('autopilot.platform._get_property_file')
    def test_get_not_tablet_from_property_file(
            self, mock_get_property_file):
        """Detector must read lack of tablet from android properties file."""
        mock_get_property_file.return_value = StringIO(
            "ro.build.characteristics=nosdcard")

        detector = platform._PlatformDetector.create()
        self.assertThat(detector.is_tablet, Equals(False))

    @patch('autopilot.platform._get_property_file')
    def test_tablet_without_property_file(self, mock_get_property_file):
        """Detector must return False for tablet when there is no properties
        file.

        """
        mock_get_property_file.return_value = None

        detector = platform._PlatformDetector.create()
        self.assertThat(detector.is_tablet, Equals(False))


class BuildPropertyParserTests(TestCase):
    """Tests for the android build properties file parser."""

    def test_empty_file_returns_empty_dictionary(self):
        """An empty file must result in an empty dictionary."""
        prop_file = StringIO("")
        properties = platform._parse_build_properties_file(prop_file)
        self.assertThat(len(properties), Equals(0))

    def test_whitespace_is_ignored(self):
        """Whitespace in build file must be ignored."""
        prop_file = StringIO("\n\n\n\n\n")
        properties = platform._parse_build_properties_file(prop_file)
        self.assertThat(len(properties), Equals(0))

    def test_comments_are_ignored(self):
        """Comments in build file must be ignored."""
        prop_file = StringIO("# Hello World\n #Hello Again\n#####")
        properties = platform._parse_build_properties_file(prop_file)
        self.assertThat(len(properties), Equals(0))

    def test_invalid_lines_are_ignored(self):
        """lines without ana ssignment must be ignored."""
        prop_file = StringIO("Hello")
        properties = platform._parse_build_properties_file(prop_file)
        self.assertThat(len(properties), Equals(0))

    def test_simple_value(self):
        """Test a simple a=b expression."""
        prop_file = StringIO("a=b")
        properties = platform._parse_build_properties_file(prop_file)
        self.assertThat(properties, Equals(dict(a='b')))

    def test_multiple_values(self):
        """Test several expressions over multiple lines."""
        prop_file = StringIO("a=b\nb=23")
        properties = platform._parse_build_properties_file(prop_file)
        self.assertThat(properties, Equals(dict(a='b', b='23')))

    def test_values_with_equals_in_them(self):
        """Test that we can parse values with a '=' in them."""
        prop_file = StringIO("a=b=c")
        properties = platform._parse_build_properties_file(prop_file)
        self.assertThat(properties, Equals(dict(a='b=c')))

    def test_dotted_values_work(self):
        """Test that we can use dotted values as the keys."""
        prop_file = StringIO("ro.product.model=maguro")
        properties = platform._parse_build_properties_file(prop_file)
        self.assertThat(properties, Equals({'ro.product.model': 'maguro'}))
