# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2013-2014 Canonical
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

from datetime import datetime

from autopilot.testcase import AutopilotTestCase
from autopilot.tests.functional import QmlScriptRunnerMixin
from autopilot.tests.functional.fixtures import Timezone

from textwrap import dedent


class DateTimeTests(AutopilotTestCase, QmlScriptRunnerMixin):
    scenarios = [
        ('UTC', dict(
            TZ='UTC',
        )),
        ('NZ', dict(
            TZ='Pacific/Auckland',
        )),
        ('US Central', dict(
            TZ='US/Central',
        )),
        ('US Eastern', dict(
            TZ='US/Eastern',
        )),
        ('Hongkong', dict(
            TZ='Hongkong'
        )),
        ('CET', dict(
            TZ='Europe/Copenhagen',
        )),
        # QML timezone database is incorrect/out-of-date for
        # Europe/Moscow. Given the timestamp of 1411992000 (UTC: 2014:9:29
        # 12:00) for this date offset should be +0400
        # (http://en.wikipedia.org/wiki/Time_in_Russia#Daylight_saving_time)
        # QML app gives: 2014:9:29 14:00 where it should be 2014:9:29 16:00
        # ('MSK', dict(
        #     TZ='Europe/Moscow',
        # )),
    ]

    def get_test_qml_string(self, date_string):
        return dedent("""
            import QtQuick 2.0
            import QtQml 2.2
            Rectangle {
                property date testingTime: new Date(%s);
                Text {
                    text: testingTime;
                }
            }""" % date_string)

    def test_qml_applies_timezone_to_timestamp(self):
        """Test that when given a timestamp the datetime displayed has the
        timezone applied to it.

        QML will apply a timezone calculation to a timestamp (but not a
        timestring).

        """
        self.useFixture(Timezone(self.TZ))

        timestamp = 1411992000
        timestamp_ms = 1411992000 * 1000

        qml_script = self.get_test_qml_string(timestamp_ms)
        expected_string = datetime.fromtimestamp(timestamp).strftime('%FT%T')

        proxy = self.start_qml_script(qml_script)
        self.assertEqual(
            proxy.select_single('QQuickText').text,
            expected_string
        )

    def test_timezone_not_applied_to_timestring(self):
        """Test that, in all timezones, the literal representation we get in
        the proxy object matches the one in the Qml script.

        """
        self.useFixture(Timezone(self.TZ))

        qml_script = self.get_test_qml_string("'2014-01-15 12:34:52'")
        proxy = self.start_qml_script(qml_script)
        date_object = proxy.select_single("QQuickRectangle").testingTime

        self.assertEqual(date_object.year, 2014)
        self.assertEqual(date_object.month, 1)
        self.assertEqual(date_object.day, 15)
        self.assertEqual(date_object.hour, 12)
        self.assertEqual(date_object.minute, 34)
        self.assertEqual(date_object.second, 52)
        self.assertEqual(datetime(2014, 1, 15, 12, 34, 52), date_object)
