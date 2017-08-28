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


"""
.. otto:: **Deprecated Namespace!**

    This module contains modules that were in the ``autopilot.emulators``
    package in autopilot version 1.2 and earlier, but have now been moved to
    the ``autopilot`` package.

    This module exists to ease the transition to autopilot 1.3, but is not
    guaranteed to exist in the future.

    .. seealso::

        Modulule :mod:`autopilot.display`
            Get display information.
        Module :mod:`autopilot.input`
            Create input events to interact with the application under test.

"""

import autopilot.display as display  # flake8: noqa
import autopilot.clipboard as clipboard  # flake8: noqa
import autopilot.dbus_handler as dbus_handler  # flake8: noqa
import autopilot.input as input  # flake8: noqa
