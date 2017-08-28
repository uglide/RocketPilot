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

"""This module contains support for capturing screenshots."""

import logging
import os
import subprocess
import time
import tempfile
from io import BytesIO

from PIL import Image

import autopilot._glib

logger = logging.getLogger(__name__)


def get_screenshot_data(display_type):
    """Return a BytesIO object of the png data for the screenshot image.

    *display_type* is the display server type. supported values are:
      - "X11"
      - "MIR"

    :raises RuntimeError: If attempting to capture an image on an unsupported
      display server.
    :raises RuntimeError: If saving image data to file-object fails.

    """

    if display_type == "MIR":
        return _get_screenshot_mir()
    elif display_type == "X11":
        return _get_screenshot_x11()
    else:
        raise RuntimeError(
            "Don't know how to take screen shot for this display server: {}"
            .format(display_type)
        )


def _get_screenshot_x11():
    """Capture screenshot from an X11 display.

    :raises RuntimeError: If saving pixbuf to fileobject fails.

    """
    pixbuf_data = _get_x11_pixbuf_data()
    return _save_gdk_pixbuf_to_fileobject(pixbuf_data)


def _get_x11_pixbuf_data():
    Gdk = autopilot._glib._import_gdk()
    window = Gdk.get_default_root_window()
    x, y, width, height = window.get_geometry()
    return Gdk.pixbuf_get_from_window(window, x, y, width, height)


def _save_gdk_pixbuf_to_fileobject(pixbuf):
    image_data = pixbuf.save_to_bufferv("png", [], [])
    if image_data[0] is True:
        image_datafile = BytesIO()
        image_datafile.write(image_data[1])
        image_datafile.seek(0)
        return image_datafile

    logger.error("Unable to write image data.")
    raise RuntimeError("Failed to save image data to file object.")


def _get_screenshot_mir():
    """Capture screenshot from Mir display.

    :raises FileNotFoundError: If the mirscreencast utility is not found.
    :raises CalledProcessError: If the mirscreencast utility errors while
      taking a screenshot.
    :raises ValueError: If the PNG conversion step fails.

    """
    from autopilot.display import Display
    display_resolution = Display.create().get_screen_geometry(0)[2:]
    screenshot_filepath = _take_mirscreencast_screenshot()
    try:
        png_data_file = _get_png_from_rgba_file(
            screenshot_filepath,
            display_resolution
        )
    finally:
        os.remove(screenshot_filepath)

    return png_data_file


def _take_mirscreencast_screenshot():
    """Takes a single frame capture of the screen using mirscreencast.

    Return the path to the resulting rgba file.

    :raises FileNotFoundError: If the mirscreencast utility is not found.
    :raises CalledProcessError: If the mirscreencast utility errors while
      taking a screenshot.

    """
    timestamp = int(time.time())
    filename = "ap-screenshot-data-{ts}.rgba".format(ts=timestamp)

    filepath = os.path.join(tempfile.gettempdir(), filename)

    try:
        subprocess.check_call([
            "mirscreencast",
            "-m", "/run/mir_socket",
            "-n", "1",
            "-f", filepath
        ])
    except FileNotFoundError as e:
        e.args += ("The utility 'mirscreencast' is not available.", )
        raise
    except subprocess.CalledProcessError as e:
        e.args += ("Failed to take screenshot.", )
        raise

    return filepath


# This currently uses PIL but I'm investigating using something
# quicker/lighter-weight.
def _get_png_from_rgba_file(filepath, image_size):
    """Convert an rgba file to a png file stored in a filelike object.

    Returns a BytesIO object containing the png data.

    """
    image_data = _image_data_from_file(filepath, image_size)
    bio = BytesIO()
    image_data.save(bio, format="png")
    bio.seek(0)

    return bio


def _image_data_from_file(filepath, image_size):
    with open(filepath, "rb") as f:
        image_data = Image.frombuffer(
            "RGBA", image_size, f.read(), "raw", "RGBA", 0, 1
        )
    return image_data
