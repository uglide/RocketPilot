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
from unittest.mock import patch
from testtools import TestCase

from autopilot import _config as config


class TestConfigurationTests(TestCase):

    def test_can_set_test_config_string(self):
        token = self.getUniqueString()
        config.set_configuration_string(token)
        self.assertEqual(config._test_config_string, token)

    def test_can_create_config_dictionary_from_empty_string(self):
        d = config.ConfigDict('')
        self.assertEqual(0, len(d))

    def test_cannot_write_to_config_dict(self):
        def set_item():
            d['sdf'] = 123

        d = config.ConfigDict('')
        self.assertRaises(
            TypeError,
            set_item,
        )

    def test_simple_key_present(self):
        d = config.ConfigDict('foo')
        self.assertTrue('foo' in d)

    def test_simple_key_value(self):
        d = config.ConfigDict('foo')
        self.assertEqual(d['foo'], '1')

    def test_single_value_containing_equals_symbol(self):
        d = config.ConfigDict('foo=b=a')
        self.assertEqual(d['foo'], 'b=a')

    def test_multiple_simple_keys(self):
        d = config.ConfigDict('foo,bar')
        self.assertTrue('foo' in d)
        self.assertTrue('bar' in d)
        self.assertEqual(2, len(d))

    def test_ignores_empty_simple_keys_at_end(self):
        d = config.ConfigDict('foo,,')
        self.assertEqual(1, len(d))

    def test_ignores_empty_simple_keys_at_start(self):
        d = config.ConfigDict(',,foo')
        self.assertEqual(1, len(d))

    def test_ignores_empty_simple_keys_in_middle(self):
        d = config.ConfigDict('foo,,bar')
        self.assertEqual(2, len(d))

    def test_strips_leading_whitespace_for_simple_keys(self):
        d = config.ConfigDict(' foo, bar')
        self.assertEqual(set(d.keys()), {'foo', 'bar'})

    def test_complex_key_single(self):
        d = config.ConfigDict('foo=bar')
        self.assertEqual(1, len(d))
        self.assertEqual(d['foo'], 'bar')

    def test_complex_key_multiple(self):
        d = config.ConfigDict('foo=bar,baz=foo')
        self.assertEqual(d['foo'], 'bar')
        self.assertEqual(d['baz'], 'foo')

    def test_complex_keys_strip_leading_whitespace(self):
        d = config.ConfigDict(' foo=bar, bar=baz')
        self.assertEqual(set(d.keys()), {'foo', 'bar'})

    def test_raises_ValueError_on_blank_key(self):
        self.assertRaises(ValueError, lambda: config.ConfigDict('=,'))

    def test_raises_ValueError_on_space_key(self):
        self.assertRaises(ValueError, lambda: config.ConfigDict(' =,'))

    def test_raises_ValueError_on_invalid_string(self):
        self.assertRaises(ValueError, lambda: config.ConfigDict('f,='))

    def test_iter(self):
        k = config.ConfigDict('foo').keys()
        self.assertEqual({'foo'}, k)

    def test_get_test_configuration_uses_global_test_config_string(self):
        with patch.object(config, '_test_config_string', new='foo'):
            d = config.get_test_configuration()
            self.assertTrue('foo' in d)
