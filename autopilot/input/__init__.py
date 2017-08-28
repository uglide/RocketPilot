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


"""
Autopilot unified input system.
===============================

This package provides input methods for various platforms. Autopilot aims to
provide an appropriate implementation for the currently running system. For
example, not all systems have an X11 stack running: on those systems, autopilot
will instantiate input classes class that use something other than X11 to
generate events (possibly UInput).

Test authors should instantiate the appropriate class using the ``create``
method on each class. Calling ``create()`` with  no arguments will get an
instance of the specified class that suits the current platform. In this case,
autopilot will do it's best to pick a suitable backend. Calling ``create``
with a backend name will result in that specific backend type being returned,
or, if it cannot be created, an exception will be raised. For more information
on creating backends, see :ref:`tut-picking-backends`

There are three basic input types available:

 * :class:`Keyboard` - traditional keyboard devices.
 * :class:`Mouse` - traditional mouse devices (Currently only avaialble on the
    desktop).
 * :class:`Touch` - single point-of-contact touch device.

The :class:`Pointer` class is a wrapper that unifies the API of the
:class:`Mouse` and :class:`Touch` classes, which can be helpful if you want to
write a test that can use either a mouse of a touch device. A common pattern is
to use a Touch device when running on a mobile device, and a Mouse device when
running on a desktop.

.. seealso::
    Module :mod:`autopilot.gestures`
        Multitouch and gesture support for touch devices.

"""

from collections import OrderedDict
from contextlib import contextmanager

import psutil

from autopilot.input._common import get_center_point
from autopilot.utilities import _pick_backend, CleanupRegistered

import logging

_logger = logging.getLogger(__name__)


__all__ = ['get_center_point']


class Keyboard(CleanupRegistered):

    """A simple keyboard device class.

    The keyboard class is used to generate key events while in an autopilot
    test. This class should not be instantiated directly. To get an
    instance of the keyboard class, call :py:meth:`create` instead.

    """

    @staticmethod
    def create(preferred_backend=''):
        """Get an instance of the :py:class:`Keyboard` class.

        For more infomration on picking specific backends, see
        :ref:`tut-picking-backends`

        For details regarding backend limitations please see:
        :ref:`Keyboard backend limitations<keyboard_backend_limitations>`

        .. warning:: The **OSK** (On Screen Keyboard) backend option does not
         implement either :py:meth:`press` or :py:meth:`release` methods due to
         technical implementation details and will raise a NotImplementedError
         exception if used.

        :param preferred_backend: A string containing a hint as to which
            backend you would like. Possible backends are:

            * ``X11`` - Generate keyboard events using the X11 client
                libraries.
            * ``UInput`` - Use UInput kernel-level device driver.
            * ``OSK`` - Use the graphical On Screen Keyboard as a backend.

        :raises: RuntimeError if autopilot cannot instantate any of the
            possible backends.
        :raises: RuntimeError if the preferred_backend is specified and is not
            one of the possible backends for this device class.
        :raises: :class:`~autopilot.BackendException` if the preferred_backend
            is set, but that backend could not be instantiated.

        """
        def get_x11_kb():
            from autopilot.input._X11 import Keyboard
            return Keyboard()

        def get_uinput_kb():
            from autopilot.input._uinput import Keyboard
            return Keyboard()

        def get_osk_kb():
            try:
                maliit = [p for p in
                          psutil.process_iter() if p.name() == 'maliit-server']
                if maliit:
                    from autopilot.input._osk import Keyboard
                    return Keyboard()
                else:
                    raise RuntimeError('maliit-server is not running')
            except ImportError as e:
                e.args += ("Unable to import the OSK backend",)
                raise

        backends = OrderedDict()
        backends['X11'] = get_x11_kb
        backends['OSK'] = get_osk_kb
        backends['UInput'] = get_uinput_kb
        return _pick_backend(backends, preferred_backend)

    @contextmanager
    def focused_type(self, input_target, pointer=None):
        """Type into an input widget.

        This context manager takes care of making sure a particular
        *input_target* UI control is selected before any text is entered.

        Some backends extend this method to perform cleanup actions at the end
        of the context manager block. For example, the OSK backend dismisses
        the keyboard.

        If the *pointer* argument is None (default) then either a Mouse or
        Touch pointer will be created based on the current platform.

        An example of using the context manager (with an OSK backend)::

            from autopilot.input import Keyboard

            text_area = self._launch_test_input_area()
            keyboard = Keyboard.create('OSK')
            with keyboard.focused_type(text_area) as kb:
                kb.type("Hello World.")
                self.assertThat(text_area.text, Equals("Hello World"))
            # Upon leaving the context managers scope the keyboard is dismissed
            # with a swipe

        """
        if pointer is None:
            from autopilot.platform import model
            if model() == 'Desktop':
                pointer = Pointer(Mouse.create())
            else:
                pointer = Pointer(Touch.create())

        pointer.click_object(input_target)
        yield self

    def press(self, keys, delay=0.2):
        """Send key press events only.

        :param keys: Keys you want pressed.
        :param delay: The delay (in Seconds) after pressing the keys before
            returning control to the caller.
        :raises: NotImplementedError If called when using the OSK Backend.

        .. warning:: The **OSK** backend does not implement the press method
          and will raise a NotImplementedError if called.

        Example::

            press('Alt+F2')

        presses the 'Alt' and 'F2' keys, but does not release them.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def release(self, keys, delay=0.2):
        """Send key release events only.

        :param keys: Keys you want released.
        :param delay: The delay (in Seconds) after releasing the keys before
            returning control to the caller.
        :raises: NotImplementedError If called when using the OSK Backend.

        .. warning:: The **OSK** backend does not implement the press method
         and will raise a NotImplementedError if called.

        Example::

            release('Alt+F2')

        releases the 'Alt' and 'F2' keys.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def press_and_release(self, keys, delay=0.2):
        """Press and release all items in 'keys'.

        This is the same as calling 'press(keys);release(keys)'.

        :param keys: Keys you want pressed and released.
        :param delay: The delay (in Seconds) after pressing and releasing each
            key.

        Example::

            press_and_release('Alt+F2')

        presses both the 'Alt' and 'F2' keys, and then releases both keys.

        """

        raise NotImplementedError("You cannot use this class directly.")

    def type(self, string, delay=0.1):
        """Simulate a user typing a string of text.

        :param string: The string to text to type.
        :param delay: The delay (in Seconds) after pressing and releasing each
            key. Note that the default value here is shorter than for the
            press, release and press_and_release methods.

        .. note:: Only 'normal' keys can be typed with this method. Control
         characters (such as 'Alt' will be interpreted as an 'A', and 'l',
         and a 't').

        """
        raise NotImplementedError("You cannot use this class directly.")


class Mouse(CleanupRegistered):

    """A simple mouse device class.

    The mouse class is used to generate mouse events while in an autopilot
    test. This class should not be instantiated directly however. To get an
    instance of the mouse class, call :py:meth:`create` instead.

    For example, to create a mouse object and click at (100,50)::

        mouse = Mouse.create()
        mouse.move(100, 50)
        mouse.click()

    """

    @staticmethod
    def create(preferred_backend=''):
        """Get an instance of the :py:class:`Mouse` class.

        For more infomration on picking specific backends, see
        :ref:`tut-picking-backends`

        :param preferred_backend: A string containing a hint as to which
            backend you would like. Possible backends are:

            * ``X11`` - Generate mouse events using the X11 client libraries.

        :raises: RuntimeError if autopilot cannot instantate any of the
            possible backends.
        :raises: RuntimeError if the preferred_backend is specified and is not
            one of the possible backends for this device class.
        :raises: :class:`~autopilot.BackendException` if the preferred_backend
            is set, but that backend could not be instantiated.

        """
        def get_x11_mouse():
            from autopilot.input._X11 import Mouse
            return Mouse()

        def get_uinput_mouse():
            # Return the Touch device for now as Mouse under a Mir desktop
            # is a challenge for now.
            from autopilot.input._uinput import Touch
            return Touch()

        backends = OrderedDict()
        backends['X11'] = get_x11_mouse
        backends['UInput'] = get_uinput_mouse
        return _pick_backend(backends, preferred_backend)

    @property
    def x(self):
        """Mouse position X coordinate."""
        raise NotImplementedError("You cannot use this class directly.")

    @property
    def y(self):
        """Mouse position Y coordinate."""
        raise NotImplementedError("You cannot use this class directly.")

    def press(self, button=1):
        """Press mouse button at current mouse location."""
        raise NotImplementedError("You cannot use this class directly.")

    def release(self, button=1):
        """Releases mouse button at current mouse location."""
        raise NotImplementedError("You cannot use this class directly.")

    def click(self, button=1, press_duration=0.10, time_between_events=0.1):
        """Click mouse at current location.

        :param time_between_events: takes floating point to represent the
          delay time between subsequent clicks. Default value 0.1 represents
          tenth of a second.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def click_object(
            self,
            object_proxy,
            button=1,
            press_duration=0.10,
            time_between_events=0.1):
        """Click the center point of a given object.

        It does this by looking for several attributes, in order. The first
        attribute found will be used. The attributes used are (in order):

         * globalRect (x,y,w,h)
         * center_x, center_y
         * x, y, w, h

        :param time_between_events: takes floating point to represent the
          delay time between subsequent clicks. Default value 0.1 represents
          tenth of a second.
        :raises: **ValueError** if none of these attributes are found, or if an
         attribute is of an incorrect type.

         """
        self.move_to_object(object_proxy)
        self.click(button, press_duration, time_between_events)

    def move(self, x, y, animate=True, rate=10, time_between_events=0.01):
        """Moves mouse to location (x,y).

        Callers should avoid specifying the *rate* or *time_between_events*
        parameters unless they need a specific rate of movement.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def move_to_object(self, object_proxy):
        """Attempts to move the mouse to 'object_proxy's centre point.

        It does this by looking for several attributes, in order. The first
        attribute found will be used. The attributes used are (in order):

         * globalRect (x,y,w,h)
         * center_x, center_y
         * x, y, w, h

        :raises: **ValueError** if none of these attributes are found, or if an
         attribute is of an incorrect type.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def position(self):
        """
        Returns the current position of the mouse pointer.

        :return: (x,y) tuple
        """
        raise NotImplementedError("You cannot use this class directly.")

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
        raise NotImplementedError("You cannot use this class directly.")


class Touch(object):
    """A simple touch driver class.

    This class can be used for any touch events that require a single active
    touch at once. If you want to do complex gestures (including multi-touch
    gestures), look at the :py:mod:`autopilot.gestures` module.

    """

    @staticmethod
    def create(preferred_backend=''):
        """Get an instance of the :py:class:`Touch` class.

        :param preferred_backend: A string containing a hint as to which
            backend you would like. If left blank, autopilot will pick a
            suitable backend for you. Specifying a backend will guarantee that
            either that backend is returned, or an exception is raised.

            possible backends are:

            * ``UInput`` - Use UInput kernel-level device driver.

        :raises: RuntimeError if autopilot cannot instantate any of the
            possible backends.
        :raises: RuntimeError if the preferred_backend is specified and is not
            one of the possible backends for this device class.
        :raises: :class:`~autopilot.BackendException` if the preferred_backend
            is set, but that backend could not be instantiated.

        """
        def get_uinput_touch():
            from autopilot.input._uinput import Touch
            return Touch()

        backends = OrderedDict()
        backends['UInput'] = get_uinput_touch
        return _pick_backend(backends, preferred_backend)

    @property
    def pressed(self):
        """Return True if this touch is currently in use (i.e.- pressed on the
            'screen').

        """
        raise NotImplementedError("You cannot use this class directly.")

    def tap(self, x, y, press_duration=0.1, time_between_events=0.1):
        """Click (or 'tap') at given x,y coordinates.

        :param time_between_events: takes floating point to represent the
          delay time between subsequent taps. Default value 0.1 represents
          tenth of a second.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def tap_object(self, object, press_duration=0.1, time_between_events=0.1):
        """Tap the center point of a given object.

        It does this by looking for several attributes, in order. The first
        attribute found will be used. The attributes used are (in order):

         * globalRect (x,y,w,h)
         * center_x, center_y
         * x, y, w, h

        :param time_between_events: takes floating point to represent the
          delay time between subsequent taps. Default value 0.1 represents
          tenth of a second.
        :raises: **ValueError** if none of these attributes are found, or if an
         attribute is of an incorrect type.

         """
        raise NotImplementedError("You cannot use this class directly.")

    def press(self, x, y):
        """Press and hold at the given x,y coordinates."""
        raise NotImplementedError("You cannot use this class directly.")

    def move(self, x, y):
        """Move the pointer coords to (x,y).

        .. note:: The touch 'finger' must be pressed for a call to this
         method to be successful. (see :py:meth:`press` for further details on
         touch presses.)

        :raises: **RuntimeError** if called and the touch 'finger' isn't
         pressed.

        """
        raise NotImplementedError("You cannot use this class directly.")

    def release(self):
        """Release a previously pressed finger"""
        raise NotImplementedError("You cannot use this class directly.")

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
        raise NotImplementedError("You cannot use this class directly.")


class Pointer(object):

    """A wrapper class that represents a pointing device which can either be a
    mouse or a touch, and provides a unified API.

    This class is useful if you want to run tests with either a mouse or a
    touch device, and want to write your tests to use a single API. Create
    this wrapper by passing it either a mouse or a touch device, like so::

        pointer_device = Pointer(Mouse.create())

    or, like so::

        pointer_device = Pointer(Touch.create())


    .. warning::
        Some operations only make sense for certain devices. This class
        attempts to minimise the differences between the Mouse and Touch APIs,
        but there are still some operations that will cause exceptions to be
        raised. These are documented in the specific methods below.

    """

    def __init__(self, device):
        if not isinstance(device, Mouse) and not isinstance(device, Touch):
            raise TypeError(
                "`device` must be either a Touch or a Mouse instance.")
        self._device = device

    @property
    def x(self):
        """Pointer X coordinate.

        If the wrapped device is a :class:`Touch` device, this will return the
        last known X coordinate, which may not be a sensible value.

        """
        return self._device.x

    @property
    def y(self):
        """Pointer Y coordinate.

        If the wrapped device is a :class:`Touch` device, this will return the
        last known Y coordinate, which may not be a sensible value.

        """
        return self._device.y

    def press(self, button=1):
        """Press the pointer at it's current location.

        If the wrapped device is a mouse, you may pass a button specification.
        If it is a touch device, passing anything other than 1 will raise a
        ValueError exception.

        """
        if isinstance(self._device, Mouse):
            self._device.press(button)
        else:
            if button != 1:
                raise ValueError(
                    "Touch devices do not have button %d" % (button))
            self._device.press(self.x, self.y)

    def release(self, button=1):
        """Releases the pointer at it's current location.

        If the wrapped device is a mouse, you may pass a button specification.
        If it is a touch device, passing anything other than 1 will raise a
        ValueError exception.

        """
        if isinstance(self._device, Mouse):
            self._device.release(button)
        else:
            if button != 1:
                raise ValueError(
                    "Touch devices do not have button %d" % (button))
            self._device.release()

    def click(self, button=1, press_duration=0.10, time_between_events=0.1):
        """Press and release at the current pointer location.

        If the wrapped device is a mouse, the button specification is used. If
        it is a touch device, passing anything other than 1 will raise a
        ValueError exception.

        :param time_between_events: takes floating point to represent the
          delay time between subsequent clicks/taps. Default value 0.1
          represents tenth of a second.
        """
        if isinstance(self._device, Mouse):
            self._device.click(button, press_duration, time_between_events)
        else:
            if button != 1:
                raise ValueError(
                    "Touch devices do not have button %d" % (button))
            self._device.tap(
                self.x,
                self.y,
                press_duration=press_duration,
                time_between_events=time_between_events
            )

    def move(self, x, y):
        """Moves the pointer to the specified coordinates.

        If the wrapped device is a mouse, the mouse will animate to the
        specified coordinates. If the wrapped device is a touch device, this
        method will determine where the next :meth:`press`, :meth:`release` or
        :meth:`click` will occur.

        """
        self._device.move(x, y)

    def click_object(
            self,
            object_proxy,
            button=1,
            press_duration=0.10,
            time_between_events=0.1):
        """
        Attempts to move the pointer to 'object_proxy's centre point
        and click a button.

        See :py:meth:`~autopilot.input.get_center_point` for details on how
        the center point is calculated.

        If the wrapped device is a mouse, the button specification is used. If
        it is a touch device, passing anything other than 1 will raise a
        ValueError exception.

        :param time_between_events: takes floating point to represent the
            delay time between subsequent clicks/taps. Default value 0.1
            represents tenth of a second.

        """

        self.move_to_object(object_proxy)
        self.click(button, press_duration, time_between_events)

    def move_to_object(self, object_proxy):
        """Attempts to move the pointer to 'object_proxy's centre point.

        See :py:meth:`~autopilot.input.get_center_point` for details on how
        the center point is calculated.

        """
        x, y = get_center_point(object_proxy)
        self.move(x, y)

    def position(self):
        """
        Returns the current position of the pointer.

        :return: (x,y) tuple
        """
        if isinstance(self._device, Mouse):
            return self._device.position()
        else:
            return (self.x, self.y)

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
        self._device.drag(
            x1, y1, x2, y2, rate=rate, time_between_events=time_between_events)
