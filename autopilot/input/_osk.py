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

import logging
from contextlib import contextmanager

from ubuntu_keyboard.emulators.keyboard import Keyboard as KeyboardDriver

from autopilot.input import Keyboard as KeyboardBase
from autopilot.utilities import sleep


_logger = logging.getLogger(__name__)


class Keyboard(KeyboardBase):

    _keyboard = KeyboardDriver()

    @contextmanager
    def focused_type(self, input_target, pointer=None):
        """Ensures that the keyboard is up and ready for input as well as
        dismisses the keyboard afterward.

        """
        with super(Keyboard, self).focused_type(input_target, pointer):
            try:
                self._keyboard.wait_for_keyboard_ready()
                yield self
            finally:
                self._keyboard.dismiss()

    def press(self, keys, delay=0.2):
        raise NotImplementedError(
            "OSK Backend does not support the press method"
        )

    def release(self, keys, delay=0.2):
        raise NotImplementedError(
            "OSK Backend does not support the release method"
        )

    def press_and_release(self, key, delay=0.2):
        """Press and release the key *key*.

        The 'key' argument must be a string of the single key you want pressed
        and released.

        For example::

            press_and_release('A')

        presses then releases the 'A' key.

        :raises: *ValueError* if the provided key is not supported by the
         OSK Backend (or the current OSK langauge layout).

        :raises: *ValueError* if there is more than a single key supplied in
         the *key* argument.

        """

        if len(self._sanitise_keys(key)) != 1:
            raise ValueError("Only a single key can be passed in.")

        try:
            self._keyboard.press_key(key)
            sleep(delay)
        except ValueError as e:
            e.args += ("OSK Backend is unable to type the key '%s" % key,)
            raise

    def type(self, string, delay=0.1):
        """Simulate a user typing a string of text.

        Only 'normal' keys can be typed with this method. There is no such
        thing as Alt or Ctrl on the Onscreen Keyboard.

        The OSK class back end will take care of ensuring that capitalized
        keys are in fact capitalized.

        :raises: *ValueError* if there is a key within the string that is
        not supported by the OSK Backend (or the current OSK langauge layout.)

        """
        if not isinstance(string, str):
            raise TypeError("'string' argument must be a string.")
        _logger.debug("Typing text: %s", string)
        self._keyboard.type(string, delay)

    @classmethod
    def on_test_end(cls, test_instance):
        """Dismiss (swipe hide) the keyboard.

        """
        _logger.debug("Dismissing the OSK with a swipe.")
        cls._keyboard.dismiss()

    def _sanitise_keys(self, keys):
        if keys == '+':
            return [keys]
        else:
            return keys.split('+')
