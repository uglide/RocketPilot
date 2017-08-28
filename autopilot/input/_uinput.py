# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012, 2013, 2014, 2015 Canonical
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

"""UInput device drivers."""

import logging

from evdev import UInput, ecodes as e

from autopilot.input import Keyboard as KeyboardBase
from autopilot.input import Touch as TouchBase
from autopilot.input import get_center_point
from autopilot.platform import model
from autopilot.utilities import deprecated, EventDelay, sleep


_logger = logging.getLogger(__name__)


def _get_devnode_path():
    """Return the uinput device node"""
    return '/dev/uinput'


class _UInputKeyboardDevice(object):
    """Wrapper for the UInput Keyboard to execute its primitives."""

    def __init__(self, device_class=UInput):
        super(_UInputKeyboardDevice, self).__init__()
        self._device = device_class(devnode=_get_devnode_path())
        self._pressed_keys_ecodes = []

    def press(self, key):
        """Press one key button.

        It ignores case, so, for example, 'a' and 'A' are mapped to the same
        key.

        """
        ecode = self._get_ecode_for_key(key)
        _logger.debug('Pressing %s (%r).', key, ecode)
        self._emit_press_event(ecode)
        self._pressed_keys_ecodes.append(ecode)

    def _get_ecode_for_key(self, key):
        key_name = key if key.startswith('KEY_') else 'KEY_' + key
        key_name = key_name.upper()
        ecode = e.ecodes.get(key_name, None)
        if ecode is None:
            raise ValueError('Unknown key name: %s.' % key)
        return ecode

    def _emit_press_event(self, ecode):
        press_value = 1
        self._emit(ecode, press_value)

    def _emit(self, ecode, value):
        self._device.write(e.EV_KEY, ecode, value)
        self._device.syn()

    def release(self, key):
        """Release one key button.

        It ignores case, so, for example, 'a' and 'A' are mapped to the same
        key.

        :raises ValueError: if ``key`` is not pressed.

        """
        ecode = self._get_ecode_for_key(key)
        if ecode in self._pressed_keys_ecodes:
            _logger.debug('Releasing %s (%r).', key, ecode)
            self._emit_release_event(ecode)
            self._pressed_keys_ecodes.remove(ecode)
        else:
            raise ValueError('Key %r not pressed.' % key)

    def _emit_release_event(self, ecode):
        release_value = 0
        self._emit(ecode, release_value)

    def release_pressed_keys(self):
        """Release all the keys that are currently pressed."""
        for ecode in self._pressed_keys_ecodes:
            self._emit_release_event(ecode)
        self._pressed_keys_ecodes = []


class Keyboard(KeyboardBase):

    _device = None

    def __init__(self, device_class=_UInputKeyboardDevice):
        super(Keyboard, self).__init__()
        if Keyboard._device is None:
            Keyboard._device = device_class()

    def _sanitise_keys(self, keys):
        if keys == '+':
            return [keys]
        else:
            return keys.split('+')

    def press(self, keys, delay=0.1):
        """Send key press events only.

        The 'keys' argument must be a string of keys you want
        pressed. For example:

        press('Alt+F2')

        presses the 'Alt' and 'F2' keys.

        :raises TypeError: if ``keys`` is not a string.

        """
        if not isinstance(keys, str):
            raise TypeError("'keys' argument must be a string.")

        for key in self._sanitise_keys(keys):
            for key_button in self._get_key_buttons(key):
                self._device.press(key_button)
                sleep(delay)

    def release(self, keys, delay=0.1):
        """Send key release events only.

        The 'keys' argument must be a string of keys you want
        released. For example:

        release('Alt+F2')

        releases the 'Alt' and 'F2' keys.

        Keys are released in the reverse order in which they are specified.

        :raises TypeError: if ``keys`` is not a string.
        :raises ValueError: if one of the keys to be released is not pressed.

        """
        if not isinstance(keys, str):
            raise TypeError("'keys' argument must be a string.")

        for key in reversed(self._sanitise_keys(keys)):
            for key_button in reversed(self._get_key_buttons(key)):
                self._device.release(key_button)
                sleep(delay)

    def press_and_release(self, keys, delay=0.1):
        """Press and release all items in 'keys'.

        This is the same as calling 'press(keys);release(keys)'.

        The 'keys' argument must be a string of keys you want
        pressed and released.. For example:

        press_and_release('Alt+F2')

        presses both the 'Alt' and 'F2' keys, and then releases both keys.

        :raises TypeError: if ``keys`` is not a string.

        """
        _logger.debug("Pressing and Releasing: %s", keys)
        self.press(keys, delay)
        self.release(keys, delay)

    def type(self, string, delay=0.1):
        """Simulate a user typing a string of text.

        Only 'normal' keys can be typed with this method. Control characters
        (such as 'Alt' will be interpreted as an 'A', and 'l', and a 't').

        :raises TypeError: if ``keys`` is not a string.

        """
        if not isinstance(string, str):
            raise TypeError("'keys' argument must be a string.")
        _logger.debug("Typing text %r", string)
        for key in string:
            self.press(key, delay)
            self.release(key, delay)

    @classmethod
    def on_test_end(cls, test_instance):
        """Generate KeyRelease events for any un-released keys.

        Make sure you call this at the end of any test to release
        any keys that were pressed and not released.

        """
        if cls._device is not None:
            cls._device.release_pressed_keys()

    def _get_key_buttons(self, key):
        """Return a list of the key buttons required to press.

        Multiple buttons will be returned when the key specified requires more
        than one keypress to generate (for example, upper-case letters).

        """
        key_buttons = []
        if key.isupper() or key in _SHIFTED_KEYS:
            key_buttons.append('KEY_LEFTSHIFT')
        key_name = _UINPUT_CODE_TRANSLATIONS.get(key.upper(), key)
        key_buttons.append(key_name)
        return key_buttons


@deprecated('the Touch class to instantiate a device object')
def create_touch_device(res_x=None, res_y=None):
    """Create and return a UInput touch device.

    If res_x and res_y are not specified, they will be queried from the system.

    """
    return UInput(events=_get_touch_events(res_x, res_y),
                  name='autopilot-finger',
                  version=0x2, devnode=_get_devnode_path())


# Multiouch notes:
# ----------------

# We're simulating a class of device that can track multiple touches, and keep
# them separate. This is how most modern track devices work anyway. The device
# is created with a capability to track a certain number of distinct touches at
# once. This is the ABS_MT_SLOT capability. Since our target device can track 9
# separate touches, we'll do the same.

# Each finger contact starts by registering a slot number (0-8) with a tracking
# Id. The Id should be unique for this touch - this can be an
# auto-inctrementing integer. The very first packets to tell the kernel that
# we have a touch happening should look like this:

#    ABS_MT_SLOT 0
#    ABS_MT_TRACKING_ID 45
#    ABS_MT_POSITION_X x[0]
#    ABS_MT_POSITION_Y y[0]

# This associates Tracking id 45 (could be any number) with slot 0. Slot 0 can
# now not be use by any other touch until it is released.

# If we want to move this contact's coordinates, we do this:

#    ABS_MT_SLOT 0
#    ABS_MT_POSITION_X 123
#    ABS_MT_POSITION_Y 234

# Technically, the 'SLOT 0' part isn't needed, since we're already in slot 0,
# but it doesn't hurt to have it there.

# To lift the contact, we simply specify a tracking Id of -1:

#    ABS_MT_SLOT 0
#    ABS_MT_TRACKING_ID -1

# The initial association between slot and tracking Id is made when the
# 'finger' first makes contact with the device (well, not technically true,
# but close enough). Multiple touches can be active simultaniously, as long
# as they all have unique slots, and tracking Ids. The simplest way to think
# about this is that the SLOT refers to a finger number, and the TRACKING_ID
# identifies a unique touch for the duration of it's existance.


def _get_touch_events(res_x=None, res_y=None):
    if res_x is None or res_y is None:
        res_x, res_y = _get_system_resolution()

    touch_tool = _get_touch_tool()

    events = {
        e.EV_ABS: [
            (e.ABS_X, (0, res_x, 0, 0)),
            (e.ABS_Y, (0, res_y, 0, 0)),
            (e.ABS_PRESSURE, (0, 65535, 0, 0)),
            (e.ABS_MT_POSITION_X, (0, res_x, 0, 0)),
            (e.ABS_MT_POSITION_Y, (0, res_y, 0, 0)),
            (e.ABS_MT_TOUCH_MAJOR, (0, 30, 0, 0)),
            (e.ABS_MT_TRACKING_ID, (0, 65535, 0, 0)),
            (e.ABS_MT_PRESSURE, (0, 255, 0, 0)),
            (e.ABS_MT_SLOT, (0, 9, 0, 0)),
        ],
        e.EV_KEY: [
            touch_tool,
        ]
    }
    return events


def _get_system_resolution():
    from autopilot.display import Display
    display = Display.create()
    # TODO: This calculation needs to become part of the display module:
    l = r = t = b = 0
    for screen in range(display.get_num_screens()):
        geometry = display.get_screen_geometry(screen)
        if geometry[0] < l:
            l = geometry[0]
        if geometry[1] < t:
            t = geometry[1]
        if geometry[0] + geometry[2] > r:
            r = geometry[0] + geometry[2]
        if geometry[1] + geometry[3] > b:
            b = geometry[1] + geometry[3]
    res_x = r - l
    res_y = b - t
    return res_x, res_y


def _get_touch_tool():
    return e.BTN_TOUCH


class _UInputTouchDevice(object):
    """Wrapper for the UInput Touch to execute its primitives."""

    _device = None
    _touch_fingers_in_use = []
    _last_tracking_id = 0

    def __init__(self, res_x=None, res_y=None, device_class=UInput):
        """Class constructor.

        If res_x and res_y are not specified, they will be queried from the
        system.

        """
        super(_UInputTouchDevice, self).__init__()
        if _UInputTouchDevice._device is None:
            _UInputTouchDevice._device = device_class(
                events=_get_touch_events(res_x, res_y),
                name='autopilot-finger',
                version=0x2, devnode=_get_devnode_path())
        self._touch_finger_slot = None

    @property
    def pressed(self):
        return self._touch_finger_slot is not None

    def finger_down(self, x, y):
        """Internal: moves finger "finger" down on the touchscreen.

        :param x: The finger will be moved to this x coordinate.
        :param y: The finger will be moved to this y coordinate.

        :raises RuntimeError: if the finger is already pressed.
        :raises RuntimeError: if no more touch slots are available.

        """
        if self.pressed:
            raise RuntimeError("Cannot press finger: it's already pressed.")
        self._touch_finger_slot = self._get_free_touch_finger_slot()

        self._device.write(e.EV_ABS, e.ABS_MT_SLOT, self._touch_finger_slot)
        self._device.write(
            e.EV_ABS, e.ABS_MT_TRACKING_ID, self._get_next_tracking_id())
        press_value = 1
        self._device.write(e.EV_KEY, _get_touch_tool(), press_value)
        self._device.write(e.EV_ABS, e.ABS_MT_POSITION_X, int(x))
        self._device.write(e.EV_ABS, e.ABS_MT_POSITION_Y, int(y))
        self._device.write(e.EV_ABS, e.ABS_MT_PRESSURE, 400)
        self._device.syn()

    def _get_free_touch_finger_slot(self):
        """Return the id of a free touch finger.

        :raises RuntimeError: if no more touch slots are available.

        """
        max_number_of_fingers = 9
        for i in range(max_number_of_fingers):
            if i not in _UInputTouchDevice._touch_fingers_in_use:
                _UInputTouchDevice._touch_fingers_in_use.append(i)
                return i
        raise RuntimeError('All available fingers have been used already.')

    def _get_next_tracking_id(self):
        _UInputTouchDevice._last_tracking_id += 1
        return _UInputTouchDevice._last_tracking_id

    def finger_move(self, x, y):
        """Internal: moves finger "finger" on the touchscreen to pos (x,y)

        NOTE: The finger has to be down for this to have any effect.

        :raises RuntimeError: if the finger is not pressed.

        """
        if not self.pressed:
            raise RuntimeError('Attempting to move without finger being down.')
        _logger.debug("Moving pointing 'finger' to position %d,%d.", x, y)
        self._device.write(e.EV_ABS, e.ABS_MT_SLOT, self._touch_finger_slot)
        self._device.write(e.EV_ABS, e.ABS_MT_POSITION_X, int(x))
        self._device.write(e.EV_ABS, e.ABS_MT_POSITION_Y, int(y))
        self._device.syn()
        _logger.debug("The pointing 'finger' is now at position %d,%d.", x, y)

    def finger_up(self):
        """Internal: moves finger "finger" up from the touchscreen

        :raises RuntimeError: if the finger is not pressed.

        """
        if not self.pressed:
            raise RuntimeError("Cannot release finger: it's not pressed.")
        self._device.write(e.EV_ABS, e.ABS_MT_SLOT, self._touch_finger_slot)
        lift_tracking_id = -1
        self._device.write(e.EV_ABS, e.ABS_MT_TRACKING_ID, lift_tracking_id)
        release_value = 0
        self._device.write(e.EV_KEY, _get_touch_tool(), release_value)
        self._device.syn()
        self._release_touch_finger()

    def _release_touch_finger(self):
        """Release the touch finger.

        :raises RuntimeError: if the finger was not claimed before or was
            already released.

        """
        if (self._touch_finger_slot not in
                _UInputTouchDevice._touch_fingers_in_use):
            raise RuntimeError(
                "Finger %d was never claimed, or has already been released." %
                self._touch_finger_slot)
        _UInputTouchDevice._touch_fingers_in_use.remove(
            self._touch_finger_slot)
        self._touch_finger_slot = None


class Touch(TouchBase):
    """Low level interface to generate single finger touch events."""

    def __init__(self, device_class=_UInputTouchDevice):
        super(Touch, self).__init__()
        self._device = device_class()
        self.event_delayer = EventDelay()
        self._x = 0
        self._y = 0

    @property
    def x(self):
        """Finger position X coordinate."""
        return self._x

    @property
    def y(self):
        """Finger position Y coordinate."""
        return self._y

    @property
    def pressed(self):
        return self._device.pressed

    def tap(self, x, y, press_duration=0.1, time_between_events=0.1):
        """Click (or 'tap') at given x and y coordinates.

        :raises RuntimeError: if the finger is already pressed.
        :raises RuntimeError: if no more finger slots are available.

        """
        _logger.debug("Tapping at: %d,%d", x, y)
        self.event_delayer.delay(time_between_events)
        self._finger_down(x, y)
        sleep(press_duration)
        self._device.finger_up()

    def _finger_down(self, x, y):
        self._device.finger_down(x, y)
        self._x = x
        self._y = y

    def tap_object(self, object_, press_duration=0.1, time_between_events=0.1):
        """Click (or 'tap') a given object.

        :raises RuntimeError: if the finger is already pressed.
        :raises RuntimeError: if no more finger slots are available.
        :raises ValueError: if `object_` doesn't have any recognised position
            attributes or if they are not of the correct type.

        """
        _logger.debug("Tapping object: %r", object)
        x, y = get_center_point(object_)
        self.tap(
            x,
            y,
            press_duration=press_duration,
            time_between_events=time_between_events
        )

    def press(self, x, y):
        """Press and hold a given object or at the given coordinates.

        Call release() when the object has been pressed long enough.

        :raises RuntimeError: if the finger is already pressed.
        :raises RuntimeError: if no more finger slots are available.

        """
        _logger.debug("Pressing at: %d,%d", x, y)
        self._finger_down(x, y)

    def release(self):
        """Release a previously pressed finger.

        :raises RuntimeError: if the touch is not pressed.

        """
        _logger.debug("Releasing")
        self._device.finger_up()

    def move(self, x, y, animate=True, rate=10, time_between_events=0.01):
        """Moves the pointing "finger" to pos(x,y).

        NOTE: The finger has to be down for this to have any effect.

        :param x: The point on the x axis where the move will end at.
        :param y: The point on the y axis where the move will end at.
        :param animate: Indicates if the move should be immediate or it should
            be animated moving the finger slowly accross the screen as a real
            user would do. By default, when the finger is down the finger is
            animated. When the finger is up, the parameter is ignored and the
            move is always immediate.
        :type animate: boolean.
        :param rate: The number of pixels the finger will be moved per
            iteration. Default is 10 pixels. A higher rate will make the drag
            faster, and lower rate will make it slower.
        :param time_between_events: The number of seconds that the drag will
            wait between iterations.
        :raises RuntimeError: if the finger is not pressed.

        """
        if self.pressed:
            if animate:
                self._move_with_animation(x, y, rate, time_between_events)
            else:
                self._device.finger_move(x, y)
        self._x = x
        self._y = y

    def _move_with_animation(self, x, y, rate, time_between_events):
        current_x, current_y = self.x, self.y
        while current_x != x or current_y != y:
            dx = abs(x - current_x)
            dy = abs(y - current_y)

            intx = float(dx) / max(dx, dy)
            inty = float(dy) / max(dx, dy)

            step_x = min(rate * intx, dx)
            step_y = min(rate * inty, dy)

            if x < current_x:
                step_x *= -1
            if y < current_y:
                step_y *= -1

            current_x += step_x
            current_y += step_y

            self._device.finger_move(current_x, current_y)

            sleep(time_between_events)

    def drag(self, x1, y1, x2, y2, rate=10, time_between_events=0.01):
        """Perform a drag gesture.

        The finger will be dragged from the starting point to the ending point
        with multiple moves. The number of moves, and thus the time that it
        will take to complete the drag can be altered with the `rate`
        parameter.

        :param x1: The point on the x axis where the drag will start from.
        :param y1: The point on the y axis where the drag will starts from.
        :param x2: The point on the x axis where the drag will end at.
        :param y2: The point on the y axis where the drag will end at.
        :param rate: The number of pixels the finger will be moved per
            iteration. Default is 10 pixels. A higher rate will make the drag
            faster, and lower rate will make it slower.
        :param time_between_events: The number of seconds that the drag will
            wait between iterations.

        :raises RuntimeError: if the finger is already pressed.
        :raises RuntimeError: if no more finger slots are available.

        """
        _logger.debug("Dragging from %d,%d to %d,%d", x1, y1, x2, y2)
        self._finger_down(x1, y1)
        self.move(
            x2, y2, animate=True, rate=rate,
            time_between_events=time_between_events)
        self._device.finger_up()


# veebers: there should be a better way to handle this.
_SHIFTED_KEYS = "~!@#$%^&*()_+{}|:\"?><"

# The double-ups are due to the 'shifted' keys.
_UINPUT_CODE_TRANSLATIONS = {
    '/': 'SLASH',
    '?': 'SLASH',
    '.': 'DOT',
    ',': 'COMMA',
    '>': 'DOT',
    '<': 'COMMA',
    '\'': 'APOSTROPHE',
    '"': 'APOSTROPHE',
    ';': 'SEMICOLON',
    ':': 'SEMICOLON',
    '\\': 'BACKSLASH',
    '|': 'BACKSLASH',
    ']': 'RIGHTBRACE',
    '[': 'LEFTBRACE',
    '}': 'RIGHTBRACE',
    '{': 'LEFTBRACE',
    '=': 'EQUAL',
    '+': 'EQUAL',
    '-': 'MINUS',
    '_': 'MINUS',
    ')': '0',
    '(': '9',
    '*': '8',
    '&': '7',
    '^': '6',
    '%': '5',
    '$': '4',
    '#': '3',
    '@': '2',
    '!': '1',
    '~': 'GRAVE',
    '`': 'GRAVE',
    ' ': 'SPACE',
    '\t': 'TAB',
    '\n': 'ENTER',
    '\b': 'BACKSPACE',
    'CTRL': 'LEFTCTRL',
    'ALT': 'LEFTALT',
    'SHIFT': 'LEFTSHIFT',
}


class UInputHardwareKeysDevice:

    _device = None

    def __init__(self, device_class=UInput):
        if not UInputHardwareKeysDevice._device:
            UInputHardwareKeysDevice._device = device_class(
                devnode=_get_devnode_path(),
            )
            # This workaround is not needed on desktop.
            if model() != 'Desktop':
                self._wait_for_device_to_ready()

    def press_and_release_power_button(self):
        self._device.write(e.EV_KEY, e.KEY_POWER, 1)
        self._device.write(e.EV_KEY, e.KEY_POWER, 0)
        self._device.syn()

    def _wait_for_device_to_ready(
            self,
            retry_attempts_count=10,
            retry_interval=0.1,
    ):
        """Wait for UInput device to initialize.

        This is a workaround for a bug in evdev where the input device
        is not instantly created.

        :param retry_attempts_count: number of attempts to check
            if device is ready.

        :param retry_interval: time in fractional seconds to be
            slept, between each attempt to check if device is
            ready.

        :raises RuntimeError: if device is not initialized after
            number of retries specified in *retry_attempts_count*.
        """
        for i in range(retry_attempts_count):
            device = self._device._find_device()
            if device:
                self._device.device = device
                return
            else:
                sleep(retry_interval)
        raise RuntimeError('Failed to find UInput device.')
