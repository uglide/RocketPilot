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

"""Content objects and helpers for autopilot tests."""

import io

import logging
from testtools.content import ContentType, content_from_stream
from autopilot.utilities import safe_text_content

_logger = logging.getLogger(__name__)


def follow_file(path, test_case, content_name=None):
    """Start monitoring a file.

    Use this convenience function to attach the contents of a file to a test.

    :param path: The path to the file on disk you want to monitor.
    :param test_case: An object that supports attaching details and cleanup
        actions (i.e.- has the ``addDetail`` and ``addCleanup`` methods).
    :param content_name: A name to give this content. If not specified, the
        file path will be used instead.
    """
    try:
        file_obj = io.open(path, mode='rb')
    except IOError as e:
        _logger.error(
            "Could not add content object '%s' due to IO Error: %s",
            content_name,
            str(e)
        )
        return safe_text_content('')
    else:
        file_obj.seek(0, io.SEEK_END)
        return follow_stream(
            file_obj,
            test_case,
            content_name or file_obj.name
        )


def follow_stream(stream, test_case, content_name):
    """Start monitoring the content from a stream.

    This function can be used to attach a portion of a stream to a test.

    :param stream: an open file-like object (that supports a read method that
        returns bytes).
    :param test_case: An object that supports attaching details and cleanup
        actions (i.e.- has the ``addDetail`` and ``addCleanup`` methods).
    :param content_name: A name to give this content. If not specified, the
        file path will be used instead.
    """
    def make_content():
        content_obj = content_from_stream(
            stream,
            ContentType('text', 'plain', {'charset': 'iso8859-1'}),
            buffer_now=True
        )

        # Work around a bug in older testtools where an empty file would result
        # in None being decoded and exploding.
        # See: https://bugs.launchpad.net/autopilot/+bug/1517289
        if list(content_obj.iter_text()) == []:
            _logger.warning('Followed stream is empty.')
            content_obj = safe_text_content('Unable to read file data.')

        test_case.addDetail(content_name, content_obj)
    test_case.addCleanup(make_content)
