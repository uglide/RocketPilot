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

from testscenarios import TestWithScenarios
from testtools import TestCase
from testtools.matchers import raises

from autopilot.introspection import _xpathselect as xpathselect
from autopilot.exceptions import InvalidXPathQuery


class XPathSelectQueryTests(TestCase):

    def test_query_raises_TypeError_on_non_bytes_query(self):
        fn = lambda: xpathselect.Query(
            None,
            xpathselect.Query.Operation.CHILD,
            'asd'
        )
        self.assertThat(
            fn,
            raises(
                TypeError(
                    "'query' parameter must be bytes, not %s"
                    % type('').__name__
                )
            )
        )

    def test_can_create_root_query(self):
        q = xpathselect.Query.root(b'Foo')
        self.assertEqual(b"/Foo", q.server_query_bytes())

    def test_can_create_app_name_from_ascii_string(self):
        q = xpathselect.Query.root('Foo')
        self.assertEqual(b"/Foo", q.server_query_bytes())

    def test_creating_root_query_with_unicode_app_name_raises(self):
        self.assertThat(
            lambda: xpathselect.Query.root("\u2026"),
            raises(
                InvalidXPathQuery(
                    "Type name '%s', must be ASCII encodable" % ('\u2026')
                )
            )
        )

    def test_repr_with_path(self):
        path = b"/some/path"
        q = xpathselect.Query.root('some').select_child('path')
        self.assertEqual("Query(%r)" % path, repr(q))

    def test_repr_with_path_and_filters(self):
        expected = b"/some/path[bar=456,foo=123]"
        filters = dict(foo=123, bar=456)
        q = xpathselect.Query.root('some').select_child('path', filters)
        self.assertEqual("Query(%r)" % expected, repr(q))

    def test_select_child(self):
        q = xpathselect.Query.root("Foo").select_child("Bar")
        self.assertEqual(q.server_query_bytes(), b"/Foo/Bar")

    def test_select_child_with_filters(self):
        q = xpathselect.Query.root("Foo")\
            .select_child("Bar", dict(visible=True))
        self.assertEqual(q.server_query_bytes(), b"/Foo/Bar[visible=True]")

    def test_many_select_children(self):
        q = xpathselect.Query.root("Foo") \
            .select_child("Bar") \
            .select_child("Baz")

        self.assertEqual(b"/Foo/Bar/Baz", q.server_query_bytes())

    def test_many_select_children_with_filters(self):
        q = xpathselect.Query.root("Foo") \
            .select_child("Bar", dict(visible=True)) \
            .select_child("Baz", dict(id=123))

        self.assertEqual(
            b"/Foo/Bar[visible=True]/Baz[id=123]",
            q.server_query_bytes()
        )

    def test_select_descendant(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Bar")

        self.assertEqual(b"/Foo//Bar", q.server_query_bytes())

    def test_select_descendant_with_filters(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Bar", dict(name="Hello"))

        self.assertEqual(b'/Foo//Bar[name="Hello"]', q.server_query_bytes())

    def test_many_select_descendants(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Bar") \
            .select_descendant("Baz")

        self.assertEqual(b"/Foo//Bar//Baz", q.server_query_bytes())

    def test_many_select_descendants_with_filters(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Bar", dict(visible=True)) \
            .select_descendant("Baz", dict(id=123))

        self.assertEqual(
            b"/Foo//Bar[visible=True]//Baz[id=123]",
            q.server_query_bytes()
        )

    def test_full_server_side_filter(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Bar", dict(visible=True)) \
            .select_descendant("Baz", dict(id=123))
        self.assertFalse(q.needs_client_side_filtering())

    def test_client_side_filter(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Bar", dict(visible=True)) \
            .select_descendant("Baz", dict(name="\u2026"))
        self.assertTrue(q.needs_client_side_filtering())

    def test_client_side_filter_all_query_bytes(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Bar", dict(visible=True)) \
            .select_descendant("Baz", dict(name="\u2026"))
        self.assertEqual(
            b'/Foo//Bar[visible=True]//Baz',
            q.server_query_bytes()
        )

    def test_deriving_from_client_side_filtered_query_raises_ValueError(self):
        q = xpathselect.Query.root("Foo") \
            .select_descendant("Baz", dict(name="\u2026"))
        fn = lambda: q.select_child("Foo")
        self.assertThat(
            fn,
            raises(InvalidXPathQuery(
                "Cannot create a new query from a parent that requires "
                "client-side filter processing."
            ))
        )

    def test_init_raises_TypeError_on_invalid_operation_type(self):
        fn = lambda: xpathselect.Query(None, '/', b'sdf')
        self.assertThat(
            fn,
            raises(TypeError(
                "'operation' parameter must be bytes, not '%s'"
                % type('').__name__
            ))
        )

    def test_init_raises_ValueError_on_invalid_operation(self):
        fn = lambda: xpathselect.Query(None, b'foo', b'sdf')
        self.assertThat(
            fn,
            raises(InvalidXPathQuery("Invalid operation 'foo'."))
        )

    def test_init_raises_ValueError_on_invalid_descendant_search(self):
        fn = lambda: xpathselect.Query(None, b'//', b'*')
        self.assertThat(
            fn,
            raises(InvalidXPathQuery(
                "Must provide at least one server-side filter when searching "
                "for descendants and using a wildcard node."
            ))
        )

    def test_new_from_path_and_id_raises_TypeError_on_unicode_path(self):
        fn = lambda: xpathselect.Query.new_from_path_and_id('bad_path', 42)
        self.assertThat(
            fn,
            raises(TypeError(
                "'path' attribute must be bytes, not '%s'" % type('').__name__
            ))
        )

    def test_new_from_path_and_id_raises_ValueError_on_invalid_path(self):
        fn = lambda: xpathselect.Query.new_from_path_and_id(b'bad_path', 42)
        self.assertThat(
            fn,
            raises(InvalidXPathQuery("Invalid path 'bad_path'."))
        )

    def test_new_from_path_and_id_raises_ValueError_on_invalid_path2(self):
        fn = lambda: xpathselect.Query.new_from_path_and_id(b'/', 42)
        self.assertThat(
            fn,
            raises(InvalidXPathQuery("Invalid path '/'."))
        )

    def test_new_from_path_and_id_works_for_root_node(self):
        q = xpathselect.Query.new_from_path_and_id(b'/root', 42)
        self.assertEqual(b'/root', q.server_query_bytes())

    def test_new_from_path_and_id_works_for_small_tree(self):
        q = xpathselect.Query.new_from_path_and_id(b'/root/child', 42)
        self.assertEqual(b'/root/child[id=42]', q.server_query_bytes())

    def test_new_from_path_and_id_works_for_larger_tree(self):
        q = xpathselect.Query.new_from_path_and_id(b'/root/child/leaf', 42)
        self.assertEqual(b'/root/child/leaf[id=42]', q.server_query_bytes())

    def test_get_client_side_filters_returns_client_side_filters(self):
        q = xpathselect.Query.root('app') \
            .select_child('leaf', dict(name='\u2026'))
        self.assertEqual(dict(name='\u2026'), q.get_client_side_filters())

    def test_get_parent_on_root_node_returns_the_same_query(self):
        q = xpathselect.Query.root('app')
        q2 = q.select_parent()
        self.assertEqual(b'/app/..', q2.server_query_bytes())

    def test_get_parent_on_node_returns_parent_query(self):
        q = xpathselect.Query.new_from_path_and_id(b'/root/child', 42)
        q2 = q.select_parent()
        self.assertEqual(b'/root/child[id=42]/..', q2.server_query_bytes())

    def test_init_raises_ValueError_when_passing_filters_and_parent(self):
        fn = lambda: xpathselect.Query(None, b'/', b'..', dict(foo=123))
        self.assertThat(
            fn,
            raises(InvalidXPathQuery(
                "Cannot specify filters while selecting a parent"
            ))
        )

    def test_init_raises_ValueError_when_passing_bad_op_and_parent(self):
        fn = lambda: xpathselect.Query(None, b'//', b'..')
        self.assertThat(
            fn,
            raises(InvalidXPathQuery(
                "Operation must be CHILD while selecting a parent"
            ))
        )

    def test_select_tree_root_returns_correct_query(self):
        q = xpathselect.Query.pseudo_tree_root()
        self.assertEqual(b'/', q.server_query_bytes())

    def test_cannot_select_child_on_pseudo_tree_root(self):
        fn = lambda: xpathselect.Query.pseudo_tree_root().select_child('foo')
        self.assertThat(
            fn,
            raises(InvalidXPathQuery(
                "Cannot select children from a pseudo-tree-root query."
            ))
        )

    def test_whole_tree_search_returns_correct_query(self):
        q = xpathselect.Query.whole_tree_search('Foo')
        self.assertEqual(b'//Foo', q.server_query_bytes())

    def test_whole_tree_search_with_filters_returns_correct_query(self):
        q = xpathselect.Query.whole_tree_search('Foo', dict(foo='bar'))
        self.assertEqual(b'//Foo[foo="bar"]', q.server_query_bytes())


class ParameterFilterStringScenariodTests(TestWithScenarios, TestCase):

    scenarios = [
        ('bool true', dict(k='visible', v=True, r=b"visible=True")),
        ('bool false', dict(k='visible', v=False, r=b"visible=False")),
        ('int +ve', dict(k='size', v=123, r=b"size=123")),
        ('int -ve', dict(k='prio', v=-12, r=b"prio=-12")),
        ('simple string', dict(k='Name', v="btn1", r=b"Name=\"btn1\"")),
        ('simple bytes', dict(k='Name', v=b"btn1", r=b"Name=\"btn1\"")),
        ('string space', dict(k='Name', v="a b  c ", r=b"Name=\"a b  c \"")),
        ('bytes space', dict(k='Name', v=b"a b  c ", r=b"Name=\"a b  c \"")),
        ('string escapes', dict(
            k='a',
            v="\a\b\f\n\r\t\v\\",
            r=br'a="\x07\x08\x0c\n\r\t\x0b\\"')),
        ('byte escapes', dict(
            k='a',
            v=b"\a\b\f\n\r\t\v\\",
            r=br'a="\x07\x08\x0c\n\r\t\x0b\\"')),
        ('escape quotes (str)', dict(k='b', v="'", r=b'b="\\' + b"'" + b'"')),
        (
            'escape quotes (bytes)',
            dict(k='b', v=b"'", r=b'b="\\' + b"'" + b'"')
        ),
    ]

    def test_query_string(self):
        s = xpathselect._get_filter_string_for_key_value_pair(self.k, self.v)
        self.assertEqual(s, self.r)


class ParameterFilterStringTests(TestWithScenarios, TestCase):

    def test_raises_ValueError_on_unknown_type(self):
        fn = lambda: xpathselect._get_filter_string_for_key_value_pair(
            'k',
            object()
        )
        self.assertThat(
            fn,
            raises(
                ValueError("Unsupported value type: object")
            )
        )


class ServerSideParamMatchingTests(TestWithScenarios, TestCase):

    """Tests for the server side matching decision function."""

    scenarios = [
        ('should work', dict(key='keyname', value='value', result=True)),
        ('invalid key', dict(key='k  e', value='value', result=False)),
        ('string value', dict(key='key', value='v  e', result=True)),
        ('string value2', dict(key='key', value='v?e', result=True)),
        ('string value3', dict(key='key', value='1/2."!@#*&^%', result=True)),
        ('bool value', dict(key='key', value=False, result=True)),
        ('int value', dict(key='key', value=123, result=True)),
        ('int value2', dict(key='key', value=-123, result=True)),
        ('float value', dict(key='key', value=1.0, result=False)),
        ('dict value', dict(key='key', value={}, result=False)),
        ('obj value', dict(key='key', value=TestCase, result=False)),
        ('int overflow 1', dict(key='key', value=-2147483648, result=True)),
        ('int overflow 2', dict(key='key', value=-2147483649, result=False)),
        ('int overflow 3', dict(key='key', value=2147483647, result=True)),
        ('int overflow 4', dict(key='key', value=2147483648, result=False)),
        ('unicode string', dict(key='key', value='H\u2026i', result=False)),
    ]

    def test_valid_server_side_param(self):
        self.assertEqual(
            xpathselect._is_valid_server_side_filter_param(
                self.key,
                self.value
            ),
            self.result
        )


class GetClassnameFromPathTests(TestCase):

    def test_single_element(self):
        self.assertEqual("Foo", xpathselect.get_classname_from_path("Foo"))

    def test_single_element_with_path(self):
        self.assertEqual("Foo", xpathselect.get_classname_from_path("/Foo"))

    def test_multiple_elements(self):
        self.assertEqual(
            "Baz",
            xpathselect.get_classname_from_path("/Foo/Bar/Baz")
        )


class GetPathRootTests(TestCase):

    def test_get_root_path_on_string_path(self):
        self.assertEqual("Foo", xpathselect.get_path_root("/Foo/Bar/Baz"))

    def test_get_root_path_on_bytes_literal_path(self):
        self.assertEqual(b"Foo", xpathselect.get_path_root(b"/Foo/Bar/Baz"))

    def test_get_root_path_on_garbage_path_raises(self):
        self.assertRaises(IndexError, xpathselect.get_path_root, "asdfgh")
