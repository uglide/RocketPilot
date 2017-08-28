# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2014 Canonical
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


from testtools import TestCase
from testtools.matchers import raises
from unittest.mock import patch, Mock
import autopilot._fixtures as ap_fixtures


class FixtureWithDirectAddDetailTests(TestCase):

    def test_sets_caseAddDetail_method(self):
        fixture = ap_fixtures.FixtureWithDirectAddDetail(self.addDetail)
        self.assertEqual(fixture.caseAddDetail, self.addDetail)

    def test_can_construct_without_arguments(self):
        fixture = ap_fixtures.FixtureWithDirectAddDetail()
        self.assertEqual(fixture.caseAddDetail, fixture.addDetail)


class GSettingsAccessTests(TestCase):

    def test_incorrect_schema_raises_exception(self):
        self.assertThat(
            lambda: ap_fixtures._gsetting_get_setting('com.foo.', 'baz'),
            raises(ValueError)
        )

    def test_incorrect_key_raises_exception(self):
        self.assertThat(
            lambda: ap_fixtures._gsetting_get_setting(
                'org.gnome.system.locale',
                'baz'
            ),
            raises(ValueError)
        )

    def test_get_value_returns_expected_value(self):
        with patch.object(ap_fixtures, '_gsetting_get_setting') as get_setting:
            setting = Mock()
            setting.get_boolean.return_value = True
            get_setting.return_value = setting
            self.assertEqual(
                ap_fixtures.get_bool_gsettings_value('foo', 'bar'),
                True
            )


class OSKAlwaysEnabledTests(TestCase):

    @patch.object(ap_fixtures, '_gsetting_get_setting')
    def test_sets_stayhidden_to_False(self, gs):
        with patch.object(ap_fixtures, 'set_bool_gsettings_value') as set_gs:
            with ap_fixtures.OSKAlwaysEnabled():
                set_gs.assert_called_once_with(
                    'com.canonical.keyboard.maliit',
                    'stay-hidden',
                    False
                )

    def test_resets_value_to_original(self):
        with patch.object(ap_fixtures, 'set_bool_gsettings_value') as set_gs:
            with patch.object(ap_fixtures, 'get_bool_gsettings_value') as get_gs:  # NOQA
                get_gs.return_value = 'foo'
                with ap_fixtures.OSKAlwaysEnabled():
                    pass
                set_gs.assert_called_with(
                    'com.canonical.keyboard.maliit',
                    'stay-hidden',
                    'foo'
                )
