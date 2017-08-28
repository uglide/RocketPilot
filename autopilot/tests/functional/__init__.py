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


from codecs import open
import os
import os.path
import sys
import logging
from shutil import rmtree
import subprocess
from tempfile import mkdtemp, mktemp
from testtools.content import text_content


from autopilot import platform
from autopilot.tests.functional.fixtures import TempDesktopFile
from autopilot.testcase import AutopilotTestCase


def remove_if_exists(path):
    if os.path.exists(path):
        if os.path.isdir(path):
            rmtree(path)
        else:
            os.remove(path)


logger = logging.getLogger(__name__)


class AutopilotRunTestBase(AutopilotTestCase):

    """The base class for the autopilot functional tests."""

    def setUp(self):
        super(AutopilotRunTestBase, self).setUp()
        self.base_path = self.create_empty_test_module()

    def create_empty_test_module(self):
        """Create an empty temp directory, with an empty test directory inside
        it.

        This method handles cleaning up the directory once the test completes.

        Returns the full path to the temp directory.

        """

        # create the base directory:
        base_path = mkdtemp()
        self.addDetail('base path', text_content(base_path))
        self.addCleanup(rmtree, base_path)

        # create the tests directory:
        os.mkdir(
            os.path.join(base_path, 'tests')
        )

        # make tests importable:
        open(
            os.path.join(
                base_path,
                'tests',
                '__init__.py'),
            'w').write('# Auto-generated file.')
        return base_path

    def run_autopilot(self, arguments, pythonpath="", use_script=False):
        environment_patch = _get_environment_patch(pythonpath)

        if use_script:
            arg = [sys.executable, self._write_setup_tools_script()]
        else:
            arg = [sys.executable, '-m', 'autopilot.run']

        environ = os.environ.copy()
        environ.update(environment_patch)

        logger.info("Starting autopilot command with:")
        logger.info("Autopilot command = %s", ' '.join(arg))
        logger.info("Arguments = %s", arguments)
        logger.info("CWD = %r", self.base_path)

        arg.extend(arguments)
        process = subprocess.Popen(
            arg,
            cwd=self.base_path,
            env=environ,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        stdout, stderr = process.communicate()
        retcode = process.poll()

        self.addDetail('retcode', text_content(str(retcode)))
        self.addDetail(
            'stdout',
            text_content(stdout)
        )
        self.addDetail(
            'stderr',
            text_content(stderr)
        )

        return (retcode, stdout, stderr)

    def create_test_file(self, name, contents):
        """Create a test file with the given name and contents.

        'name' must end in '.py' if it is to be importable.
        'contents' must be valid python code.

        """
        open(
            os.path.join(
                self.base_path,
                'tests',
                name),
            'w',
            encoding='utf8').write(contents)

    def _write_setup_tools_script(self):
        """Creates a python script that contains the setup entry point."""
        base_path = mkdtemp()
        self.addCleanup(rmtree, base_path)

        script_file = os.path.join(base_path, 'autopilot')
        open(script_file, 'w').write(load_entry_point_script)

        return script_file


def _get_environment_patch(pythonpath):
    environment_patch = dict(DISPLAY=':0')

    ap_base_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '..',
            '..',
            '..'
        )
    )

    pythonpath_additions = []
    if pythonpath:
        pythonpath_additions.append(pythonpath)
    if not ap_base_path.startswith('/usr/'):
        pythonpath_additions.append(ap_base_path)
    environment_patch['PYTHONPATH'] = ":".join(pythonpath_additions)

    return environment_patch


load_entry_point_script = """\
#!/usr/bin/python
__requires__ = 'autopilot==1.6.0'
import sys
from pkg_resources import load_entry_point

if __name__ == '__main__':
    sys.exit(
        load_entry_point('autopilot==1.6.0', 'console_scripts', 'autopilot3')()
    )
"""


class QmlScriptRunnerMixin(object):

    """A Mixin class that knows how to get a proxy object for a qml script."""

    def start_qml_script(self, script_contents):
        """Launch a qml script."""
        qml_path = mktemp(suffix='.qml')
        open(qml_path, 'w').write(script_contents)
        self.addCleanup(os.remove, qml_path)

        extra_args = ''
        if platform.model() != "Desktop":
            # We need to add the desktop-file-hint
            desktop_file = self.useFixture(
                TempDesktopFile()
            ).get_desktop_file_path()
            extra_args = '--desktop_file_hint={hint_file}'.format(
                hint_file=desktop_file
            )

        return self.launch_test_application(
            "qmlscene",
            "-qt=qt5",
            qml_path,
            extra_args,
            app_type='qt',
        )
