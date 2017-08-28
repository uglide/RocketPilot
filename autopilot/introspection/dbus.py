# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2013 Canonical
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


"""This module contains the code to retrieve state via DBus calls.

Under normal circumstances, the only thing you should need to use from this
module is the DBusIntrospectableObject class.

"""

import logging
import sys
from contextlib import contextmanager

from autopilot.exceptions import StateNotFoundError
from autopilot.introspection import _xpathselect as xpathselect
from autopilot.introspection._object_registry import (
    DBusIntrospectionObjectBase,
)
from autopilot.introspection.types import create_value_instance
from autopilot.introspection.utilities import (
    translate_state_keys,
    sort_by_keys,
)
from autopilot.utilities import sleep

_logger = logging.getLogger(__name__)


class DBusIntrospectionObject(DBusIntrospectionObjectBase):
    """A class that supports transparent data retrieval from the application
    under test.

    This class is the base class for all objects retrieved from the application
    under test. It handles transparently refreshing attribute values when
    needed, and contains many methods to select child objects in the
    introspection tree.

    This class must be used as a base class for any custom proxy classes.

    .. seealso::
        Tutorial Section :ref:`custom_proxy_classes`
            Information on how to write custom proxy classes.

    """

    def __init__(self, state_dict, path, backend):
        """Construct a new proxy instance.

        :param state_dict: A dictionary of state data for the proxy object.
        :param path: A bytestring describing the path to the object within the
            introspection tree.
        :param backend: The data source backend this proxy should use then
            retrieving additional state data.

        The state dictionary must contain an 'id' element, as this is used to
        uniquely identify this object.

        """
        self.__state = {}
        self.__refresh_on_attribute = True
        self._set_properties(state_dict)
        self._path = path
        self._backend = backend
        self._query = xpathselect.Query.new_from_path_and_id(
            self._path,
            self.id
        )

    def _execute_query(self, query):
        """Execute query object 'query' and return the result."""
        return self._backend.execute_query_get_proxy_instances(
            query,
            getattr(self, '_id', None),
        )

    def _set_properties(self, state_dict):
        """Creates and set attributes of *self* based on contents of
        *state_dict*.

        .. note:: Translates '-' to '_', so a key of 'icon-type' for example
         becomes 'icon_type'.

        """
        # don't store id in state dictionary - make it a proper instance
        # attribute. If id is not present, raise a ValueError.
        try:
            self.id = int(state_dict['id'][1])
        except KeyError:
            raise ValueError(
                "State dictionary does not contain required 'id' key."
            )

        self.__state = {}
        for key, value in translate_state_keys(state_dict).items():
            if key == 'id':
                continue
            try:
                self.__state[key] = create_value_instance(value, self, key)
            except ValueError as e:
                _logger.warning(
                    "While constructing attribute '%s.%s': %s",
                    self.__class__.__name__,
                    key,
                    str(e)
                )

    def get_children_by_type(self, desired_type, **kwargs):
        """Get a list of children of the specified type.

        Keyword arguments can be used to restrict returned instances. For
        example::

            get_children_by_type('Launcher', monitor=1)

        will return only Launcher instances that have an attribute 'monitor'
        that is equal to 1. The type can also be specified as a string, which
        is useful if there is no emulator class specified::

            get_children_by_type('Launcher', monitor=1)

        Note however that if you pass a string, and there is an emulator class
        defined, autopilot will not use it.

        :param desired_type: Either a string naming the type you want, or a
            class of the type you want (the latter is used when defining
            custom emulators)

        .. seealso::
            Tutorial Section :ref:`custom_proxy_classes`

        """
        new_query = self._query.select_child(
            get_type_name(desired_type),
            kwargs
        )

        return self._execute_query(new_query)

    def get_properties(self):
        """Returns a dictionary of all the properties on this class.

        This can be useful when you want to log all the properties exported
        from your application for a particular object. Every property in the
        returned dictionary can be accessed as attributes of the object as
        well.

        """
        # Since we're grabbing __state directly there's no implied state
        # refresh, so do it manually:
        self.refresh_state()
        props = self.__state.copy()
        props['id'] = self.id
        return props

    def get_children(self):
        """Returns a list of all child objects.

        This returns a list of all children. To return only children of a
        specific type, use :meth:`get_children_by_type`. To get objects
        further down the introspection tree (i.e.- nodes that may not
        necessarily be immeadiate children), use :meth:`select_single` and
        :meth:`select_many`.

        """
        # Thomi: 2014-03-20: There used to be a call to 'self.refresh_state()'
        # here. That's not needed, since the only thing we use is the proxy
        # path, which isn't affected by the current state.
        new_query = self._query.select_child(xpathselect.Query.WILDCARD)
        return self._execute_query(new_query)

    def _get_parent(self, base_object=None, level=1):
        """Returns the parent of this object.

        Note: *level* is in ascending order, i.e. its value as 1 will return
            the immediate parent of this object or (optionally) *base_object*,
            if provided.
        """
        obj = base_object or self
        new_query = obj._query
        for i in range(level):
            new_query = new_query.select_parent()
        return obj._execute_query(new_query)[0]

    def _get_parent_nodes(self):
        parent_nodes = self.get_path().split('/')
        parent_nodes.pop()
        # return a list without any NoneType elements. Only needed for the
        # case when we try to get parent of a root object
        return [node for node in parent_nodes if node]

    def get_parent(self, type_name='', **kwargs):
        """Returns the parent of this object.

        One may also use this method to get a specific parent node from the
        introspection tree, with type equal to *type_name* or matching the
        keyword filters present in *kwargs*.
        Note: The priority order is closest parent.

        If no filters are provided and this object has no parent (i.e.- it is
        the root of the introspection tree). Then it returns itself.

        :param type_name: Either a string naming the type you want, or a class
            of the appropriate type (the latter case is for overridden emulator
            classes).

        :raises StateNotFoundError: if the requested object was not found.
        """
        if not type_name and not kwargs:
            return self._get_parent()

        parent_nodes = self._get_parent_nodes()
        type_name_str = get_type_name(type_name)
        if type_name:
            # Raise if type_name is not a parent.
            if type_name_str not in parent_nodes:
                raise StateNotFoundError(type_name_str, **kwargs)
            for index, node in reversed(list(enumerate(parent_nodes))):
                if node == type_name_str:
                    parent_level = len(parent_nodes) - index
                    parent = self._get_parent(level=parent_level)
                    if _validate_object_properties(parent, **kwargs):
                        return parent
        else:
            # Keep a reference of the parent object to improve performance.
            parent = self
            for i in range(len(parent_nodes)):
                parent = self._get_parent(base_object=parent)
                if _validate_object_properties(parent, **kwargs):
                    return parent
        raise StateNotFoundError(type_name_str, **kwargs)

    def _select(self, type_name_str, **kwargs):
        """Base method to execute search query on the DBus."""
        new_query = self._query.select_descendant(type_name_str, kwargs)
        _logger.debug(
            "Selecting object(s) of %s with attributes: %r",
            'any type' if type_name_str == '*' else 'type ' + type_name_str,
            kwargs
        )
        return self._execute_query(new_query)

    def _select_single(self, type_name, **kwargs):
        """
        Ensures a single search result is produced from the query
        and returns it.
        """
        type_name_str = get_type_name(type_name)
        instances = self._select(type_name_str, **kwargs)
        if not instances:
            raise StateNotFoundError(type_name_str, **kwargs)
        if len(instances) > 1:
            raise ValueError("More than one item was returned for query")
        return instances[0]

    def select_single(self, type_name='*', **kwargs):
        """Get a single node from the introspection tree, with type equal to
        *type_name* and (optionally) matching the keyword filters present in
        *kwargs*.

        You must specify either *type_name*, keyword filters or both.

        This method searches recursively from the instance this method is
        called on. Calling :meth:`select_single` on the application (root)
        proxy object will search the entire tree. Calling
        :meth:`select_single` on an object in the tree will only search it's
        descendants.

        Example usage::

            app.select_single('QPushButton', objectName='clickme')
            # returns a QPushButton whose 'objectName' property is 'clickme'.

        If nothing is returned from the query, this method raises
        StateNotFoundError.

        :param type_name: Either a string naming the type you want, or a class
            of the appropriate type (the latter case is for overridden emulator
            classes).

        :raises ValueError: if the query returns more than one item. *If
            you want more than one item, use select_many instead*.

        :raises ValueError: if neither *type_name* or keyword filters are
            provided.

        :raises StateNotFoundError: if the requested object was not found.

        .. seealso::
            Tutorial Section :ref:`custom_proxy_classes`

        """
        return self._select_single(type_name, **kwargs)

    def wait_select_single(self, type_name='*', ap_query_timeout=10, **kwargs):
        """Get a proxy object matching some search criteria, retrying if no
        object is found until a timeout is reached.

        This method is identical to the :meth:`select_single` method, except
        that this method will poll the application under test for 10 seconds
        in the event that the search criteria does not match anything.

        This method will return single proxy object from the introspection
        tree, with type equal to *type_name* and (optionally) matching the
        keyword filters present in *kwargs*.

        You must specify either *type_name*, keyword filters or both.

        This method searches recursively from the proxy object this method is
        called on. Calling :meth:`select_single` on the application (root)
        proxy object will search the entire tree. Calling
        :meth:`select_single` on an object in the tree will only search it's
        descendants.

        Example usage::

            app.wait_select_single('QPushButton', objectName='clickme')
            # returns a QPushButton whose 'objectName' property is 'clickme'.
            # will poll the application until such an object exists, or will
            # raise StateNotFoundError after 10 seconds.

        If nothing is returned from the query, this method raises
        StateNotFoundError after *ap_query_timeout* seconds.

        :param type_name: Either a string naming the type you want, or a class
            of the appropriate type (the latter case is for overridden emulator
            classes).

        :param ap_query_timeout: Time in seconds to wait for search criteria
            to match.

        :raises ValueError: if the query returns more than one item. *If
            you want more than one item, use select_many instead*.

        :raises ValueError: if neither *type_name* or keyword filters are
            provided.

        :raises StateNotFoundError: if the requested object was not found.

        .. seealso::
            Tutorial Section :ref:`custom_proxy_classes`

        """
        if ap_query_timeout <= 0:
            return self._select_single(type_name, **kwargs)

        for i in range(ap_query_timeout):
            try:
                return self._select_single(type_name, **kwargs)
            except StateNotFoundError:
                sleep(1)
        raise StateNotFoundError(type_name, **kwargs)

    def _select_many(self, type_name, **kwargs):
        """Executes a query, with no restraints on the number of results."""
        type_name_str = get_type_name(type_name)
        return self._select(type_name_str, **kwargs)

    def select_many(self, type_name='*', ap_result_sort_keys=None, **kwargs):
        """Get a list of nodes from the introspection tree, with type equal to
        *type_name* and (optionally) matching the keyword filters present in
        *kwargs*.

        You must specify either *type_name*, keyword filters or both.

        This method searches recursively from the instance this method is
        called on. Calling :meth:`select_many` on the application (root) proxy
        object will search the entire tree. Calling :meth:`select_many` on an
        object in the tree will only search it's descendants.

        Example Usage::

            app.select_many('QPushButton', enabled=True)
            # returns a list of QPushButtons that are enabled.

        As mentioned above, this method searches the object tree recursively::

            file_menu = app.select_one('QMenu', title='File')
            file_menu.select_many('QAction')
            # returns a list of QAction objects who appear below file_menu in
            # the object tree.

        .. warning::
            The order in which objects are returned is not guaranteed. It is
            bad practise to write tests that depend on the order in which
            this method returns objects. (see :ref:`object_ordering` for more
            information).

        If you want to ensure a certain count of results retrieved from this
        method, use :meth:`wait_select_many` or if you only want to get one
        item, use :meth:`select_single` instead.

        :param type_name: Either a string naming the type you want, or a class
            of the appropriate type (the latter case is for overridden emulator
            classes).

        :param ap_result_sort_keys: list of object properties to sort the
            query result with (sort key priority starts with element 0 as
            highest priority and then descends down the list).

        :raises ValueError: if neither *type_name* or keyword filters are
            provided.

        .. seealso::
            Tutorial Section :ref:`custom_proxy_classes`

        """
        instances = self._select_many(type_name, **kwargs)
        return sort_by_keys(instances, ap_result_sort_keys)

    def wait_select_many(
            self,
            type_name='*',
            ap_query_timeout=10,
            ap_result_count=1,
            ap_result_sort_keys=None,
            **kwargs
    ):
        """Get a list of nodes from the introspection tree, with type equal to
        *type_name* and (optionally) matching the keyword filters present in
        *kwargs*.

        This method is identical to the :meth:`select_many` method, except
        that this method will poll the application under test for
        *ap_query_timeout* seconds in the event that the search result count
        is not greater than or equal to *ap_result_count*.

        You must specify either *type_name*, keyword filters or both.

        This method searches recursively from the instance this method is
        called on. Calling :meth:`wait_select_many` on the application (root)
        proxy object will search the entire tree. Calling
        :meth:`wait_select_many` on an object in the tree will only search
        it's descendants.

        Example Usage::

            app.wait_select_many(
                'QPushButton',
                ap_query_timeout=5,
                ap_result_count=2,
                enabled=True
            )
            # returns at least 2 QPushButtons that are enabled, within
            # 5 seconds.

        .. warning::
            The order in which objects are returned is not guaranteed. It is
            bad practise to write tests that depend on the order in which
            this method returns objects. (see :ref:`object_ordering` for more
            information).

        :param type_name: Either a string naming the type you want, or a class
            of the appropriate type (the latter case is for overridden emulator
            classes).

        :param ap_query_timeout: Time in seconds to wait for search criteria
            to match.

        :param ap_result_count: Minimum number of results to return.

        :param ap_result_sort_keys: list of object properties to sort the
            query result with (sort key priority starts with element 0 as
            highest priority and then descends down the list).

        :raises ValueError: if neither *type_name* or keyword filters are
            provided. Also raises, if search result count does not match the
            number specified by *ap_result_count* within *ap_query_timeout*
            seconds.

        .. seealso::
            Tutorial Section :ref:`custom_proxy_classes`

        """
        exception_message = 'Failed to find the requested number of elements.'

        if ap_query_timeout <= 0:
            instances = self._select_many(type_name, **kwargs)
            if len(instances) < ap_result_count:
                raise ValueError(exception_message)
            return sort_by_keys(instances, ap_result_sort_keys)

        for i in range(ap_query_timeout):
            instances = self._select_many(type_name, **kwargs)
            if len(instances) >= ap_result_count:
                return sort_by_keys(instances, ap_result_sort_keys)
            sleep(1)
        raise ValueError(exception_message)

    def refresh_state(self):
        """Refreshes the object's state.

        You should probably never have to call this directly. Autopilot
        automatically retrieves new state every time this object's attributes
        are read.

        :raises StateNotFound: if the object in the application under test
            has been destroyed.

        """
        _, new_state = self._get_new_state()
        self._set_properties(new_state)

    def get_all_instances(self):
        """Get all instances of this class that exist within the Application
        state tree.

        For example, to get all the LauncherIcon instances::

            icons = LauncherIcon.get_all_instances()

        .. warning::
            Using this method is slow - it requires a complete scan of the
            introspection tree. You should only use this when you're not sure
            where the objects you are looking for are located. Depending on
            the application you are testing, you may get duplicate results
            using this method.

        :return: List (possibly empty) of class instances.

        """
        cls_name = type(self).__name__
        return self._execute_query(
            xpathselect.Query.whole_tree_search(cls_name)
        )

    def get_root_instance(self):
        """Get the object at the root of this tree.

        This will return an object that represents the root of the
        introspection tree.

        """
        query = xpathselect.Query.pseudo_tree_root()
        return self._execute_query(query)[0]

    def __getattr__(self, name):
        # avoid recursion if for some reason we have no state set (should never
        # happen).
        if name == '__state':
            raise AttributeError()

        if name in self.__state:
            if self.__refresh_on_attribute:
                self.refresh_state()
            return self.__state[name]
        # attribute not found.
        raise AttributeError(
            "Class '%s' has no attribute '%s'." %
            (self.__class__.__name__, name))

    def _get_new_state(self):
        """Retrieve a new state dictionary for this class instance.

        You should probably never need to call this directly.

        .. note:: The state keys in the returned dictionary are not translated.

        """
        try:
            return self._backend.execute_query_get_data(self._query)[0]
        except IndexError:
            raise StateNotFoundError(self.__class__.__name__, id=self.id)

    def wait_until_destroyed(self, timeout=10):
        """Block until this object is destroyed in the application.

        Block until the object this instance is a proxy for has been destroyed
        in the applicaiton under test. This is commonly used to wait until a
        UI component has been destroyed.

        :param timeout: The number of seconds to wait for the object to be
            destroyed. If not specified, defaults to 10 seconds.
        :raises RuntimeError: if the method timed out.

        """
        for i in range(timeout):
            try:
                self._get_new_state()
                sleep(1)
            except StateNotFoundError:
                return
        else:
            raise RuntimeError(
                "Object was not destroyed after %d seconds" % timeout
            )

    def is_moving(self, gap_interval=0.1):
        """Check if the element is moving.

        :param gap_interval: Time in seconds to wait before
            re-inquiring the object co-ordinates to be able
            to evaluate if, the element is moving.

        :return: True, if the element is moving, otherwise False.
        """
        return _MockableDbusObject(self).is_moving(gap_interval)

    def wait_until_not_moving(
            self,
            retry_attempts_count=20,
            retry_interval=0.5,
    ):
        """Block until this object is not moving.

        Block until both x and y of the object stop changing. This is
        normally useful for cases, where there is a need to ensure an
        object is static before interacting with it.

        :param retry_attempts_count: number of attempts to check
            if the object is moving.

        :param retry_interval: time in fractional seconds to be
            slept, between each attempt to check if the object
            moving.

        :raises RuntimeError: if DBus node is still moving after
            number of retries specified in *retry_attempts_count*.
        """
        # In case *retry_attempts_count* is something smaller than
        # 1, sanitize it.
        if retry_attempts_count < 1:
            retry_attempts_count = 1
        for i in range(retry_attempts_count):
            if not self.is_moving(retry_interval):
                return
        raise RuntimeError(
            'Object was still moving after {} second(s)'.format(
                retry_attempts_count * retry_interval
            )
        )

    def print_tree(self, output=None, maxdepth=None, _curdepth=0):
        """Print properties of the object and its children to a stream.

        When writing new tests, this can be called when it is too difficult to
        find the widget or property that you are interested in in "vis".

        .. warning:: Do not use this in production tests, this is expensive and
            not at all appropriate for actual testing. Only call this
            temporarily and replace with proper select_single/select_many
            calls.

        :param output: A file object or path name where the output will be
            written to. If not given, write to stdout.

        :param maxdepth: If given, limit the maximum recursion level to that
            number, i. e. only print children which have at most maxdepth-1
            intermediate parents.

        """
        if maxdepth is not None and _curdepth > maxdepth:
            return

        indent = "  " * _curdepth
        if output is None:
            output = sys.stdout
        elif isinstance(output, str):
            output = open(output, 'w')

        # print path
        if _curdepth > 0:
            output.write("\n")
        output.write("%s== %s ==\n" % (indent, self._path.decode('utf-8')))
        # Thomi 2014-03-20: For all levels other than the top level, we can
        # avoid an entire dbus round trip if we grab the underlying property
        # dictionary directly. We can do this since the print_tree function
        # that called us will have retrieved us via a call to get_children(),
        # which gets the latest state anyway.
        if _curdepth > 0:
            properties = self.__state.copy()
        else:
            properties = self.get_properties()
        # print properties
        try:
            for key in sorted(properties.keys()):
                output.write("%s%s: %r\n" % (indent, key, properties[key]))
            # print children
            if maxdepth is None or _curdepth < maxdepth:
                for c in self.get_children():
                    c.print_tree(output, maxdepth, _curdepth + 1)
        except StateNotFoundError as error:
            output.write("%sError: %s\n" % (indent, error))

    def get_path(self):
        """Return the absolute path of the dbus node"""
        if isinstance(self._path, str):
            return self._path

        return self._path.decode('utf-8')

    @contextmanager
    def no_automatic_refreshing(self):
        """Context manager function to disable automatic DBus refreshing when
        retrieving attributes.

        Example usage:

            with instance.no_automatic_refreshing():
                # access lots of attributes.

        This can be useful if you need to check lots of attributes in a tight
        loop, or if you want to atomicaly check several attributes at once.

        """
        try:
            self.__refresh_on_attribute = False
            yield
        finally:
            self.__refresh_on_attribute = True

    @classmethod
    def validate_dbus_object(cls, path, _state):
        """Return whether this class is the appropriate proxy object class for
        a given dbus path and state.

        The default version matches the name of the dbus object and the class.
        Subclasses of CustomProxyObject can override it to define a different
        validation method.

        :param path: The dbus path of the object to check
        :param state: The dbus state dict of the object to check
                      (ignored in default implementation)
        :returns: Whether this class is appropriate for the dbus object

        """
        state_name = xpathselect.get_classname_from_path(path)
        if isinstance(state_name, str):
            state_name = state_name.encode('utf-8')
        class_name = cls.__name__.encode('utf-8')
        return state_name == class_name

    @classmethod
    def get_type_query_name(cls):
        """Return the Type node name to use within the search query.

        This allows for a Custom Proxy Object to be named differently to the
        underlying node type name.

        For instance if you have a QML type defined in the file RedRect.qml::

            import QtQuick 2.0
            Rectangle {
                color: red;
            }

        You can then define a Custom Proxy Object  for this type like so::

        class RedRect(DBusIntrospectionObject):
            @classmethod
            def get_type_query_name(cls):
                return 'QQuickRectangle'

        This is due to the qml engine storing 'RedRect' as a QQuickRectangle in
        the UI tree and the xpathquery query needs a node type to query for.
        By default the query will use the class name (in this case RedRect) but
        this will not match any node type in the tree.

        """

        return cls.__name__


# TODO - can we add a deprecation warning around this somehow?
CustomEmulatorBase = DBusIntrospectionObject


def get_type_name(maybe_string_or_class):
    """Get a type name from something that might be a class or a string.

    This is a temporary funtion that will be removed once custom proxy classes
    can specify the query to be used to select themselves.

    """
    if not isinstance(maybe_string_or_class, str):
        return _get_class_type_name(maybe_string_or_class)
    return maybe_string_or_class


def _get_class_type_name(maybe_cpo_class):
    if hasattr(maybe_cpo_class, 'get_type_query_name'):
        return maybe_cpo_class.get_type_query_name()
    else:
        return maybe_cpo_class.__name__


def _validate_object_properties(item, **kwargs):
    """Returns bool representing if the properties specified in *kwargs*
    match the provided object *item*."""
    props = item.get_properties()
    for key in kwargs.keys():
        if key not in props or props[key] != kwargs[key]:
            return False
    return True


def raises(exception_class, func, *args, **kwargs):
    """Evaluate if the callable *func* raises the expected
    exception.

    :param exception_class: Expected exception to be raised.

    :param func: The callable that is to be evaluated.

    :param args: Optional *args* to call the *func* with.

    :param kwargs: Optional *kwargs* to call the *func* with.

    :returns: bool, if the exception was raised.
    """
    try:
        func(*args, **kwargs)
    except exception_class:
        return True
    else:
        return False


def is_element(ap_query_func, *args, **kwargs):
    """Call the *ap_query_func* with the args and indicate if it
    raises StateNotFoundError.

    :param: ap_query_func: The dbus query call to be evaluated.

    :param: *args: The *ap_query_func* positional parameters.

    :param: **kwargs: The *ap_query_func* optional parameters.

    :returns: False if the *ap_query_func* raises StateNotFoundError,
        True otherwise.
    """
    return not raises(StateNotFoundError, ap_query_func, *args, **kwargs)


class _MockableDbusObject:
    """Mockable DBus object."""

    def __init__(self, dbus_object):
        self._dbus_object = dbus_object
        self._mocked = False
        self._dbus_object_secondary = None
        sleep.disable_mock()

    @contextmanager
    def mocked(self, dbus_object_secondary):
        try:
            self.enable_mock(dbus_object_secondary)
            yield self
        finally:
            self.disable_mock()

    def enable_mock(self, dbus_object_secondary):
        self._dbus_object_secondary = dbus_object_secondary
        sleep.enable_mock()
        self._mocked = True

    def disable_mock(self):
        self._dbus_object_secondary = None
        sleep.disable_mock()
        self._mocked = False

    def _get_default_dbus_object(self):
        return self._dbus_object

    def _get_secondary_dbus_object(self):
        if not self._mocked:
            return self._get_default_dbus_object()
        else:
            return self._dbus_object_secondary

    def is_moving(self, gap_interval=0.1):
        """Check if the element is moving.

        :param gap_interval: Time in seconds to wait before
            re-inquiring the object co-ordinates to be able
            to evaluate if, the element has moved.

        :return: True, if the element is moving, otherwise False.
        """
        x1, y1, h1, w1 = self._get_default_dbus_object().globalRect
        sleep(gap_interval)
        x2, y2, h2, w2 = self._get_secondary_dbus_object().globalRect

        return x1 != x2 or y1 != y2
