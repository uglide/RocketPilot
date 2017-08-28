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


import fixtures
import glob
from functools import partial
import logging
import os
import signal
import subprocess

from testtools.matchers import NotEquals

from autopilot.matchers import Eventually
from autopilot.utilities import safe_text_content


logger = logging.getLogger(__name__)


class RMDVideoLogFixture(fixtures.Fixture):

    """Video capture autopilot tests, saving the results if the test failed."""

    _recording_app = '/usr/bin/recordmydesktop'
    _recording_opts = ['--no-sound', '--no-frame', '-o']

    def __init__(self, recording_directory, test_instance):
        super().__init__()
        self.recording_directory = recording_directory
        self.test_instance = test_instance

    def setUp(self):
        super().setUp()
        self._test_passed = True

        if not self._have_recording_app():
            logger.warning(
                "Disabling video capture since '%s' is not present",
                self._recording_app)

        self.test_instance.addOnException(self._on_test_failed)
        self.test_instance.addCleanup(
            self._stop_video_capture,
            self.test_instance
        )
        self._start_video_capture(self.test_instance.shortDescription())

    def _have_recording_app(self):
        return os.path.exists(self._recording_app)

    def _start_video_capture(self, test_id):
        args = self.get_capture_command_line()
        self._capture_file = os.path.join(
            self.recording_directory,
            '%s.ogv' % (test_id)
        )
        _ensure_directory_exists_but_not_file(self._capture_file)
        args.append(self._capture_file)
        video_session_pattern = '/tmp/rMD-session*'
        orig_sessions = glob.glob(video_session_pattern)
        logger.debug("Starting: %r", args)
        self._capture_process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        # wait until rmd session directory is created
        Eventually(NotEquals(orig_sessions)).match(
            lambda: glob.glob(video_session_pattern)
        )

    def _stop_video_capture(self, test_instance):
        """Stop the video capture. If the test failed, save the resulting
        file."""

        if self._test_passed:
            # SIGABRT terminates the program and removes
            # the specified output file.
            self._capture_process.send_signal(signal.SIGABRT)
            self._capture_process.wait()
        else:
            self._capture_process.terminate()
            self._capture_process.wait()
            if self._capture_process.returncode != 0:
                test_instance.addDetail(
                    'video capture log',
                    safe_text_content(self._capture_process.stdout.read()))
        self._capture_process = None
        self._currently_recording_description = None

    def _on_test_failed(self, ex_info):
        """Called when a test fails."""
        from unittest.case import SkipTest
        failure_class_type = ex_info[0]
        if failure_class_type is not SkipTest:
            self._test_passed = False

    def get_capture_command_line(self):
        return [self._recording_app] + self._recording_opts

    def set_recording_dir(self, dir):
        self.recording_directory = dir


def _have_video_recording_facilities():
    call_ret_code = subprocess.call(
        ['which', 'recordmydesktop'],
        stdout=subprocess.PIPE
    )
    return call_ret_code == 0


def _ensure_directory_exists_but_not_file(file_path):
    dirpath = os.path.dirname(file_path)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)
    elif os.path.exists(file_path):
        logger.warning(
            "Video capture file '%s' already exists, deleting.", file_path)
        os.remove(file_path)


class DoNothingFixture(fixtures.Fixture):
    def __init__(self, arg):
        pass


VideoLogFixture = DoNothingFixture


def configure_video_recording(args):
    """Configure video recording based on contents of ``args``.

    :raises RuntimeError: If the user asked for video recording, but the
        system does not support video recording.

    """
    global VideoLogFixture

    if args.record_directory:
        args.record = True

    if not args.record:
        # blank fixture when recording is not enabled
        VideoLogFixture = DoNothingFixture
    else:
        if not args.record_directory:
            args.record_directory = '/tmp/autopilot'

        if not _have_video_recording_facilities():
            raise RuntimeError(
                "The application 'recordmydesktop' needs to be installed to "
                "record failing jobs."
            )

        VideoLogFixture = partial(RMDVideoLogFixture, args.record_directory)


def get_video_recording_fixture():
    return VideoLogFixture
