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

"""Base module or application environment setup."""

import fixtures
import os


class ApplicationEnvironment(fixtures.Fixture):

    def prepare_environment(self, app_path, arguments):
        """Prepare the application, or environment to launch with
        autopilot-support.

        The method *must* return a tuple of (*app_path*, *arguments*). Either
        of these can be altered by this method.

        """
        raise NotImplementedError("Sub-classes must implement this method.")


class GtkApplicationEnvironment(ApplicationEnvironment):

    def prepare_environment(self, app_path, arguments):
        """Prepare the application, or environment to launch with
        autopilot-support.

        :returns: unmodified app_path and arguments

        """
        modules = os.getenv('GTK_MODULES', '').split(':')
        if 'autopilot' not in modules:
            modules.append('autopilot')
            os.putenv('GTK_MODULES', ':'.join(modules))

        return app_path, arguments


class QtApplicationEnvironment(ApplicationEnvironment):

    def prepare_environment(self, app_path, arguments):
        """Prepare the application, or environment to launch with
        autopilot-support.

        :returns: unmodified app_path and arguments

        """
        if '-testability' not in arguments:
            insert_pos = 0
            for pos, argument in enumerate(arguments):
                if argument.startswith("-qt="):
                    insert_pos = pos + 1
                    break
            arguments.insert(insert_pos, '-testability')

        return app_path, arguments
