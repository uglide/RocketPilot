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

"""Unit tests for the display screenshot functionality."""


import subprocess
import tempfile
import os
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from testtools import TestCase, skipIf
from testtools.matchers import (
    Equals,
    FileExists,
    MatchesRegex,
    Not,
    StartsWith,
    raises,
)
from unittest.mock import Mock, patch

import autopilot.display._screenshot as _ss
from autopilot import platform


class ScreenShotTests(TestCase):

    def test_get_screenshot_data_raises_RuntimeError_on_unknown_display(self):
        self.assertRaises(RuntimeError, lambda: _ss.get_screenshot_data(""))


class X11ScreenShotTests(TestCase):

    def get_pixbuf_that_mocks_saving(self, success, data):
        pixbuf_obj = Mock()
        pixbuf_obj.save_to_bufferv.return_value = (success, data)

        return pixbuf_obj

    @skipIf(platform.model() != "Desktop", "Only available on desktop.")
    def test_save_gdk_pixbuf_to_fileobject_raises_error_if_save_failed(self):
        pixbuf_obj = self.get_pixbuf_that_mocks_saving(False, None)
        with patch.object(_ss, 'logger') as p_log:
            self.assertRaises(
                RuntimeError,
                lambda: _ss._save_gdk_pixbuf_to_fileobject(pixbuf_obj)
            )
            p_log.error.assert_called_once_with("Unable to write image data.")

    def test_save_gdk_pixbuf_to_fileobject_returns_data_object(self):
        expected_data = b"Tests Rock"
        pixbuf_obj = self.get_pixbuf_that_mocks_saving(True, expected_data)

        data_object = _ss._save_gdk_pixbuf_to_fileobject(pixbuf_obj)

        self.assertThat(data_object, Not(Equals(None)))
        self.assertEqual(data_object.tell(), 0)
        self.assertEqual(data_object.getvalue(), expected_data)


class MirScreenShotTests(TestCase):

    def test_take_screenshot_raises_when_binary_not_available(self):
        with patch.object(_ss.subprocess, 'check_call') as check_call:
            check_call.side_effect = FileNotFoundError()

            self.assertThat(
                _ss._take_mirscreencast_screenshot,
                raises(
                    FileNotFoundError(
                        "The utility 'mirscreencast' is not available."
                    )
                )
            )

    def test_take_screenshot_raises_when_screenshot_fails(self):
        with patch.object(_ss.subprocess, 'check_call') as check_call:
            check_call.side_effect = subprocess.CalledProcessError(None, None)

            self.assertThat(
                _ss._take_mirscreencast_screenshot,
                raises(
                    subprocess.CalledProcessError(
                        None, None, "Failed to take screenshot."
                    )
                )
            )

    def test_take_screenshot_returns_resulting_filename(self):
        with patch.object(_ss.subprocess, 'check_call'):
            self.assertThat(
                _ss._take_mirscreencast_screenshot(),
                MatchesRegex(".*ap-screenshot-data-\d+.rgba")
            )

    def test_take_screenshot_filepath_is_in_tmp_dir(self):
        with patch.object(_ss.subprocess, 'check_call'):
            self.assertThat(
                _ss._take_mirscreencast_screenshot(),
                StartsWith(tempfile.gettempdir())
            )

    def test_image_data_from_file_returns_PIL_Image(self):
        with _single_pixel_rgba_data_file() as filepath:
            image_data = _ss._image_data_from_file(filepath, (1, 1))
        self.assertEqual(image_data.mode, "RGBA")
        self.assertEqual(image_data.size, (1, 1))

    def test_get_png_from_rgba_file_returns_png_file(self):
        with _single_pixel_rgba_data_file() as filepath:
            png_image_data = _ss._get_png_from_rgba_file(filepath, (1, 1))

            self.assertEqual(0, png_image_data.tell())
            self.assertThat(png_image_data.read(), StartsWith(b'\x89PNG\r\n'))

    @skipIf(platform.model() == "Desktop", "Only available on device.")
    def test_raw_data_file_cleaned_up_on_failure(self):
        """Creation of image will fail with a nonsense filepath."""
        with _simulate_bad_rgba_image_file() as image_file_path:
            self.assertRaises(ValueError, _ss._get_screenshot_mir)
            self.assertThat(image_file_path, Not(FileExists()))


@contextmanager
def _simulate_bad_rgba_image_file():
    try:
        with NamedTemporaryFile(delete=False) as f:
            with patch.object(_ss, "_take_mirscreencast_screenshot") as mir_ss:
                mir_ss.return_value = f.name
                yield f.name
    finally:
        if os.path.exists(f.name):
            os.remove(f.name)


@contextmanager
def _single_pixel_rgba_data_file():
    with NamedTemporaryFile() as f:
        f.write(b'<\x1e#\xff')
        f.seek(0)
        yield f.name
