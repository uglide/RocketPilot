# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2013, 2014, 2015 Canonical
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
import unittest

import testscenarios
from evdev import ecodes, uinput
from unittest.mock import ANY, call, Mock, patch
from testtools import TestCase
from testtools.matchers import Contains, raises

import autopilot.input
from autopilot import (
    tests,
    utilities
)
from autopilot.input import _uinput, get_center_point, Keyboard


class Empty(object):

    def __repr__(self):
        return "<Empty>"


def make_fake_object(globalRect=False, center=False, xywh=False):
    obj = Empty()
    if globalRect:
        obj.globalRect = (0, 0, 100, 100)
    if center:
        obj.center_x = 123
        obj.center_y = 345
    if xywh:
        obj.x, obj.y, obj.w, obj.h = (100, 100, 20, 40)
    return obj


class InputCenterPointTests(TestCase):
    """Tests for the input get_center_point utility."""

    def test_get_center_point_raises_ValueError_on_empty_object(self):
        obj = make_fake_object()
        fn = lambda: get_center_point(obj)
        expected_exception = ValueError(
            "Object '%r' does not have any recognised position attributes" %
            obj)
        self.assertThat(fn, raises(expected_exception))

    def test_get_center_point_works_with_globalRect(self):
        obj = make_fake_object(globalRect=True)
        x, y = get_center_point(obj)

        self.assertEqual(50, x)
        self.assertEqual(50, y)

    def test_raises_ValueError_on_uniterable_globalRect(self):
        obj = Empty()
        obj.globalRect = 123
        expected_exception = ValueError(
            "Object '<Empty>' has globalRect attribute, but it is not of the "
            "correct type"
        )
        self.assertThat(
            lambda: get_center_point(obj),
            raises(expected_exception)
        )

    def test_raises_ValueError_on_too_small_globalRect(self):
        obj = Empty()
        obj.globalRect = (1, 2, 3)
        expected_exception = ValueError(
            "Object '<Empty>' has globalRect attribute, but it is not of the "
            "correct type"
        )
        self.assertThat(
            lambda: get_center_point(obj),
            raises(expected_exception)
        )

    @patch('autopilot.input._common._logger')
    def test_get_center_point_logs_with_globalRect(self, mock_logger):
        obj = make_fake_object(globalRect=True)
        x, y = get_center_point(obj)

        mock_logger.debug.assert_called_once_with(
            "Moving to object's globalRect coordinates."
        )

    def test_get_center_point_works_with_center_points(self):
        obj = make_fake_object(center=True)
        x, y = get_center_point(obj)

        self.assertEqual(123, x)
        self.assertEqual(345, y)

    @patch('autopilot.input._common._logger')
    def test_get_center_point_logs_with_center_points(self, mock_logger):
        obj = make_fake_object(center=True)
        x, y = get_center_point(obj)

        mock_logger.debug.assert_called_once_with(
            "Moving to object's center_x, center_y coordinates."
        )

    def test_get_center_point_works_with_xywh(self):
        obj = make_fake_object(xywh=True)
        x, y = get_center_point(obj)

        self.assertEqual(110, x)
        self.assertEqual(120, y)

    @patch('autopilot.input._common._logger')
    def test_get_center_point_logs_with_xywh(self, mock_logger):
        obj = make_fake_object(xywh=True)
        x, y = get_center_point(obj)

        mock_logger.debug.assert_called_once_with(
            "Moving to object's center point calculated from x,y,w,h "
            "attributes."
        )

    def test_get_center_point_raises_valueError_on_non_numerics(self):
        obj = Empty()
        obj.x, obj.y, obj.w, obj.h = 1, None, True, "oof"
        expected_exception = ValueError(
            "Object '<Empty>' has x,y attribute, but they are not of the "
            "correct type"
        )
        self.assertThat(
            lambda: get_center_point(obj),
            raises(expected_exception)
        )

    def test_get_center_point_prefers_globalRect(self):
        obj = make_fake_object(globalRect=True, center=True, xywh=True)
        x, y = get_center_point(obj)

        self.assertEqual(50, x)
        self.assertEqual(50, y)

    def test_get_center_point_prefers_center_points(self):
        obj = make_fake_object(globalRect=False, center=True, xywh=True)
        x, y = get_center_point(obj)

        self.assertEqual(123, x)
        self.assertEqual(345, y)


class UInputTestCase(TestCase):
    """Tests for the global methods of the uinput module."""

    def test_create_touch_device_must_print_deprecation_message(self):
        with patch('autopilot.utilities.logger') as patched_log:
            with patch('autopilot.input._uinput.UInput'):
                _uinput.create_touch_device('dummy', 'dummy')
        self.assertThat(
            patched_log.warning.call_args[0][0],
            Contains(
                "This function is deprecated. Please use 'the Touch class to "
                "instantiate a device object' instead."
            )
        )


class UInputKeyboardDeviceTestCase(TestCase):
    """Test the integration with evdev.UInput for the keyboard."""

    _PRESS_VALUE = 1
    _RELEASE_VALUE = 0

    def get_keyboard_with_mocked_backend(self):
        keyboard = _uinput._UInputKeyboardDevice(device_class=Mock)
        keyboard._device.mock_add_spec(uinput.UInput, spec_set=True)
        return keyboard

    def assert_key_press_emitted_write_and_syn(self, keyboard, key):
        self.assert_emitted_write_and_syn(keyboard, key, self._PRESS_VALUE)

    def assert_key_release_emitted_write_and_syn(self, keyboard, key):
        self.assert_emitted_write_and_syn(keyboard, key, self._RELEASE_VALUE)

    def assert_emitted_write_and_syn(self, keyboard, key, value):
        key_ecode = ecodes.ecodes.get(key)
        expected_calls = [
            call.write(ecodes.EV_KEY, key_ecode, value),
            call.syn()
        ]

        self.assertEqual(expected_calls, keyboard._device.mock_calls)

    def press_key_and_reset_mock(self, keyboard, key):
        keyboard.press(key)
        keyboard._device.reset_mock()

    def test_press_key_must_emit_write_and_syn(self):
        keyboard = self.get_keyboard_with_mocked_backend()
        keyboard.press('KEY_A')
        self.assert_key_press_emitted_write_and_syn(keyboard, 'KEY_A')

    def test_press_key_must_append_leading_string(self):
        keyboard = self.get_keyboard_with_mocked_backend()
        keyboard.press('A')
        self.assert_key_press_emitted_write_and_syn(keyboard, 'KEY_A')

    def test_press_key_must_ignore_case(self):
        keyboard = self.get_keyboard_with_mocked_backend()
        keyboard.press('a')
        self.assert_key_press_emitted_write_and_syn(keyboard, 'KEY_A')

    def test_press_unexisting_key_must_raise_error(self):
        keyboard = self.get_keyboard_with_mocked_backend()
        error = self.assertRaises(
            ValueError, keyboard.press, 'unexisting')

        self.assertEqual('Unknown key name: unexisting.', str(error))

    def test_release_not_pressed_key_must_raise_error(self):
        keyboard = self.get_keyboard_with_mocked_backend()
        error = self.assertRaises(
            ValueError, keyboard.release, 'A')

        self.assertEqual("Key 'A' not pressed.", str(error))

    def test_release_key_must_emit_write_and_syn(self):
        keyboard = self.get_keyboard_with_mocked_backend()
        self.press_key_and_reset_mock(keyboard, 'KEY_A')

        keyboard.release('KEY_A')
        self.assert_key_release_emitted_write_and_syn(keyboard, 'KEY_A')

    def test_release_key_must_append_leading_string(self):
        keyboard = self.get_keyboard_with_mocked_backend()
        self.press_key_and_reset_mock(keyboard, 'KEY_A')

        keyboard.release('A')
        self.assert_key_release_emitted_write_and_syn(keyboard, 'KEY_A')

    def test_release_key_must_ignore_case(self):
        keyboard = self.get_keyboard_with_mocked_backend()
        self.press_key_and_reset_mock(keyboard, 'KEY_A')

        keyboard.release('a')
        self.assert_key_release_emitted_write_and_syn(keyboard, 'KEY_A')

    def test_release_unexisting_key_must_raise_error(self):
        keyboard = self.get_keyboard_with_mocked_backend()
        error = self.assertRaises(
            ValueError, keyboard.release, 'unexisting')

        self.assertEqual('Unknown key name: unexisting.', str(error))

    def test_release_pressed_keys_without_pressed_keys_must_do_nothing(self):
        keyboard = self.get_keyboard_with_mocked_backend()
        keyboard.release_pressed_keys()
        self.assertEqual([], keyboard._device.mock_calls)

    def test_release_pressed_keys_with_pressed_keys(self):
        expected_calls = [
            call.write(
                ecodes.EV_KEY, ecodes.ecodes.get('KEY_A'),
                self._RELEASE_VALUE),
            call.syn(),
            call.write(
                ecodes.EV_KEY, ecodes.ecodes.get('KEY_B'),
                self._RELEASE_VALUE),
            call.syn()
        ]

        keyboard = self.get_keyboard_with_mocked_backend()
        self.press_key_and_reset_mock(keyboard, 'KEY_A')
        self.press_key_and_reset_mock(keyboard, 'KEY_B')

        keyboard.release_pressed_keys()

        self.assertEqual(expected_calls, keyboard._device.mock_calls)

    def test_release_pressed_keys_already_released(self):
        expected_calls = []
        keyboard = self.get_keyboard_with_mocked_backend()
        keyboard.press('KEY_A')
        keyboard.release_pressed_keys()
        keyboard._device.reset_mock()

        keyboard.release_pressed_keys()
        self.assertEqual(expected_calls, keyboard._device.mock_calls)


class UInputKeyboardTestCase(testscenarios.TestWithScenarios, TestCase):
    """Test UInput Keyboard helper for autopilot tests."""

    scenarios = [
        ('single key', dict(keys='a', expected_calls_args=['a'])),
        ('upper-case letter', dict(
            keys='A', expected_calls_args=['KEY_LEFTSHIFT', 'A'])),
        ('key combination', dict(
            keys='a+b', expected_calls_args=['a', 'b']))
    ]

    def setUp(self):
        super(UInputKeyboardTestCase, self).setUp()
        # Return to the original device after the test.
        self.addCleanup(self.set_keyboard_device, _uinput.Keyboard._device)
        # Mock the sleeps so we don't have to spend time actually sleeping.
        self.addCleanup(utilities.sleep.disable_mock)
        utilities.sleep.enable_mock()

    def set_keyboard_device(self, device):
        _uinput.Keyboard._device = device

    def get_keyboard_with_mocked_backend(self):
        _uinput.Keyboard._device = None
        keyboard = _uinput.Keyboard(device_class=Mock)
        keyboard._device.mock_add_spec(
            _uinput._UInputKeyboardDevice, spec_set=True)
        return keyboard

    def test_press_must_put_press_device_keys(self):
        expected_calls = [
            call.press(arg) for arg in self.expected_calls_args]
        keyboard = self.get_keyboard_with_mocked_backend()
        keyboard.press(self.keys)

        self.assertEqual(expected_calls, keyboard._device.mock_calls)

    def test_release_must_release_device_keys(self):
        keyboard = self.get_keyboard_with_mocked_backend()
        keyboard.press(self.keys)
        keyboard._device.reset_mock()

        expected_calls = [
            call.release(arg) for arg in
            reversed(self.expected_calls_args)]
        keyboard.release(self.keys)

        self.assertEqual(
            expected_calls, keyboard._device.mock_calls)

    def test_press_and_release_must_press_device_keys(self):
        expected_press_calls = [
            call.press(arg) for arg in self.expected_calls_args]
        ignored_calls = [
            ANY for arg in self.expected_calls_args]

        keyboard = self.get_keyboard_with_mocked_backend()
        keyboard.press_and_release(self.keys)

        self.assertEqual(
            expected_press_calls + ignored_calls,
            keyboard._device.mock_calls)

    def test_press_and_release_must_release_device_keys_in_reverse_order(
            self):
        ignored_calls = [
            ANY for arg in self.expected_calls_args]
        expected_release_calls = [
            call.release(arg) for arg in
            reversed(self.expected_calls_args)]

        keyboard = self.get_keyboard_with_mocked_backend()
        keyboard.press_and_release(self.keys)

        self.assertEqual(
            ignored_calls + expected_release_calls,
            keyboard._device.mock_calls)

    def test_on_test_end_without_device_must_do_nothing(self):
        _uinput.Keyboard._device = None
        # This will fail if it calls anything from the device, as it's None.
        _uinput.Keyboard.on_test_end(self)

    def test_on_test_end_with_device_must_release_pressed_keys(self):
        keyboard = self.get_keyboard_with_mocked_backend()
        _uinput.Keyboard.on_test_end(self)
        self.assertEqual(
            [call.release_pressed_keys()], keyboard._device.mock_calls)


class TouchEventsTestCase(TestCase):

    def assert_expected_ev_abs(self, res_x, res_y, actual_ev_abs):
        expected_ev_abs = [
            (ecodes.ABS_X, (0, res_x, 0, 0)),
            (ecodes.ABS_Y, (0, res_y, 0, 0)),
            (ecodes.ABS_PRESSURE, (0, 65535, 0, 0)),
            (ecodes.ABS_MT_POSITION_X, (0, res_x, 0, 0)),
            (ecodes.ABS_MT_POSITION_Y, (0, res_y, 0, 0)),
            (ecodes.ABS_MT_TOUCH_MAJOR, (0, 30, 0, 0)),
            (ecodes.ABS_MT_TRACKING_ID, (0, 65535, 0, 0)),
            (ecodes.ABS_MT_PRESSURE, (0, 255, 0, 0)),
            (ecodes.ABS_MT_SLOT, (0, 9, 0, 0))
        ]
        self.assertEqual(expected_ev_abs, actual_ev_abs)

    def test_get_touch_events_without_args_must_use_system_resolution(self):
        with patch.object(
                _uinput, '_get_system_resolution', spec_set=True,
                autospec=True) as mock_system_resolution:
            mock_system_resolution.return_value = (
                'system_res_x', 'system_res_y')
            events = _uinput._get_touch_events()

        ev_abs = events.get(ecodes.EV_ABS)
        self.assert_expected_ev_abs('system_res_x', 'system_res_y', ev_abs)

    def test_get_touch_events_with_args_must_use_given_resulution(self):
        events = _uinput._get_touch_events('given_res_x', 'given_res_y')
        ev_abs = events.get(ecodes.EV_ABS)
        self.assert_expected_ev_abs('given_res_x', 'given_res_y', ev_abs)


class UInputTouchDeviceTestCase(tests.LogHandlerTestCase):
    """Test the integration with evdev.UInput for the touch device."""

    def setUp(self):
        super(UInputTouchDeviceTestCase, self).setUp()
        self._number_of_slots = 9

        # Return to the original device after the test.
        self.addCleanup(
            self.set_mouse_device,
            _uinput._UInputTouchDevice._device,
            _uinput._UInputTouchDevice._touch_fingers_in_use,
            _uinput._UInputTouchDevice._last_tracking_id)

        # Always start the tests without fingers in use.
        _uinput._UInputTouchDevice._touch_fingers_in_use = []
        _uinput._UInputTouchDevice._last_tracking_id = 0

    def set_mouse_device(
            self, device, touch_fingers_in_use, last_tracking_id):
        _uinput._UInputTouchDevice._device = device
        _uinput._UInputTouchDevice._touch_fingers_in_use = touch_fingers_in_use
        _uinput._UInputTouchDevice._last_tracking_id = last_tracking_id

    def get_touch_with_mocked_backend(self):
        dummy_x_resolution = 100
        dummy_y_resolution = 100

        _uinput._UInputTouchDevice._device = None
        touch = _uinput._UInputTouchDevice(
            res_x=dummy_x_resolution, res_y=dummy_y_resolution,
            device_class=Mock)
        touch._device.mock_add_spec(uinput.UInput, spec_set=True)
        return touch

    def assert_finger_down_emitted_write_and_syn(
            self, touch, slot, tracking_id, x, y):
        press_value = 1
        expected_calls = [
            call.write(ecodes.EV_ABS, ecodes.ABS_MT_SLOT, slot),
            call.write(
                ecodes.EV_ABS, ecodes.ABS_MT_TRACKING_ID, tracking_id),
            call.write(
                ecodes.EV_KEY, ecodes.BTN_TOUCH, press_value),
            call.write(ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, x),
            call.write(ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, y),
            call.write(ecodes.EV_ABS, ecodes.ABS_MT_PRESSURE, 400),
            call.syn()
        ]
        self.assertEqual(expected_calls, touch._device.mock_calls)

    def assert_finger_move_emitted_write_and_syn(self, touch, slot, x, y):
        expected_calls = [
            call.write(ecodes.EV_ABS, ecodes.ABS_MT_SLOT, slot),
            call.write(ecodes.EV_ABS, ecodes.ABS_MT_POSITION_X, x),
            call.write(ecodes.EV_ABS, ecodes.ABS_MT_POSITION_Y, y),
            call.syn()
        ]
        self.assertEqual(expected_calls, touch._device.mock_calls)

    def assert_finger_up_emitted_write_and_syn(self, touch, slot):
        lift_tracking_id = -1
        release_value = 0
        expected_calls = [
            call.write(ecodes.EV_ABS, ecodes.ABS_MT_SLOT, slot),
            call.write(
                ecodes.EV_ABS, ecodes.ABS_MT_TRACKING_ID, lift_tracking_id),
            call.write(
                ecodes.EV_KEY, ecodes.BTN_TOUCH, release_value),
            call.syn()
        ]
        self.assertEqual(expected_calls, touch._device.mock_calls)

    def test_finger_down_must_use_free_slot(self):
        for slot in range(self._number_of_slots):
            touch = self.get_touch_with_mocked_backend()

            touch.finger_down(0, 0)

            self.assert_finger_down_emitted_write_and_syn(
                touch, slot=slot, tracking_id=ANY, x=0, y=0)

    def test_finger_down_without_free_slots_must_raise_error(self):
        # Claim all the available slots.
        for slot in range(self._number_of_slots):
            touch = self.get_touch_with_mocked_backend()
            touch.finger_down(0, 0)

        touch = self.get_touch_with_mocked_backend()

        # Try to use one more.
        error = self.assertRaises(RuntimeError, touch.finger_down, 11, 11)
        self.assertEqual(
            'All available fingers have been used already.', str(error))

    def test_finger_down_must_use_unique_tracking_id(self):
        for number in range(self._number_of_slots):
            touch = self.get_touch_with_mocked_backend()
            touch.finger_down(0, 0)

            self.assert_finger_down_emitted_write_and_syn(
                touch, slot=ANY, tracking_id=number + 1, x=0, y=0)

    def test_finger_down_must_not_reuse_tracking_ids(self):
        # Claim and release all the available slots once.
        for number in range(self._number_of_slots):
            touch = self.get_touch_with_mocked_backend()
            touch.finger_down(0, 0)
            touch.finger_up()

        touch = self.get_touch_with_mocked_backend()

        touch.finger_down(12, 12)
        self.assert_finger_down_emitted_write_and_syn(
            touch, slot=ANY, tracking_id=number + 2, x=12, y=12)

    def test_finger_down_with_finger_pressed_must_raise_error(self):
        touch = self.get_touch_with_mocked_backend()
        touch.finger_down(0, 0)

        error = self.assertRaises(RuntimeError, touch.finger_down, 0, 0)
        self.assertEqual(
            "Cannot press finger: it's already pressed.", str(error))

    def test_finger_move_without_finger_pressed_must_raise_error(self):
        touch = self.get_touch_with_mocked_backend()

        error = self.assertRaises(RuntimeError, touch.finger_move, 10, 10)
        self.assertEqual(
            'Attempting to move without finger being down.', str(error))

    def test_finger_move_must_use_assigned_slot(self):
        for slot in range(self._number_of_slots):
            touch = self.get_touch_with_mocked_backend()
            touch.finger_down(0, 0)
            touch._device.reset_mock()

            touch.finger_move(10, 10)

            self.assert_finger_move_emitted_write_and_syn(
                touch, slot=slot, x=10, y=10)

    def test_finger_move_must_reuse_assigned_slot(self):
        first_slot = 0
        touch = self.get_touch_with_mocked_backend()
        touch.finger_down(1, 1)
        touch._device.reset_mock()

        touch.finger_move(13, 13)
        self.assert_finger_move_emitted_write_and_syn(
            touch, slot=first_slot, x=13, y=13)
        touch._device.reset_mock()

        touch.finger_move(14, 14)
        self.assert_finger_move_emitted_write_and_syn(
            touch, slot=first_slot, x=14, y=14)

    def test_finger_move_must_log_position_at_debug_level(self):
        self.root_logger.setLevel(logging.DEBUG)
        touch = self.get_touch_with_mocked_backend()
        touch.finger_down(0, 0)

        touch.finger_move(10, 10)
        self.assertLogLevelContains(
            'DEBUG',
            "Moving pointing 'finger' to position 10,10."
        )
        self.assertLogLevelContains(
            'DEBUG',
            "The pointing 'finger' is now at position 10,10."
        )

    def test_finger_up_without_finger_pressed_must_raise_error(self):
        touch = self.get_touch_with_mocked_backend()

        error = self.assertRaises(RuntimeError, touch.finger_up)
        self.assertEqual(
            "Cannot release finger: it's not pressed.", str(error))

    def test_finger_up_must_use_assigned_slot(self):
        fingers = []
        for slot in range(self._number_of_slots):
            touch = self.get_touch_with_mocked_backend()
            touch.finger_down(0, 0)
            touch._device.reset_mock()
            fingers.append(touch)

        for slot, touch in enumerate(fingers):
            touch.finger_up()

            self.assert_finger_up_emitted_write_and_syn(touch, slot=slot)
            touch._device.reset_mock()

    def test_finger_up_must_release_slot(self):
        fingers = []
        # Claim all the available slots.
        for slot in range(self._number_of_slots):
            touch = self.get_touch_with_mocked_backend()
            touch.finger_down(0, 0)
            fingers.append(touch)

        slot_to_reuse = 3
        fingers[slot_to_reuse].finger_up()

        touch = self.get_touch_with_mocked_backend()

        # Try to use one more.
        touch.finger_down(15, 15)
        self.assert_finger_down_emitted_write_and_syn(
            touch, slot=slot_to_reuse, tracking_id=ANY, x=15, y=15)

    def test_device_with_finger_down_must_be_pressed(self):
        touch = self.get_touch_with_mocked_backend()
        touch.finger_down(0, 0)

        self.assertTrue(touch.pressed)

    def test_device_without_finger_down_must_not_be_pressed(self):
        touch = self.get_touch_with_mocked_backend()
        self.assertFalse(touch.pressed)

    def test_device_after_finger_up_must_not_be_pressed(self):
        touch = self.get_touch_with_mocked_backend()
        touch.finger_down(0, 0)
        touch.finger_up()

        self.assertFalse(touch.pressed)

    def test_press_other_device_must_not_press_all_of_them(self):
        other_touch = self.get_touch_with_mocked_backend()
        other_touch.finger_down(0, 0)

        touch = self.get_touch_with_mocked_backend()
        self.assertFalse(touch.pressed)


class UInputTouchBaseTestCase(TestCase):

    def setUp(self):
        super(UInputTouchBaseTestCase, self).setUp()
        # Mock the sleeps so we don't have to spend time actually sleeping.
        self.addCleanup(utilities.sleep.disable_mock)
        utilities.sleep.enable_mock()

    def get_touch_with_mocked_backend(self):
        touch = _uinput.Touch(device_class=Mock)
        touch._device.mock_add_spec(_uinput._UInputTouchDevice)
        return touch


class UInputTouchFingerCoordinatesTestCase(
        testscenarios.TestWithScenarios, UInputTouchBaseTestCase):

    TEST_X_DESTINATION = 10
    TEST_Y_DESTINATION = 10

    scenarios = [
        ('tap', {
            'method': 'tap',
            'args': (TEST_X_DESTINATION, TEST_Y_DESTINATION)
        }),
        ('press', {
            'method': 'press',
            'args': (TEST_X_DESTINATION, TEST_Y_DESTINATION)
        }),
        ('move', {
            'method': 'move',
            'args': (TEST_X_DESTINATION, TEST_Y_DESTINATION)
        }),
        ('drag', {
            'method': 'drag',
            'args': (0, 0, TEST_X_DESTINATION, TEST_Y_DESTINATION)
        })
    ]

    def call_scenario_method(self, object_, method, *args):
        getattr(object_, method)(*self.args)

    def test_method_must_update_finger_coordinates(self):
        touch = self.get_touch_with_mocked_backend()

        self.call_scenario_method(touch, self.method, *self.args)

        self.assertEqual(touch.x, self.TEST_X_DESTINATION)
        self.assertEqual(touch.y, self.TEST_Y_DESTINATION)


class UInputTouchTestCase(UInputTouchBaseTestCase):
    """Test UInput Touch helper for autopilot tests."""

    def test_initial_coordinates_must_be_zero(self):
        touch = self.get_touch_with_mocked_backend()

        self.assertEqual(touch.x, 0)
        self.assertEqual(touch.y, 0)

    def test_tap_must_put_finger_down_then_sleep_and_then_put_finger_up(self):
        expected_calls = [
            call.finger_down(0, 0),
            call.sleep(ANY),
            call.finger_up()
        ]

        touch = self.get_touch_with_mocked_backend()
        with patch('autopilot.input._uinput.sleep') as mock_sleep:
            touch._device.attach_mock(mock_sleep, 'sleep')
            touch.tap(0, 0)
        self.assertEqual(expected_calls, touch._device.mock_calls)

    def test_tap_object_must_put_finger_down_and_then_up_on_the_center(self):
        object_ = make_fake_object(center=True)
        expected_calls = [
            call.finger_down(object_.center_x, object_.center_y),
            call.finger_up()
        ]

        touch = self.get_touch_with_mocked_backend()
        touch.tap_object(object_)
        self.assertEqual(expected_calls, touch._device.mock_calls)

    def test_press_must_put_finger_down(self):
        expected_calls = [call.finger_down(0, 0)]

        touch = self.get_touch_with_mocked_backend()
        touch.press(0, 0)
        self.assertEqual(expected_calls, touch._device.mock_calls)

    def test_release_must_put_finger_up(self):
        expected_calls = [call.finger_up()]

        touch = self.get_touch_with_mocked_backend()
        touch.release()
        self.assertEqual(expected_calls, touch._device.mock_calls)

    def test_move_must_move_finger(self):
        expected_calls = [call.finger_move(10, 10)]

        touch = self.get_touch_with_mocked_backend()
        touch.move(10, 10)
        self.assertEqual(expected_calls, touch._device.mock_calls)

    def test_move_must_move_with_specified_rate(self):
        expected_calls = [
            call.finger_move(5, 5),
            call.finger_move(10, 10),
            call.finger_move(15, 15),
        ]

        touch = self.get_touch_with_mocked_backend()
        touch.move(15, 15, rate=5)

        self.assertEqual(
            expected_calls, touch._device.mock_calls)

    def test_move_without_rate_must_use_default(self):
        expected_calls = [
            call.finger_move(10, 10),
            call.finger_move(20, 20),
        ]

        touch = self.get_touch_with_mocked_backend()
        touch.move(20, 20)

        self.assertEqual(
            expected_calls, touch._device.mock_calls)

    def test_move_to_same_place_must_not_move(self):
        expected_calls = []

        touch = self.get_touch_with_mocked_backend()
        touch.move(0, 0)
        self.assertEqual(expected_calls, touch._device.mock_calls)

    def test_drag_must_call_finger_down_move_and_up(self):
        expected_calls = [
            call.finger_down(0, 0),
            call.finger_move(10, 10),
            call.finger_up()
        ]

        touch = self.get_touch_with_mocked_backend()
        touch.drag(0, 0, 10, 10)
        self.assertEqual(expected_calls, touch._device.mock_calls)

    def test_tap_without_press_duration_must_sleep_default_time(self):
        touch = self.get_touch_with_mocked_backend()

        touch.tap(0, 0)

        self.assertEqual(utilities.sleep.total_time_slept(), 0.1)

    def test_tap_with_press_duration_must_sleep_specified_time(self):
        touch = self.get_touch_with_mocked_backend()

        touch.tap(0, 0, press_duration=10)

        self.assertEqual(utilities.sleep.total_time_slept(), 10)

    def test_tap_object_without_duration_must_call_tap_with_default_time(self):
        object_ = make_fake_object(center=True)
        touch = self.get_touch_with_mocked_backend()

        with patch.object(touch, 'tap') as mock_tap:
            touch.tap_object(object_)

        mock_tap.assert_called_once_with(
            object_.center_x,
            object_.center_y,
            press_duration=0.1,
            time_between_events=0.1
        )

    def test_tap_object_with_duration_must_call_tap_with_specified_time(self):
        object_ = make_fake_object(center=True)
        touch = self.get_touch_with_mocked_backend()

        with patch.object(touch, 'tap') as mock_tap:
            touch.tap_object(
                object_,
                press_duration=10
            )

        mock_tap.assert_called_once_with(
            object_.center_x,
            object_.center_y,
            press_duration=10,
            time_between_events=0.1
        )


class MultipleUInputTouchBackend(_uinput._UInputTouchDevice):

    def __init__(self, res_x=100, res_y=100, device_class=Mock):
        super(MultipleUInputTouchBackend, self).__init__(
            res_x, res_y, device_class)


class MultipleUInputTouchTestCase(TestCase):

    def setUp(self):
        super(MultipleUInputTouchTestCase, self).setUp()
        # Return to the original device after the test.
        self.addCleanup(
            self.set_mouse_device,
            _uinput._UInputTouchDevice._device,
            _uinput._UInputTouchDevice._touch_fingers_in_use,
            _uinput._UInputTouchDevice._last_tracking_id)

    def set_mouse_device(
            self, device, touch_fingers_in_use, last_tracking_id):
        _uinput._UInputTouchDevice._device = device
        _uinput._UInputTouchDevice._touch_fingers_in_use = touch_fingers_in_use
        _uinput._UInputTouchDevice._last_tracking_id = last_tracking_id

    def test_press_other_device_must_not_press_all_of_them(self):
        finger1 = _uinput.Touch(device_class=MultipleUInputTouchBackend)
        finger2 = _uinput.Touch(device_class=MultipleUInputTouchBackend)

        finger1.press(0, 0)
        self.addCleanup(finger1.release)

        self.assertFalse(finger2.pressed)


class MoveWithAnimationUInputTouchTestCase(
        testscenarios.TestWithScenarios, TestCase):

    scenarios = [
        ('move to top', dict(
            start_x=50, start_y=50, stop_x=50, stop_y=30,
            expected_moves=[call.finger_move(50, 40),
                            call.finger_move(50, 30)])),
        ('move to bottom', dict(
            start_x=50, start_y=50, stop_x=50, stop_y=70,
            expected_moves=[call.finger_move(50, 60),
                            call.finger_move(50, 70)])),
        ('move to left', dict(
            start_x=50, start_y=50, stop_x=30, stop_y=50,
            expected_moves=[call.finger_move(40, 50),
                            call.finger_move(30, 50)])),
        ('move to right', dict(
            start_x=50, start_y=50, stop_x=70, stop_y=50,
            expected_moves=[call.finger_move(60, 50),
                            call.finger_move(70, 50)])),

        ('move to top-left', dict(
            start_x=50, start_y=50, stop_x=30, stop_y=30,
            expected_moves=[call.finger_move(40, 40),
                            call.finger_move(30, 30)])),
        ('move to top-right', dict(
            start_x=50, start_y=50, stop_x=70, stop_y=30,
            expected_moves=[call.finger_move(60, 40),
                            call.finger_move(70, 30)])),
        ('move to bottom-left', dict(
            start_x=50, start_y=50, stop_x=30, stop_y=70,
            expected_moves=[call.finger_move(40, 60),
                            call.finger_move(30, 70)])),
        ('move to bottom-right', dict(
            start_x=50, start_y=50, stop_x=70, stop_y=70,
            expected_moves=[call.finger_move(60, 60),
                            call.finger_move(70, 70)])),

        ('move less than rate', dict(
            start_x=50, start_y=50, stop_x=55, stop_y=55,
            expected_moves=[call.finger_move(55, 55)])),

        ('move with last move less than rate', dict(
            start_x=50, start_y=50, stop_x=65, stop_y=65,
            expected_moves=[call.finger_move(60, 60),
                            call.finger_move(65, 65)])),
    ]

    def setUp(self):
        super(MoveWithAnimationUInputTouchTestCase, self).setUp()
        # Mock the sleeps so we don't have to spend time actually sleeping.
        self.addCleanup(utilities.sleep.disable_mock)
        utilities.sleep.enable_mock()

    def get_touch_with_mocked_backend(self):
        touch = _uinput.Touch(device_class=Mock)
        touch._device.mock_add_spec(
            _uinput._UInputTouchDevice, spec_set=True)
        return touch

    def test_drag_moves(self):
        touch = self.get_touch_with_mocked_backend()

        touch.press(self.start_x, self.start_y)
        touch.move(self.stop_x, self.stop_y)

        expected_calls = (
            [call.finger_down(self.start_x, self.start_y)] +
            self.expected_moves)
        self.assertEqual(
            expected_calls, touch._device.mock_calls)


class PointerWithTouchBackendTestCase(TestCase):

    def get_pointer_with_touch_backend_with_mock_device(self):
        touch = _uinput.Touch(device_class=Mock)
        touch._device.mock_add_spec(
            _uinput._UInputTouchDevice, spec_set=True)
        pointer = autopilot.input.Pointer(touch)
        return pointer

    def test_initial_coordinates_must_be_zero(self):
        pointer = self.get_pointer_with_touch_backend_with_mock_device()

        self.assertEqual(pointer.x, 0)
        self.assertEqual(pointer.y, 0)

    def test_drag_must_call_move_with_animation(self):
        test_rate = 2
        test_time_between_events = 1
        test_destination_x = 20
        test_destination_y = 20

        pointer = self.get_pointer_with_touch_backend_with_mock_device()
        with patch.object(pointer._device, 'move') as mock_move:
            pointer.drag(
                0, 0,
                test_destination_x, test_destination_y,
                rate=test_rate, time_between_events=test_time_between_events)

        mock_move.assert_called_once_with(
            test_destination_x, test_destination_y,
            animate=True,
            rate=test_rate, time_between_events=test_time_between_events)

    def test_drag_with_rate(self):
        pointer = self.get_pointer_with_touch_backend_with_mock_device()
        with patch.object(pointer._device, 'drag') as mock_drag:
            pointer.drag(0, 0, 20, 20, rate='test')

        mock_drag.assert_called_once_with(
            0, 0, 20, 20, rate='test', time_between_events=0.01)

    def test_drag_with_time_between_events(self):
        pointer = self.get_pointer_with_touch_backend_with_mock_device()
        with patch.object(pointer._device, 'drag') as mock_drag:
            pointer.drag(0, 0, 20, 20, time_between_events='test')

        mock_drag.assert_called_once_with(
            0, 0, 20, 20, rate=10, time_between_events='test')

    def test_drag_with_default_parameters(self):
        pointer = self.get_pointer_with_touch_backend_with_mock_device()
        with patch.object(pointer._device, 'drag') as mock_drag:
            pointer.drag(0, 0, 20, 20)

        mock_drag.assert_called_once_with(
            0, 0, 20, 20, rate=10, time_between_events=0.01)

    def test_click_with_default_press_duration(self):
        pointer = self.get_pointer_with_touch_backend_with_mock_device()
        with patch.object(pointer._device, 'tap') as mock_tap:
            pointer.click(1)

        mock_tap.assert_called_once_with(
            0, 0, press_duration=0.1, time_between_events=0.1)

    def test_press_with_specified_press_duration(self):
        pointer = self.get_pointer_with_touch_backend_with_mock_device()
        with patch.object(pointer._device, 'tap') as mock_tap:
            pointer.click(1, press_duration=10)

        mock_tap.assert_called_once_with(
            0, 0, press_duration=10, time_between_events=0.1)

    def test_not_pressed_move_must_not_move_pointing_figer(self):
        """Test for moving the finger when it is not pressed.

        The move method on the pointer class must update the finger coordinates
        but it must not execute a move on the device.

        """
        test_x_destination = 20
        test_y_destination = 20
        pointer = self.get_pointer_with_touch_backend_with_mock_device()

        pointer.move(10, 10)
        pointer._device._device.pressed = False

        with patch.object(pointer._device._device, 'finger_move') as mock_move:
            pointer.move(test_x_destination, test_y_destination)

        self.assertFalse(mock_move.called)
        self.assertEqual(pointer.x, test_x_destination)
        self.assertEqual(pointer.y, test_y_destination)

    def test_pressed_move_must_move_pointing_finger(self):
        test_x_destination = 20
        test_y_destination = 20

        pointer = self.get_pointer_with_touch_backend_with_mock_device()

        pointer.move(10, 10)
        pointer._device._device.pressed = True

        with patch.object(pointer._device._device, 'finger_move') as mock_move:
            pointer.move(test_x_destination, test_y_destination)

        mock_move.assert_called_once_with(20, 20)
        self.assertEqual(pointer.x, test_x_destination)
        self.assertEqual(pointer.y, test_y_destination)

    def test_press_must_put_finger_down_at_last_move_position(self):
        pointer = self.get_pointer_with_touch_backend_with_mock_device()
        pointer.move(10, 10)

        pointer.press()

        pointer._device._device.finger_down.assert_called_once_with(10, 10)


class UInputPowerButtonTestCase(TestCase):

    def get_mock_hardware_keys_device(self):
        power_button = _uinput.UInputHardwareKeysDevice(device_class=Mock)
        power_button._device.mock_add_spec(uinput.UInput, spec_set=True)
        return power_button

    def assert_power_button_press_release_emitted_write_and_sync(self, calls):
        expected_calls = [
            call.write(ecodes.EV_KEY, ecodes.KEY_POWER, 1),
            call.write(ecodes.EV_KEY, ecodes.KEY_POWER, 0),
            call.syn(),
        ]
        self.assertEquals(expected_calls, calls)

    def test_power_button_press_release_emitted_write_and_sync(self):
        device = self.get_mock_hardware_keys_device()
        device.press_and_release_power_button()
        self.assert_power_button_press_release_emitted_write_and_sync(
            device._device.mock_calls
        )


class KeyboardTestCase(unittest.TestCase):

    @patch('autopilot.input._pick_backend')
    def test_input_backends_default_order(self, pick_backend):
        k = Keyboard()
        k.create()

        backends = list(pick_backend.call_args[0][0].items())
        self.assertTrue(backends[0][0] == 'X11')
        self.assertTrue(backends[1][0] == 'OSK')
        self.assertTrue(backends[2][0] == 'UInput')
