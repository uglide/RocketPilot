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

"""Autopilot Exceptions.

This module contains exceptions that autopilot may raise in various conditions.
Each exception is documented with when it is raised: a generic description in
this module, as well as a detailed description in the function or method that
raises it.

"""


class BackendException(RuntimeError):

    """An error occured while trying to initialise an autopilot backend."""

    def __init__(self, original_exception):
        super(BackendException, self).__init__(
            "Error while initialising backend. Original exception was: " +
            str(original_exception))
        self.original_exception = original_exception


class ProcessSearchError(RuntimeError):
    """Object introspection error occured."""
    pass


class StateNotFoundError(RuntimeError):

    """Raised when a piece of state information is not found.

    This exception is commonly raised when the application has destroyed (or
    not yet created) the object you are trying to access in autopilot. This
    typically happens for a number of possible reasons:

    * The UI widget you are trying to access with
      :py:meth:`~autopilot.introspection.ProxyBase.select_single` or
      :py:meth:`~autopilot.introspection.ProxyBase.wait_select_single` or
      :py:meth:`~autopilot.introspection.ProxyBase.select_many` does not exist
      yet.

    * The UI widget you are trying to access has been destroyed by the
      application.

    """

    def __init__(self, class_name=None, **filters):
        """Construct a StateNotFoundError.

        :raises ValueError: if neither the class name not keyword arguments
            are specified.

        """
        if class_name is None and not filters:
            raise ValueError("Must specify either class name or filters.")

        if class_name is None:
            self._message = \
                "Object not found with properties {}.".format(
                    repr(filters)
                )
        elif not filters:
            self._message = "Object not found with name '{}'.".format(
                class_name
            )
        else:
            self._message = \
                "Object not found with name '{}' and properties {}.".format(
                    class_name,
                    repr(filters)
                )

    _troubleshoot_url_message = (
        'Tips on minimizing the occurrence of this failure '
        'are available here: '
        'https://developer.ubuntu.com/api/autopilot/python/1.6.0/'
        'faq-troubleshooting/'
    )

    def __str__(self):
        return '{}\n\n{}'.format(
            self._message,
            self._troubleshoot_url_message
        )


class InvalidXPathQuery(ValueError):

    """Raised when an XPathselect query is invalid or unsupported."""
