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

from datetime import datetime, time
from testscenarios import TestWithScenarios, multiply_scenarios
from testtools import TestCase
from testtools.matchers import Equals, IsInstance, NotEquals, raises

import dbus
from unittest.mock import patch, Mock

from autopilot.tests.functional.fixtures import Timezone
from autopilot.introspection.types import (
    Color,
    create_value_instance,
    DateTime,
    PlainType,
    Point,
    Point3D,
    Rectangle,
    Size,
    Time,
    ValueType,
    _integer_repr,
    _boolean_repr,
    _text_repr,
    _bytes_repr,
    _dict_repr,
    _list_repr,
    _float_repr,
    _tuple_repr,
    _get_repr_callable_for_value_class,
    _boolean_str,
    _integer_str,
)
from autopilot.introspection.dbus import DBusIntrospectionObject
from autopilot.utilities import compatible_repr

from dateutil import tz


class PlainTypeTests(TestWithScenarios, TestCase):

    scenarios = [
        ('bool true', dict(t=dbus.Boolean, v=True)),
        ('bool false', dict(t=dbus.Boolean, v=False)),
        ('byte', dict(t=dbus.Byte, v=12)),
        ('int16 +ve', dict(t=dbus.Int16, v=123)),
        ('int16 -ve', dict(t=dbus.Int16, v=-23000)),
        ('int32 +ve', dict(t=dbus.Int32, v=30000000)),
        ('int32 -ve', dict(t=dbus.Int32, v=-3002050)),
        ('int64 +ve', dict(t=dbus.Int64, v=9223372036854775807)),
        ('int64 -ve', dict(t=dbus.Int64, v=-9223372036854775807)),
        ('ascii string', dict(t=dbus.String, v="Hello World")),
        ('unicode string', dict(t=dbus.String, v="\u2603")),
        ('bytearray', dict(t=dbus.ByteArray, v=b"Hello World")),
        ('object path', dict(t=dbus.ObjectPath, v="/path/to/object")),
        ('dbus signature', dict(t=dbus.Signature, v="is")),
        ('dictionary', dict(t=dbus.Dictionary, v={'hello': 'world'})),
        ('double', dict(t=dbus.Double, v=3.1415)),
        ('struct', dict(t=dbus.Struct, v=('some', 42, 'value'))),
        ('array', dict(t=dbus.Array, v=['some', 42, 'value'])),
    ]

    def test_can_construct(self):
        p = PlainType(self.t(self.v))

        self.assertThat(p, Equals(self.v))
        self.assertThat(hasattr(p, 'wait_for'), Equals(True))
        self.assertThat(p, IsInstance(self.t))

    def test_repr(self):
        """repr for PlainType must be the same as the pythonic type."""
        p = PlainType(self.t(self.v))

        expected = repr(self.v)
        expected = expected.rstrip('L')
        self.assertThat(repr(p), Equals(expected))

    def test_str(self):
        """str(p) for PlainType must be the same as the pythonic type."""
        p = PlainType(self.t(self.v))
        expected = str(self.v)
        observed = str(p)
        self.assertEqual(expected, observed)

    def test_wait_for_raises_RuntimeError(self):
        """The wait_for method must raise a RuntimeError if it's called."""
        p = PlainType(self.t(self.v))
        self.assertThat(
            lambda: p.wait_for(object()),
            raises(RuntimeError(
                "This variable was not constructed as part of "
                "an object. The wait_for method cannot be used."
            ))
        )


class RectangleTypeTests(TestCase):

    def test_can_construct_rectangle(self):
        r = Rectangle(1, 2, 3, 4)
        self.assertThat(r, IsInstance(dbus.Array))

    def test_rectangle_has_xywh_properties(self):
        r = Rectangle(1, 2, 3, 4)

        self.assertThat(r.x, Equals(1))
        self.assertThat(r.y, Equals(2))
        self.assertThat(r.w, Equals(3))
        self.assertThat(r.width, Equals(3))
        self.assertThat(r.h, Equals(4))
        self.assertThat(r.height, Equals(4))

    def test_rectangle_has_slice_access(self):
        r = Rectangle(1, 2, 3, 4)

        self.assertThat(r[0], Equals(1))
        self.assertThat(r[1], Equals(2))
        self.assertThat(r[2], Equals(3))
        self.assertThat(r[3], Equals(4))

    def test_equality_with_rectangle(self):
        r1 = Rectangle(1, 2, 3, 4)
        r2 = Rectangle(1, 2, 3, 4)

        self.assertThat(r1, Equals(r2))

    def test_equality_with_list(self):
        r1 = Rectangle(1, 2, 3, 4)
        r2 = [1, 2, 3, 4]

        self.assertThat(r1, Equals(r2))

    def test_repr(self):
        expected = repr_type("Rectangle(1, 2, 3, 4)")
        observed = repr(Rectangle(1, 2, 3, 4))
        self.assertEqual(expected, observed)

    def test_repr_equals_str(self):
        r = Rectangle(1, 2, 3, 4)
        self.assertEqual(repr(r), str(r))


class PointTypeTests(TestCase):

    def test_can_construct_point(self):
        r = Point(1, 2)
        self.assertThat(r, IsInstance(dbus.Array))

    def test_point_has_xy_properties(self):
        r = Point(1, 2)

        self.assertThat(r.x, Equals(1))
        self.assertThat(r.y, Equals(2))

    def test_point_has_slice_access(self):
        r = Point(1, 2)

        self.assertThat(r[0], Equals(1))
        self.assertThat(r[1], Equals(2))

    def test_equality_with_point(self):
        p1 = Point(1, 2)
        p2 = Point(1, 2)

        self.assertThat(p1, Equals(p2))

    def test_equality_with_list(self):
        p1 = Point(1, 2)
        p2 = [1, 2]

        self.assertThat(p1, Equals(p2))

    def test_repr(self):
        expected = repr_type('Point(1, 2)')
        observed = repr(Point(1, 2))
        self.assertEqual(expected, observed)

    def test_repr_equals_str(self):
        p = Point(1, 2)
        self.assertEqual(repr(p), str(p))


class SizeTypeTests(TestCase):

    def test_can_construct_size(self):
        r = Size(1, 2)
        self.assertThat(r, IsInstance(dbus.Array))

    def test_size_has_wh_properties(self):
        r = Size(1, 2)

        self.assertThat(r.w, Equals(1))
        self.assertThat(r.width, Equals(1))
        self.assertThat(r.h, Equals(2))
        self.assertThat(r.height, Equals(2))

    def test_size_has_slice_access(self):
        r = Size(1, 2)

        self.assertThat(r[0], Equals(1))
        self.assertThat(r[1], Equals(2))

    def test_equality_with_size(self):
        s1 = Size(50, 100)
        s2 = Size(50, 100)

        self.assertThat(s1, Equals(s2))

    def test_equality_with_list(self):
        s1 = Size(50, 100)
        s2 = [50, 100]

        self.assertThat(s1, Equals(s2))

    def test_repr(self):
        expected = repr_type('Size(1, 2)')
        observed = repr(Size(1, 2))
        self.assertEqual(expected, observed)

    def test_repr_equals_str(self):
        s = Size(3, 4)
        self.assertEqual(repr(s), str(s))


class ColorTypeTests(TestCase):

    def test_can_construct_color(self):
        r = Color(123, 234, 55, 255)
        self.assertThat(r, IsInstance(dbus.Array))

    def test_color_has_rgba_properties(self):
        r = Color(123, 234, 55, 255)

        self.assertThat(r.red, Equals(123))
        self.assertThat(r.green, Equals(234))
        self.assertThat(r.blue, Equals(55))
        self.assertThat(r.alpha, Equals(255))

    def test_color_has_slice_access(self):
        r = Color(123, 234, 55, 255)

        self.assertThat(r[0], Equals(123))
        self.assertThat(r[1], Equals(234))
        self.assertThat(r[2], Equals(55))
        self.assertThat(r[3], Equals(255))

    def test_eqiality_with_color(self):
        c1 = Color(123, 234, 55, 255)
        c2 = Color(123, 234, 55, 255)

        self.assertThat(c1, Equals(c2))

    def test_eqiality_with_list(self):
        c1 = Color(123, 234, 55, 255)
        c2 = [123, 234, 55, 255]

        self.assertThat(c1, Equals(c2))

    def test_repr(self):
        expected = repr_type('Color(1, 2, 3, 4)')
        observed = repr(Color(1, 2, 3, 4))
        self.assertEqual(expected, observed)

    def test_repr_equals_str(self):
        c = Color(255, 255, 255, 0)
        self.assertEqual(repr(c), str(c))


def unable_to_handle_timestamp(timestamp):
    """Return false if the platform can handle timestamps larger than 32bit
    limit.

    """
    try:
        datetime.fromtimestamp(timestamp)
        return False
    except:
        return True


class DateTimeCreationTests(TestCase):

    timestamp = 1405382400  # No significance, just a timestamp

    def test_can_construct_datetime(self):
        dt = DateTime(self.timestamp)
        self.assertThat(dt, IsInstance(dbus.Array))

    def test_datetime_has_slice_access(self):
        dt = DateTime(self.timestamp)
        self.assertThat(dt[0], Equals(self.timestamp))

    def test_datetime_has_properties(self):
        dt = DateTime(self.timestamp)

        self.assertTrue(hasattr(dt, 'timestamp'))
        self.assertTrue(hasattr(dt, 'year'))
        self.assertTrue(hasattr(dt, 'month'))
        self.assertTrue(hasattr(dt, 'day'))
        self.assertTrue(hasattr(dt, 'hour'))
        self.assertTrue(hasattr(dt, 'minute'))
        self.assertTrue(hasattr(dt, 'second'))

    def test_repr(self):
        # Use a well known timezone for comparison
        self.useFixture(Timezone('UTC'))
        dt = DateTime(self.timestamp)
        observed = repr(dt)

        expected = "DateTime({:%Y-%m-%d %H:%M:%S})".format(
            datetime.fromtimestamp(self.timestamp)
        )
        self.assertEqual(expected, observed)

    def test_repr_equals_str(self):
        dt = DateTime(self.timestamp)
        self.assertEqual(repr(dt), str(dt))

    def test_can_create_DateTime_using_large_timestamp(self):
        """Must be able to create a DateTime object using a timestamp larger
        than the 32bit time_t limit.

        """
        # Use a well known timezone for comparison
        self.useFixture(Timezone('UTC'))
        large_timestamp = 2**32+1
        dt = DateTime(large_timestamp)

        self.assertEqual(dt.year, 2106)
        self.assertEqual(dt.month, 2)
        self.assertEqual(dt.day, 7)
        self.assertEqual(dt.hour, 6)
        self.assertEqual(dt.minute, 28)
        self.assertEqual(dt.second, 17)
        self.assertEqual(dt.timestamp, large_timestamp)


class DateTimeTests(TestWithScenarios, TestCase):

    timestamps = [
        # This timestamp uncovered an issue during development.
        ('Explicit US/Pacific test', dict(
            timestamp=1090123200
        )),
        ('September 2014', dict(
            timestamp=1411992000
        )),

        ('NZ DST example', dict(
            timestamp=2047570047
        )),

        ('Winter', dict(
            timestamp=1389744000
        )),

        ('Summer', dict(
            timestamp=1405382400
        )),

        ('32bit max', dict(
            timestamp=2**32+1
        )),

        ('32bit limit', dict(
            timestamp=2983579200
        )),

    ]

    timezones = [
        ('UTC', dict(
            timezone='UTC'
        )),

        ('London', dict(
            timezone='Europe/London'
        )),

        ('New Zealand', dict(
            timezone='NZ',
        )),

        ('Pacific', dict(
            timezone='US/Pacific'
        )),

        ('Hongkong', dict(
            timezone='Hongkong'
        )),

        ('Moscow', dict(
            timezone='Europe/Moscow'
        )),

        ('Copenhagen', dict(
            timezone='Europe/Copenhagen',
        )),
    ]

    scenarios = multiply_scenarios(timestamps, timezones)

    def skip_if_timestamp_too_large(self, timestamp):
        if unable_to_handle_timestamp(self.timestamp):
            self.skip("Timestamp to large for platform time_t")

    def test_datetime_properties_have_correct_values(self):
        self.skip_if_timestamp_too_large(self.timestamp)
        self.useFixture(Timezone(self.timezone))

        dt1 = DateTime(self.timestamp)
        dt2 = datetime.fromtimestamp(self.timestamp, tz.gettz())

        self.assertThat(dt1.year, Equals(dt2.year))
        self.assertThat(dt1.month, Equals(dt2.month))
        self.assertThat(dt1.day, Equals(dt2.day))
        self.assertThat(dt1.hour, Equals(dt2.hour))
        self.assertThat(dt1.minute, Equals(dt2.minute))
        self.assertThat(dt1.second, Equals(dt2.second))
        self.assertThat(dt1.timestamp, Equals(dt2.timestamp()))

    def test_equality_with_datetime(self):
        self.skip_if_timestamp_too_large(self.timestamp)
        self.useFixture(Timezone(self.timezone))

        dt1 = DateTime(self.timestamp)
        dt2 = datetime(
            dt1.year, dt1.month, dt1.day, dt1.hour, dt1.minute, dt1.second
        )

        self.assertThat(dt1, Equals(dt2))

    def test_equality_with_list(self):
        self.skip_if_timestamp_too_large(self.timestamp)
        self.useFixture(Timezone(self.timezone))

        dt1 = DateTime(self.timestamp)
        dt2 = [self.timestamp]

        self.assertThat(dt1, Equals(dt2))

    def test_equality_with_datetime_object(self):
        self.skip_if_timestamp_too_large(self.timestamp)
        self.useFixture(Timezone(self.timezone))

        dt1 = DateTime(self.timestamp)
        dt2 = datetime.fromtimestamp(self.timestamp, tz.gettz())
        dt3 = datetime.fromtimestamp(self.timestamp + 1, tz.gettz())

        self.assertThat(dt1, Equals(dt2))
        self.assertThat(dt1, NotEquals(dt3))

    def test_can_convert_to_datetime(self):
        self.skip_if_timestamp_too_large(self.timestamp)

        dt1 = DateTime(self.timestamp)
        self.assertThat(dt1.datetime, IsInstance(datetime))


class TimeTests(TestCase):

    def test_can_construct_time(self):
        dt = Time(0, 0, 0, 0)
        self.assertThat(dt, IsInstance(dbus.Array))

    def test_time_has_slice_access(self):
        dt = Time(0, 1, 2, 3)

        self.assertThat(dt[0], Equals(0))
        self.assertThat(dt[1], Equals(1))
        self.assertThat(dt[2], Equals(2))
        self.assertThat(dt[3], Equals(3))

    def test_time_has_properties(self):
        dt = Time(0, 1, 2, 3)

        self.assertThat(dt.hour, Equals(0))
        self.assertThat(dt.minute, Equals(1))
        self.assertThat(dt.second, Equals(2))
        self.assertThat(dt.millisecond, Equals(3))

    def test_equality_with_time(self):
        dt1 = Time(0, 1, 2, 3)
        dt2 = Time(0, 1, 2, 3)
        dt3 = Time(4, 1, 2, 3)

        self.assertThat(dt1, Equals(dt2))
        self.assertThat(dt1, NotEquals(dt3))

    def test_equality_with_real_time(self):
        dt1 = Time(2, 3, 4, 5)
        dt2 = time(2, 3, 4, 5000)
        dt3 = time(5, 4, 3, 2000)

        self.assertThat(dt1, Equals(dt2))
        self.assertThat(dt1, NotEquals(dt3))

    def test_can_convert_to_time(self):
        dt1 = Time(1, 2, 3, 4)

        self.assertThat(dt1.time, IsInstance(time))

    def test_repr(self):
        expected = repr_type('Time(01:02:03.004)')
        observed = repr(Time(1, 2, 3, 4))
        self.assertEqual(expected, observed)

    def test_repr_equals_str(self):
        t = Time(2, 3, 4, 5)
        self.assertEqual(repr(t), str(t))


class Point3DTypeTests(TestCase):

    def test_can_construct_point3d(self):
        r = Point3D(1, 2, 3)
        self.assertThat(r, IsInstance(dbus.Array))

    def test_point3d_has_xyz_properties(self):
        r = Point3D(1, 2, 3)

        self.assertThat(r.x, Equals(1))
        self.assertThat(r.y, Equals(2))
        self.assertThat(r.z, Equals(3))

    def test_point3d_has_slice_access(self):
        r = Point3D(1, 2, 3)

        self.assertThat(r[0], Equals(1))
        self.assertThat(r[1], Equals(2))
        self.assertThat(r[2], Equals(3))

    def test_equality_with_point3d(self):
        p1 = Point3D(1, 2, 3)
        p2 = Point3D(1, 2, 3)

        self.assertThat(p1, Equals(p2))

    def test_inequality_with_point3d(self):
        p1 = Point3D(1, 2, 3)
        p2 = Point3D(1, 2, 4)

        self.assertThat(p1, NotEquals(p2))

    def test_equality_with_list(self):
        p1 = Point3D(1, 2, 3)
        p2 = [1, 2, 3]

        self.assertThat(p1, Equals(p2))

    def test_inequality_with_list(self):
        p1 = Point3D(1, 2, 3)
        p2 = [1, 2, 4]

        self.assertThat(p1, NotEquals(p2))

    def test_repr(self):
        expected = repr_type('Point3D(1, 2, 3)')
        observed = repr(Point3D(1, 2, 3))
        self.assertEqual(expected, observed)

    def test_repr_equals_str(self):
        p3d = Point3D(1, 2, 3)
        self.assertEqual(repr(p3d), str(p3d))


class CreateValueInstanceTests(TestCase):

    """Tests to check that create_value_instance does the right thing."""

    def test_plain_string(self):
        data = dbus.Array([dbus.Int32(ValueType.PLAIN), dbus.String("Hello")])
        attr = create_value_instance(data, None, None)

        self.assertThat(attr, Equals("Hello"))
        self.assertThat(attr, IsInstance(PlainType))

    def test_plain_boolean(self):
        data = dbus.Array([dbus.Int32(ValueType.PLAIN), dbus.Boolean(False)])
        attr = create_value_instance(data, None, None)

        self.assertThat(attr, Equals(False))
        self.assertThat(attr, IsInstance(PlainType))

    def test_plain_int16(self):
        data = dbus.Array([dbus.Int32(ValueType.PLAIN), dbus.Int16(-2**14)])
        attr = create_value_instance(data, None, None)

        self.assertThat(attr, Equals(-2**14))
        self.assertThat(attr, IsInstance(PlainType))

    def test_plain_int32(self):
        data = dbus.Array([dbus.Int32(ValueType.PLAIN), dbus.Int32(-2**30)])
        attr = create_value_instance(data, None, None)

        self.assertThat(attr, Equals(-2**30))
        self.assertThat(attr, IsInstance(PlainType))

    def test_plain_int64(self):
        data = dbus.Array([dbus.Int32(ValueType.PLAIN), dbus.Int64(-2**40)])
        attr = create_value_instance(data, None, None)

        self.assertThat(attr, Equals(-2**40))
        self.assertThat(attr, IsInstance(PlainType))

    def test_plain_uint16(self):
        data = dbus.Array([dbus.Int32(ValueType.PLAIN), dbus.UInt16(2**14)])
        attr = create_value_instance(data, None, None)

        self.assertThat(attr, Equals(2**14))
        self.assertThat(attr, IsInstance(PlainType))

    def test_plain_uint32(self):
        data = dbus.Array([dbus.Int32(ValueType.PLAIN), dbus.UInt32(2**30)])
        attr = create_value_instance(data, None, None)

        self.assertThat(attr, Equals(2**30))
        self.assertThat(attr, IsInstance(PlainType))

    def test_plain_uint64(self):
        data = dbus.Array([dbus.Int32(ValueType.PLAIN), dbus.UInt64(2**40)])
        attr = create_value_instance(data, None, None)

        self.assertThat(attr, Equals(2**40))
        self.assertThat(attr, IsInstance(PlainType))

    def test_plain_array(self):
        data = dbus.Array([
            dbus.Int32(ValueType.PLAIN),
            dbus.Array([
                dbus.String("Hello"),
                dbus.String("World")
            ])
        ])
        attr = create_value_instance(data, None, None)
        self.assertThat(attr, Equals(["Hello", "World"]))
        self.assertThat(attr, IsInstance(PlainType))

    def test_rectangle(self):
        data = dbus.Array(
            [
                dbus.Int32(ValueType.RECTANGLE),
                dbus.Int32(0),
                dbus.Int32(10),
                dbus.Int32(20),
                dbus.Int32(30),
            ]
        )

        attr = create_value_instance(data, None, None)

        self.assertThat(attr, IsInstance(Rectangle))

    def test_invalid_rectangle(self):
        data = dbus.Array(
            [
                dbus.Int32(ValueType.RECTANGLE),
                dbus.Int32(0),
            ]
        )

        fn = lambda: create_value_instance(data, None, None)

        self.assertThat(fn, raises(
            ValueError("Rectangle must be constructed with 4 arguments, not 1")
        ))

    def test_color(self):
        data = dbus.Array(
            [
                dbus.Int32(ValueType.COLOR),
                dbus.Int32(10),
                dbus.Int32(20),
                dbus.Int32(230),
                dbus.Int32(255),
            ]
        )

        attr = create_value_instance(data, None, None)

        self.assertThat(attr, IsInstance(Color))

    def test_invalid_color(self):
        data = dbus.Array(
            [
                dbus.Int32(ValueType.COLOR),
                dbus.Int32(0),
            ]
        )

        fn = lambda: create_value_instance(data, None, None)

        self.assertThat(fn, raises(
            ValueError("Color must be constructed with 4 arguments, not 1")
        ))

    def test_point(self):
        data = dbus.Array(
            [
                dbus.Int32(ValueType.POINT),
                dbus.Int32(0),
                dbus.Int32(10),
            ]
        )

        attr = create_value_instance(data, None, None)

        self.assertThat(attr, IsInstance(Point))

    def test_invalid_point(self):
        data = dbus.Array(
            [
                dbus.Int32(ValueType.POINT),
                dbus.Int32(0),
                dbus.Int32(0),
                dbus.Int32(0),
            ]
        )

        fn = lambda: create_value_instance(data, None, None)

        self.assertThat(fn, raises(
            ValueError("Point must be constructed with 2 arguments, not 3")
        ))

    def test_size(self):
        data = dbus.Array(
            [
                dbus.Int32(ValueType.SIZE),
                dbus.Int32(0),
                dbus.Int32(10),
            ]
        )

        attr = create_value_instance(data, None, None)

        self.assertThat(attr, IsInstance(Size))

    def test_invalid_size(self):
        data = dbus.Array(
            [
                dbus.Int32(ValueType.SIZE),
                dbus.Int32(0),
            ]
        )

        fn = lambda: create_value_instance(data, None, None)

        self.assertThat(fn, raises(
            ValueError("Size must be constructed with 2 arguments, not 1")
        ))

    def test_date_time(self):
        data = dbus.Array(
            [
                dbus.Int32(ValueType.DATETIME),
                dbus.Int32(0),
            ]
        )

        attr = create_value_instance(data, None, None)

        self.assertThat(attr, IsInstance(DateTime))

    def test_invalid_date_time(self):
        data = dbus.Array(
            [
                dbus.Int32(ValueType.DATETIME),
                dbus.Int32(0),
                dbus.Int32(0),
                dbus.Int32(0),
            ]
        )

        fn = lambda: create_value_instance(data, None, None)

        self.assertThat(fn, raises(
            ValueError("DateTime must be constructed with 1 arguments, not 3")
        ))

    def test_time(self):
        data = dbus.Array(
            [
                dbus.Int32(ValueType.TIME),
                dbus.Int32(0),
                dbus.Int32(0),
                dbus.Int32(0),
                dbus.Int32(0),
            ]
        )

        attr = create_value_instance(data, None, None)

        self.assertThat(attr, IsInstance(Time))

    def test_invalid_time(self):
        data = dbus.Array(
            [
                dbus.Int32(ValueType.TIME),
                dbus.Int32(0),
                dbus.Int32(0),
                dbus.Int32(0),
            ]
        )

        fn = lambda: create_value_instance(data, None, None)

        self.assertThat(fn, raises(
            ValueError("Time must be constructed with 4 arguments, not 3")
        ))

    def test_unknown_type_id(self):
        """Unknown type Ids should result in a plain type, along with a log
        message.

        """

        data = dbus.Array(
            [
                dbus.Int32(543),
                dbus.Int32(0),
                dbus.Boolean(False),
                dbus.String("Hello World")
            ]
        )
        attr = create_value_instance(data, None, None)
        self.assertThat(attr, IsInstance(PlainType))
        self.assertThat(attr, IsInstance(dbus.Array))
        self.assertThat(attr, Equals([0, False, "Hello World"]))

    def test_invalid_no_data(self):
        data = dbus.Array(
            [
                dbus.Int32(0),
            ]
        )
        fn = lambda: create_value_instance(data, None, None)

        self.assertThat(fn, raises(
            ValueError("Cannot create attribute, no data supplied")
        ))

    def test_point3d(self):
        data = dbus.Array(
            [
                dbus.Int32(ValueType.POINT3D),
                dbus.Int32(0),
                dbus.Int32(10),
                dbus.Int32(20),
            ]
        )

        attr = create_value_instance(data, None, None)

        self.assertThat(attr, IsInstance(Point3D))

    def test_invalid_point3d(self):
        data = dbus.Array(
            [
                dbus.Int32(ValueType.POINT3D),
                dbus.Int32(0),
                dbus.Int32(0),
            ]
        )

        fn = lambda: create_value_instance(data, None, None)

        self.assertThat(fn, raises(
            ValueError("Point3D must be constructed with 3 arguments, not 2")
        ))


class DBusIntrospectionObjectTests(TestCase):

    @patch('autopilot.introspection.dbus._logger.warning')
    def test_dbus_introspection_object_logs_bad_data(self, error_logger):
        """The DBusIntrospectionObject class must log an error when it gets
        bad data from the autopilot backend.

        """
        DBusIntrospectionObject(
            dict(foo=[0], id=[0, 42]),
            b'/some/dummy/path',
            Mock()
        )
        error_logger.assert_called_once_with(
            "While constructing attribute '%s.%s': %s",
            "ProxyBase",
            "foo",
            "Cannot create attribute, no data supplied"
        )


class TypeReprTests(TestCase):

    def test_integer_repr(self):
        expected = repr_type('42')
        observed = _integer_repr(42)
        self.assertEqual(expected, observed)

    def test_dbus_int_types_all_work(self):
        expected = repr_type('42')
        int_types = (
            dbus.Byte,
            dbus.Int16,
            dbus.Int32,
            dbus.UInt16,
            dbus.UInt32,
            dbus.Int64,
            dbus.UInt64,
        )
        for t in int_types:
            observed = _integer_repr(t(42))
            self.assertEqual(expected, observed)

    def test_get_repr_gets_integer_repr_for_all_integer_types(self):
        int_types = (
            dbus.Byte,
            dbus.Int16,
            dbus.Int32,
            dbus.UInt16,
            dbus.UInt32,
            dbus.Int64,
            dbus.UInt64,
        )
        for t in int_types:
            observed = _get_repr_callable_for_value_class(t)
            self.assertEqual(_integer_repr, observed)

    def test_boolean_repr_true(self):
        expected = repr_type('True')
        for values in (True, dbus.Boolean(True)):
            observed = _boolean_repr(True)
            self.assertEqual(expected, observed)

    def test_boolean_repr_false(self):
        expected = repr_type('False')
        for values in (False, dbus.Boolean(False)):
            observed = _boolean_repr(False)
            self.assertEqual(expected, observed)

    def test_get_repr_gets_boolean_repr_for_dbus_boolean_type(self):
        observed = _get_repr_callable_for_value_class(dbus.Boolean)
        self.assertEqual(_boolean_repr, observed)

    def test_text_repr_handles_dbus_string(self):
        unicode_text = "plɹoʍ ollǝɥ"
        observed = _text_repr(dbus.String(unicode_text))
        self.assertEqual(repr(unicode_text), observed)

    def test_text_repr_handles_dbus_object_path(self):
        path = "/path/to/some/object"
        observed = _text_repr(dbus.ObjectPath(path))
        self.assertEqual(repr(path), observed)

    def test_binry_repr_handles_dbys_byte_array(self):
        data = b'Some bytes'
        observed = _bytes_repr(dbus.ByteArray(data))
        self.assertEqual(repr(data), observed)

    def test_get_repr_gets_bytes_repr_for_dbus_byte_array(self):
        observed = _get_repr_callable_for_value_class(dbus.ByteArray)
        self.assertEqual(_bytes_repr, observed)

    def test_dict_repr_handles_dbus_dictionary(self):
        token = dict(foo='bar')
        observed = _dict_repr(dbus.Dictionary(token))
        self.assertEqual(repr(token), observed)

    def test_get_repr_gets_dict_repr_on_dbus_dictionary(self):
        observed = _get_repr_callable_for_value_class(dbus.Dictionary)
        self.assertEqual(_dict_repr, observed)

    def test_float_repr_handles_dbus_double(self):
        token = 1.2345
        observed = _float_repr(token)
        self.assertEqual(repr(token), observed)

    def test_get_repr_gets_float_repr_on_dbus_double(self):
        observed = _get_repr_callable_for_value_class(dbus.Double)
        self.assertEqual(_float_repr, observed)

    def test_tuple_repr_handles_dbus_struct(self):
        data = (1, 2, 3)
        observed = _tuple_repr(dbus.Struct(data))
        self.assertEqual(repr(data), observed)

    def test_get_repr_gets_tuple_repr_on_dbus_struct(self):
        observed = _get_repr_callable_for_value_class(dbus.Struct)
        self.assertEqual(_tuple_repr, observed)

    def test_list_repr_handles_dbus_array(self):
        data = [1, 2, 3]
        observed = _list_repr(dbus.Array(data))
        self.assertEqual(repr(data), observed)

    def test_get_repr_gets_list_repr_on_dbus_array(self):
        observed = _get_repr_callable_for_value_class(dbus.Array)
        self.assertEqual(_list_repr, observed)


class TypeStrTests(TestCase):

    def test_boolean_str_handles_dbus_boolean(self):
        observed = _boolean_str(dbus.Boolean(False))
        self.assertEqual(str(False), observed)

    def test_integer_str_handles_dbus_byte(self):
        observed = _integer_str(dbus.Byte(14))
        self.assertEqual(str(14), observed)


def repr_type(value):
    """Convert a text or bytes object into the appropriate return type for
    the __repr__ method."""
    return compatible_repr(lambda: value)()
