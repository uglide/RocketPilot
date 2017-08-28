# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012, 2013, 2014 Canonical
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


"""A collection of emulators for X11 - namely keyboards and mice.

In the future we may also need other devices.

"""

import logging

from autopilot.input import get_center_point
from autopilot.display import is_point_on_any_screen, move_mouse_to_screen
from autopilot.utilities import (
    EventDelay,
    Silence,
    sleep,
    StagnantStateDetector,
)
from autopilot.input import (
    Keyboard as KeyboardBase,
    Mouse as MouseBase,
)
from Xlib import X, XK
from Xlib.display import Display
from Xlib.ext.xtest import fake_input


_PRESSED_KEYS = []
_PRESSED_MOUSE_BUTTONS = []
_DISPLAY = None
_logger = logging.getLogger(__name__)


def get_display():
    """Return the Xlib display object.

    It is created (silently) if it doesn't exist.

    """
    global _DISPLAY
    if _DISPLAY is None:
        with Silence():
            _DISPLAY = Display()
    return _DISPLAY


def reset_display():
    global _DISPLAY
    _DISPLAY = None


class Keyboard(KeyboardBase):
    """Wrapper around xlib to make faking keyboard input possible."""

    _special_X_keysyms = {
        ' ': "space",
        '\t': "Tab",
        '\n': "Return",  # for some reason this needs to be cr, not lf
        '\r': "Return",
        '\e': "Escape",
        '\b': "BackSpace",
        '!': "exclam",
        '#': "numbersign",
        '%': "percent",
        '$': "dollar",
        '&': "ampersand",
        '"': "quotedbl",
        '\'': "apostrophe",
        '(': "parenleft",
        ')': "parenright",
        '*': "asterisk",
        '=': "equal",
        '+': "plus",
        ',': "comma",
        '-': "minus",
        '.': "period",
        '/': "slash",
        ':': "colon",
        ';': "semicolon",
        '<': "less",
        '>': "greater",
        '?': "question",
        '@': "at",
        '[': "bracketleft",
        ']': "bracketright",
        '\\': "backslash",
        '^': "asciicircum",
        '_': "underscore",
        '`': "grave",
        '{': "braceleft",
        '|': "bar",
        '}': "braceright",
        '~': "asciitilde"
    }

    _keysym_translations = {
        'Control': 'Control_L',
        'Ctrl': 'Control_L',
        'Alt': 'Alt_L',
        'AltR': 'Alt_R',
        'Super': 'Super_L',
        'Shift': 'Shift_L',
        'Enter': 'Return',
        'Space': ' ',
        'Backspace': 'BackSpace',
    }

    def __init__(self):
        super(Keyboard, self).__init__()
        self.shifted_keys = [k[1] for k in get_display()._keymap_codes if k]

    def press(self, keys, delay=0.2):
        """Send key press events only.

        :param string keys: Keys you want pressed.

        Example::

            press('Alt+F2')

        presses the 'Alt' and 'F2' keys.

        """
        if not isinstance(keys, str):
            raise TypeError("'keys' argument must be a string.")
        _logger.debug("Pressing keys %r with delay %f", keys, delay)
        for key in self.__translate_keys(keys):
            self.__perform_on_key(key, X.KeyPress)
            sleep(delay)

    def release(self, keys, delay=0.2):
        """Send key release events only.

        :param string keys: Keys you want released.

        Example::

            release('Alt+F2')

        releases the 'Alt' and 'F2' keys.

        """
        if not isinstance(keys, str):
            raise TypeError("'keys' argument must be a string.")
        _logger.debug("Releasing keys %r with delay %f", keys, delay)
        # release keys in the reverse order they were pressed in.
        keys = self.__translate_keys(keys)
        keys.reverse()
        for key in keys:
            self.__perform_on_key(key, X.KeyRelease)
            sleep(delay)

    def press_and_release(self, keys, delay=0.2):
        """Press and release all items in 'keys'.

        This is the same as calling 'press(keys);release(keys)'.

        :param string keys: Keys you want pressed and released.

        Example::

            press_and_release('Alt+F2')

        presses both the 'Alt' and 'F2' keys, and then releases both keys.

        """

        self.press(keys, delay)
        self.release(keys, delay)

    def type(self, string, delay=0.1):
        """Simulate a user typing a string of text.

        .. note:: Only 'normal' keys can be typed with this method. Control
         characters (such as 'Alt' will be interpreted as an 'A', and 'l',
         and a 't').

        """
        if not isinstance(string, str):
            raise TypeError("'keys' argument must be a string.")
        _logger.debug("Typing text %r", string)
        for key in string:
            # Don't call press or release here, as they translate keys to
            # keysyms.
            self.__perform_on_key(key, X.KeyPress)
            sleep(delay)
            self.__perform_on_key(key, X.KeyRelease)
            sleep(delay)

    @classmethod
    def on_test_end(cls, test_instance):
        """Generate KeyRelease events for any un-released keys.

        .. important:: Ensure you call this at the end of any test to release
         any keys that were pressed and not released.

        """
        global _PRESSED_KEYS
        for keycode in _PRESSED_KEYS:
            _logger.warning(
                "Releasing key %r as part of cleanup call.", keycode)
            fake_input(get_display(), X.KeyRelease, keycode)
        _PRESSED_KEYS = []

    def __perform_on_key(self, key, event):
        if not isinstance(key, str):
            raise TypeError("Key parameter must be a string")

        keycode = 0
        shift_mask = 0

        keycode, shift_mask = self.__char_to_keycode(key)

        if shift_mask != 0:
            fake_input(get_display(), event, 50)

        if event == X.KeyPress:
            _logger.debug("Sending press event for key: %s", key)
            _PRESSED_KEYS.append(keycode)
        elif event == X.KeyRelease:
            _logger.debug("Sending release event for key: %s", key)
            if keycode in _PRESSED_KEYS:
                _PRESSED_KEYS.remove(keycode)
            else:
                _logger.warning(
                    "Generating release event for keycode %d that was not "
                    "pressed.", keycode)

        fake_input(get_display(), event, keycode)
        get_display().sync()

    def __get_keysym(self, key):
        keysym = XK.string_to_keysym(key)
        if keysym == 0:
            # Unfortunately, although this works to get the correct keysym
            # i.e. keysym for '#' is returned as "numbersign"
            # the subsequent display.keysym_to_keycode("numbersign") is 0.
            keysym = XK.string_to_keysym(self._special_X_keysyms[key])
        return keysym

    def __is_shifted(self, key):
        return len(key) == 1 and ord(key) in self.shifted_keys and key != '<'

    def __char_to_keycode(self, key):
        keysym = self.__get_keysym(key)
        keycode = get_display().keysym_to_keycode(keysym)
        if keycode == 0:
            _logger.warning("Sorry, can't map '%s'", key)

        if (self.__is_shifted(key)):
            shift_mask = X.ShiftMask
        else:
            shift_mask = 0

        return keycode, shift_mask

    def __translate_keys(self, key_string):
        if len(key_string) > 1:
            return [self._keysym_translations.get(k, k)
                    for k in key_string.split('+')]
        else:
            # workaround that lets us press_and_release '+' by itself.
            return [self._keysym_translations.get(key_string, key_string)]


class Mouse(MouseBase):
    """Wrapper around xlib to make moving the mouse easier."""

    def __init__(self):
        super(Mouse, self).__init__()
        # Try to access the screen to see if X11 mouse is supported
        get_display()
        self.event_delayer = EventDelay()

    @property
    def x(self):
        """Mouse position X coordinate."""
        return self.position()[0]

    @property
    def y(self):
        """Mouse position Y coordinate."""
        return self.position()[1]

    def press(self, button=1):
        """Press mouse button at current mouse location."""
        _logger.debug("Pressing mouse button %d", button)
        _PRESSED_MOUSE_BUTTONS.append(button)
        fake_input(get_display(), X.ButtonPress, button)
        get_display().sync()

    def release(self, button=1):
        """Releases mouse button at current mouse location."""
        _logger.debug("Releasing mouse button %d", button)
        if button in _PRESSED_MOUSE_BUTTONS:
            _PRESSED_MOUSE_BUTTONS.remove(button)
        else:
            _logger.warning(
                "Generating button release event or button %d that was not "
                "pressed.", button)
        fake_input(get_display(), X.ButtonRelease, button)
        get_display().sync()

    def click(self, button=1, press_duration=0.10, time_between_events=0.1):
        """Click mouse at current location."""
        self.event_delayer.delay(time_between_events)
        self.press(button)
        sleep(press_duration)
        self.release(button)

    def move(self, x, y, animate=True, rate=10, time_between_events=0.01):
        """Moves mouse to location (x, y).

        Callers should avoid specifying the *rate* or *time_between_events*
        parameters unless they need a specific rate of movement.

        """
        def perform_move(x, y, sync):
            fake_input(
                get_display(),
                X.MotionNotify,
                sync,
                X.CurrentTime,
                X.NONE,
                x=int(x),
                y=int(y))
            get_display().sync()
            sleep(time_between_events)

        dest_x, dest_y = int(x), int(y)
        _logger.debug(
            "Moving mouse to position %d,%d %s animation.", dest_x, dest_y,
            "with" if animate else "without")

        if not animate:
            perform_move(dest_x, dest_y, False)
            return

        coordinate_valid = is_point_on_any_screen((dest_x, dest_y))
        if x < -1000 or y < -1000:
            raise ValueError(
                "Invalid mouse coordinates: %d, %d" % (dest_x, dest_y))

        loop_detector = StagnantStateDetector(threshold=1000)

        curr_x, curr_y = self.position()
        while curr_x != dest_x or curr_y != dest_y:
            dx = abs(dest_x - curr_x)
            dy = abs(dest_y - curr_y)

            intx = float(dx) / max(dx, dy)
            inty = float(dy) / max(dx, dy)

            step_x = min(rate * intx, dx)
            step_y = min(rate * inty, dy)

            if dest_x < curr_x:
                step_x *= -1
            if dest_y < curr_y:
                step_y *= -1

            perform_move(step_x, step_y, True)
            if coordinate_valid:
                curr_x, curr_y = self.position()
            else:
                curr_x += step_x
                curr_y += step_y

            try:
                loop_detector.check_state(curr_x, curr_y)
            except StagnantStateDetector.StagnantState as e:
                e.args = ("Mouse cursor is stuck.", )
                raise

        x, y = self.position()
        _logger.debug('The mouse is now at position %d,%d.', x, y)

    def move_to_object(self, object_proxy):
        """Attempts to move the mouse to 'object_proxy's centre point.

        See :py:meth:`~autopilot.input.get_center_point` for details on how
        the center point is calculated.

        """
        x, y = get_center_point(object_proxy)
        self.move(x, y)

    def position(self):
        """
        Returns the current position of the mouse pointer.

        :return: (x,y) tuple
        """

        coord = get_display().screen().root.query_pointer()._data
        x, y = coord["root_x"], coord["root_y"]
        return x, y

    def drag(self, x1, y1, x2, y2, rate=10, time_between_events=0.01):
        """Perform a press, move and release.

        This is to keep a common API between Mouse and Finger as long as
        possible.

        The pointer will be dragged from the starting point to the ending point
        with multiple moves. The number of moves, and thus the time that it
        will take to complete the drag can be altered with the `rate`
        parameter.

        :param x1: The point on the x axis where the drag will start from.
        :param y1: The point on the y axis where the drag will starts from.
        :param x2: The point on the x axis where the drag will end at.
        :param y2: The point on the y axis where the drag will end at.
        :param rate: The number of pixels the mouse will be moved per
            iteration. Default is 10 pixels. A higher rate will make the drag
            faster, and lower rate will make it slower.
        :param time_between_events: The number of seconds that the drag will
            wait between iterations.

        """
        self.move(x1, y1)
        self.press()
        self.move(x2, y2, rate=rate, time_between_events=time_between_events)
        self.release()

    @classmethod
    def on_test_end(cls, test_instance):
        """Put mouse in a known safe state."""
        global _PRESSED_MOUSE_BUTTONS
        for btn in _PRESSED_MOUSE_BUTTONS:
            _logger.debug("Releasing mouse button %d as part of cleanup", btn)
            fake_input(get_display(), X.ButtonRelease, btn)
        _PRESSED_MOUSE_BUTTONS = []
        move_mouse_to_screen(0)
