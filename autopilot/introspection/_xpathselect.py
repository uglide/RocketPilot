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

"""Classes and functions that encode knowledge of the xpathselect query
language.

This module is internal, and should not be used directly.

The main class is 'Query', which represents an xpathselect query. Query is a
read-only object - once it has been constructed, it cannot be changed. This is
partially to ease testing, but also to provide guarantees in the proxy object
classes.

To create a query, you must either have a reference to an existing query, or
you must know the name of the root note. To create a query from an existing
query::

    >>> new_query = existing_query.select_child("NodeName")

To create a query given the root node name::

    >>> new_root_query = Query.root("AppName")

Since the XPathSelect language is not perfect, and since we'd like to support
a rich set of selection criteria, not all queries can be executed totally on
the server side. Query instnaces are intelligent enough to know when they must
invoke some client-side processing - in this case the
'needs_client_side_filtering' method will return True.

Queries are executed in the autopilot.introspection.backends module.

"""
from pathlib import Path
import re

from autopilot.utilities import compatible_repr
from autopilot.exceptions import InvalidXPathQuery


class Query(object):

    """Encapsulate an XPathSelect query."""

    class Operation(object):
        ROOT = b'/'
        CHILD = b'/'
        DESCENDANT = b'//'

        ALL = (ROOT, CHILD, DESCENDANT)

    PARENT = b'..'
    WILDCARD = b'*'

    def __init__(self, parent, operation, query, filters={}):
        """Create a new query object.

        You shouldn't need to call this directly.

        :param parent: The parent query object. Pass in None to make the root
            query object.
        :param operation: The operation object to perform on the result from
            the parent node.
        :param query: The query expression for this node.
        :param filters: A dictionary of filters to apply.

        :raises TypeError: If the 'query' parameter is not 'bytes'.
        :raises TypeError: If the operation parameter is not 'bytes'.
        :raises InvalidXPathQuery: If parent is specified, and the parent
            query needs client side filter processing. Only the last query in
            the query chain can have filters that need to be executed on the
            client-side.
        :raises InvalidXPathQuery: If operation is not one of the members of
            the Query.Operation class.
        :raises InvalidXPathQuery: If the query is set to Query.WILDCARD and
            'filters' does not contain any server-side filters, and operation
            is set to Query.Operation.DESCENDANT.
        :raises InvalidXPathQuery: When 'filters' are specified while trying
            to select a parent node in the introspection tree.

        """
        if not isinstance(query, bytes):
            raise TypeError(
                "'query' parameter must be bytes, not %s"
                % type(query).__name__
            )
        if not isinstance(operation, bytes):
            raise TypeError(
                "'operation' parameter must be bytes, not '%s'"
                % type(operation).__name__)
        if (
            parent
            and parent.needs_client_side_filtering()
        ):
            raise InvalidXPathQuery(
                "Cannot create a new query from a parent that requires "
                "client-side filter processing."
            )
        if query == Query.PARENT and filters:
            raise InvalidXPathQuery(
                "Cannot specify filters while selecting a parent"
            )
        if query == Query.PARENT and operation != Query.Operation.CHILD:
            raise InvalidXPathQuery(
                "Operation must be CHILD while selecting a parent"
            )
        if operation not in Query.Operation.ALL:
            raise InvalidXPathQuery(
                "Invalid operation '%s'." % operation.decode()
            )
        if parent and parent.server_query_bytes() == b'/':
            raise InvalidXPathQuery(
                "Cannot select children from a pseudo-tree-root query."
            )
        self._parent = parent
        self._operation = operation
        self._query = query
        self._server_filters = {
            k: v for k, v in filters.items()
            if _is_valid_server_side_filter_param(k, v)
        }
        self._client_filters = {
            k: v for k, v in filters.items() if k not in self._server_filters
        }
        if (
            operation == Query.Operation.DESCENDANT
            and query == Query.WILDCARD
            and not self._server_filters
        ):
            raise InvalidXPathQuery(
                "Must provide at least one server-side filter when searching "
                "for descendants and using a wildcard node."
            )

    @staticmethod
    def root(app_name):
        """Create a root query object.

        :param app_name: The name of the root node in the introspection tree.
            This is also typically the application name.

        :returns: A new Query instance, representing the root of the tree.
        """
        app_name = _try_encode_type_name(app_name)
        return Query(
            None,
            Query.Operation.ROOT,
            app_name
        )

    @staticmethod
    def new_from_path_and_id(path, id):
        """Create a new Query object from a path and id.

        :param path: The full path to the node you want to construct the query
            for.
        :param id: The object id of the node you want to construct the query
            for.

        :raises TypeError: If the path attribute is not 'bytes'.
        :raises ValueError: If the path does not start with b'/'

        """
        if not isinstance(path, bytes):
            raise TypeError(
                "'path' attribute must be bytes, not '%s'"
                % type(path).__name__
            )
        nodes = list(filter(None, path.split(b'/')))
        if not path.startswith(b'/') or not nodes:
            raise InvalidXPathQuery("Invalid path '%s'." % path.decode())

        query = None
        for i, n in enumerate(nodes):
            if query is None:
                query = Query.root(n)
            else:
                if i == len(nodes) - 1:
                    query = query.select_child(n, dict(id=id))
                else:
                    query = query.select_child(n)
        return query

    @staticmethod
    def pseudo_tree_root():
        """Return a Query instance that will select the root of the tree.

        Unlike the 'root' method, this method does not need to know the name of
        the tree root. However, the query returned by this method cannot be
        used as the parent for any other query. In other words, calling any
        of the 'select_child', 'select_parent', 'select_descendant' method will
        raise a InvalidXPathQuery error.

        If at all possible, it's better to use the 'root' method instead of
        this one. The queries returned by this method are useful for getting
        the root proxy object, and then discarding the query.

        """
        return Query(None, Query.Operation.CHILD, b'')

    @staticmethod
    def whole_tree_search(child_name, filters={}):
        """Return a query capable of searching the entire introspection tree.

        .. warning::
            This method returns a query that can be extremely slow on larger
            applications. The execution time can easily extend beyond the dbus
            timeout period, which can result in tests that fail on some
            machines but not others. Test authors are strongly encouraged to
            use the 'Query.root' method and absolute queries instead.

        """
        child_name = _try_encode_type_name(child_name)
        return Query(None, Query.Operation.DESCENDANT, child_name, filters)

    def needs_client_side_filtering(self):
        """Return true if this query requires some filtering on the client-side
        """
        return self._client_filters or (
            self._parent.needs_client_side_filtering()
            if self._parent else False
        )

    def get_client_side_filters(self):
        """Return a dictionary of filters that must be processed on the client
        rather than the server.
        """
        return self._client_filters

    def server_query_bytes(self):
        """Get a bytestring representing the entire query.

        This method returns a bytestring suitable for sending to the server.
        """
        parent_query = self._parent.server_query_bytes() \
            if self._parent is not None else b''

        return parent_query + \
            self._operation + \
            self._query + \
            self._get_server_filter_bytes()

    def _get_server_filter_bytes(self):
        if self._server_filters:
            keys = sorted(self._server_filters.keys())
            return b'[' + \
                b",".join(
                    [
                        _get_filter_string_for_key_value_pair(
                            k,
                            self._server_filters[k]
                        ) for k in keys
                        if _is_valid_server_side_filter_param(
                            k,
                            self._server_filters[k]
                        )
                    ]
                ) + \
                b']'
        return b''

    @compatible_repr
    def __repr__(self):
        return "Query(%r)" % self.server_query_bytes()

    def select_child(self, child_name, filters={}):
        """Return a query matching an immediate child.

        Keyword arguments may be used to restrict which nodes to match.

        :param child_name: The name of the child node to match.

        :returns: A Query instance that will match the child.

        """
        child_name = _try_encode_type_name(child_name)
        return Query(
            self,
            Query.Operation.CHILD,
            child_name,
            filters
        )

    def select_descendant(self, ancestor_name, filters={}):
        """Return a query matching an ancestor of the current node.

        :param ancestor_name: The name of the ancestor node to match.

        :returns: A Query instance that will match the ancestor.

        """
        ancestor_name = _try_encode_type_name(ancestor_name)
        return Query(
            self,
            Query.Operation.DESCENDANT,
            ancestor_name,
            filters
        )

    def select_parent(self):
        """Return a query matching the parent node of the current node.

        Calling this on the root node will return a query that looks like it
        ought to select the parent of the root (something like: b'/root/..').
        This is however perfectly safe, as the server-side will just return
        the root node in this case.

        :returns: A Query instance that will match the parent node.

        """
        return Query(self, Query.Operation.CHILD, Query.PARENT)


def _try_encode_type_name(name):
    if isinstance(name, str):
        try:
            name = name.encode('ascii')
        except UnicodeEncodeError:
            raise InvalidXPathQuery(
                "Type name '%s', must be ASCII encodable" % (name)
            )
    return name


def _is_valid_server_side_filter_param(key, value):
    """Return True if the key and value parameters are valid for server-side
    processing.

    """
    key_is_valid = re.match(
        r'^[a-zA-Z0-9_\-]+( [a-zA-Z0-9_\-])*$',
        key
    ) is not None

    if type(value) == int:
        return key_is_valid and (-2**31 <= value <= 2**31 - 1)

    elif type(value) == bool:
        return key_is_valid

    elif type(value) == bytes:
        return key_is_valid

    elif type(value) == str:
        try:
            value.encode('ascii')
            return key_is_valid
        except UnicodeEncodeError:
            pass
    return False


def _get_filter_string_for_key_value_pair(key, value):
    """Return bytes representing the filter query for this key/value pair.

    The value must be suitable for server-side filtering. Raises ValueError if
    this is not the case.

    """
    if isinstance(value, str):
        escaped_value = value.encode("unicode_escape")\
            .decode('ASCII')\
            .replace("'", "\\'")
        return '{}="{}"'.format(key, escaped_value).encode('utf-8')
    elif isinstance(value, bytes):
        escaped_value = value.decode('utf-8')\
            .encode("unicode_escape")\
            .decode('ASCII')\
            .replace("'", "\\'")
        return '{}="{}"'.format(key, escaped_value).encode('utf-8')
    elif isinstance(value, int) or isinstance(value, bool):
        return "{}={}".format(key, repr(value)).encode('utf-8')
    else:
        raise ValueError(
            "Unsupported value type: {}".format(type(value).__name__)
        )


def _get_node(object_path, index):
    # TODO: Find places where paths are strings, and convert them to
    # bytestrings. Figure out what to do with the whole string vs. bytestring
    # mess.
    try:
        return Path(object_path).parts[index]
    except TypeError:
        if not isinstance(object_path, bytes):
            raise TypeError(
                'Object path needs to be a string literal or a bytes literal'
            )
        return object_path.split(b"/")[index]


def get_classname_from_path(object_path):
    """Given an object path, return the class name component."""
    return _get_node(object_path, -1)


def get_path_root(object_path):
    """Return the name of the root node of specified path."""
    return _get_node(object_path, 1)
