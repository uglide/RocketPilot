#!/usr/bin/env python3

#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2014 Canonical
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
from setuptools import find_packages, setup, Extension

import sys
assert sys.version_info >= (3,), 'Python 3 is required'


VERSION = '1.6.0'


setup(
    name='autopilot',
    version=VERSION,
    description='Functional testing tool for Ubuntu.',
    author='Thomi Richards',
    author_email='thomi.richards@canonical.com',
    url='https://launchpad.net/autopilot',
    license='GPLv3',
    packages=find_packages(),
    test_suite='autopilot.tests',
    scripts=['bin/autopilot3-sandbox-run'],
    ext_modules=[],
    entry_points={
        'console_scripts': ['autopilot3 = autopilot.run:main']
    }
)
