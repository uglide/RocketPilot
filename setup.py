#!/usr/bin/env python3

#
# Rocketpilot Functional Test Tool
# Copyright (C) 2017 Igor Malinovskiy
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
from setuptools import find_packages, setup

import sys
assert sys.version_info >= (3,), 'Python 3 is required'


VERSION = '0.3.0'

dependencies = [
    'decorator==4.2.1',
    'psutil',
    'testtools',

    'PyUserInput @ https://github.com/uglide/PyUserInput/archive/master.zip',
    'pytz',
    'python-dateutil',
]

if sys.platform != 'win32':
    dependencies.append('dbus-python')


setup(
    name='rocketpilot',
    version=VERSION,
    description='Cross-platform tool for functional GUI testing of Qt applications '
                'based on Cannonical Autopilot project.',
    author='Igor Malinovskiy',
    author_email='u.glide@gmail.com',
    url='https://github.com/uglide/RocketPilot',
    license='GPLv3',
    install_requires=dependencies,
    packages=find_packages(),
    ext_modules=[],
    entry_points={
        'console_scripts': ['rocketpilot-vis = rocketpilot.vis:vis_main']
    }
)
