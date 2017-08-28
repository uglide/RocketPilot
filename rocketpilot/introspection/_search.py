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

"""Private module for searching dbus for useful connections."""

import logging
import os
import subprocess
from functools import partial
from operator import methodcaller

import dbus
import psutil

from rocketpilot import dbus_handler, constants
from rocketpilot._timeout import Timeout
from rocketpilot.exceptions import ProcessSearchError
from rocketpilot.introspection import _object_registry
from rocketpilot.introspection import backends
from rocketpilot.introspection import dbus as ap_dbus
from rocketpilot.introspection._xpathselect import get_classname_from_path
from rocketpilot.introspection.backends import WireProtocolVersionMismatch
from rocketpilot.introspection.utilities import (
    _get_bus_connections_pid,
    get_pid_for_process,
)
from rocketpilot.utilities import deprecated

logger = logging.getLogger(__name__)


def get_proxy_object_for_existing_process(**kwargs):
    """Return a single proxy object for an application that is already running
    (i.e. launched outside of Autopilot).

    Searches the given bus (supplied by the kwarg **dbus_bus**) for an
    application matching the search criteria (also supplied in kwargs, see
    further down for explaination on what these can be.)
    Returns a proxy object created using the supplied custom emulator
    **emulator_base** (which defaults to None).

    This function take kwargs arguments containing search parameter values to
    use when searching for the target application.

    **Possible search criteria**:
    *(unless specified otherwise these parameters default to None)*

    :param pid: The PID of the application to search for.
    :param process: The process of the application to search for.
        If provided only the pid of the process is used in the search, but if
        the process exits before the search is complete it is used to supply
        details provided by the process object.
    :param connection_name: A string containing the DBus connection name to
        use with the search criteria.
    :param application_name: A string containing the applications name to
        search for.
    :param object_path: A string containing the object path to use as the
        search criteria.
        Defaults to:
        :py:data:`autopilot.introspection.constants.AUTOPILOT_PATH`.

    **Non-search parameters:**

    :param dbus_bus: The DBus bus to search for the application.
        Must be a string containing either 'session', 'system' or the
        custom buses name (i.e. 'unix:abstract=/tmp/dbus-IgothuMHNk').
        Defaults to 'session'
    :param emulator_base: The custom emulator to use when creating the
        resulting proxy object.
        Defaults to None

    **Exceptions possibly thrown by this function:**

    :raises ProcessSearchError: If no search criteria match.
    :raises RuntimeError: If the search criteria results in many matches.
    :raises RuntimeError: If both ``process`` and ``pid`` are supplied, but
        ``process.pid != pid``.


    **Examples:**

    Retrieving an application on the system bus where the applications PID is
    known::

        app_proxy = get_proxy_object_for_existing_process(pid=app_pid)

    Multiple criteria are allowed, for instance you could search on **pid**
    and **connection_name**::

        app_proxy = get_proxy_object_for_existing_process(
            pid=app_pid,
            connection_name='org.gnome.Gedit'
        )

    If the application from the previous example was on the system bus::

        app_proxy = get_proxy_object_for_existing_process(
            dbus_bus='system',
            pid=app_pid,
            connection_name='org.gnome.Gedit'
        )

    It is possible to search for the application given just the applications
    name.
    An example for an application running on a custom bus searching using the
    applications name::

        app_proxy = get_proxy_object_for_existing_process(
            application_name='qmlscene',
            dbus_bus='unix:abstract=/tmp/dbus-IgothuMHNk'
        )

    """
    # Pop off non-search stuff.
    dbus_bus = _get_dbus_bus_from_string(kwargs.pop('dbus_bus', 'session'))
    process = kwargs.pop('process', None)
    emulator_base = kwargs.pop('emulator_base', None)

    # Force default object_path
    kwargs['object_path'] = kwargs.get('object_path', constants.AUTOPILOT_PATH)
    # Special handling of pid.
    pid = _check_process_and_pid_details(process, kwargs.get('pid', None))
    if pid is not None:
        kwargs['pid'] = pid

    matcher_function = _filter_function_from_search_params(kwargs)

    connections = _find_matching_connections(
        dbus_bus,
        matcher_function,
        process
    )

    if pid is not None:
        # Due to the filtering including children parents, if there exists a
        # top-level pid, take that instead of any children that may have
        # matched.
        connections = _filter_parent_pids_from_children(
            pid,
            connections,
            dbus_bus
        )

    _raise_if_not_single_result(
        connections,
        _get_search_criteria_string_representation(**kwargs)
    )

    object_path = kwargs['object_path']
    connection_name = connections[0]
    return _make_proxy_object(
        _get_dbus_address_object(connection_name, object_path, dbus_bus),
        emulator_base
    )


def get_proxy_object_for_existing_process_by_name(
        process_name,
        emulator_base=None
):
    """Return the proxy object for a process by its name.

    :param process_name: name of the process to get proxy object.
        This must be a string.

    :param emulator_base: emulator base to use with the custom proxy object.

    :raises ValueError: if process not running or more than one PIDs
        associated with the process.

    :return: proxy object for the requested process.
    """
    pid = get_pid_for_process(process_name)
    return get_proxy_object_for_existing_process(
        pid=pid,
        emulator_base=emulator_base
    )


def _map_connection_to_pid(connection, dbus_bus):
    try:
        return _get_bus_connections_pid(dbus_bus, connection)
    except dbus.DBusException as e:
        logger.info(
            "dbus.DBusException while attempting to get PID for %s: %r" %
            (connection, e))


def _filter_parent_pids_from_children(
        pid, connections, dbus_bus, _connection_pid_fn=_map_connection_to_pid):
    """Return any connections that have an actual pid matching the requested
    and aren't just a child of that requested pid.

    :param pid: Pid passed in for matching
    :param connections: List of connections to filter
    :param dbus_bus: Dbus object that the connections are contained.
    :param _connection_pid_fn: Function that takes 2 args 'connection' 'dbus
      object' that returns the pid (or None if not found) of the connection on
      that dbus bus.
      (Note: Useful for testing.)
    :returns: List of suitable connections (e.g. returns what was passed if no
      connections match the pid (i.e. all matches are children)).

    """
    for conn in connections:
        if pid == _connection_pid_fn(conn, dbus_bus):
            logger.info('Found the parent pid, ignoring any others.')
            return [conn]
    return connections


def _get_dbus_bus_from_string(dbus_string):
    if dbus_string == 'session':
        return dbus_handler.get_session_bus()
    elif dbus_string == 'system':
        return dbus_handler.get_system_bus()
    else:
        return dbus_handler.get_custom_bus(dbus_string)


def _check_process_and_pid_details(process=None, pid=None):
    """Do error checking on process and pid specification.

    :raises RuntimeError: if both process and pid are specified, but the
        process's 'pid' attribute is different to the pid attribute specified.
    :raises ProcessSearchError: if the process specified is not running.
    :returns: the pid to use in all search queries.

    """
    if process is not None:
        if pid is None:
            pid = process.pid
        elif pid != process.pid:
            raise RuntimeError("Supplied PID and process.pid do not match.")

    if pid is not None and not psutil.pid_exists(pid):
        raise ProcessSearchError("PID %d could not be found" % pid)
    return pid


def _filter_function_from_search_params(search_params, filter_lookup=None):
    filters = _mandatory_filters() + _filters_from_search_parameters(
        search_params,
        filter_lookup
    )
    return _filter_function_with_sorted_filters(filters, search_params)


def _mandatory_filters():
    """Returns a list of Filters that are considered mandatory regardless of
    the search parameters supplied by the user.

    """
    return [
        ConnectionIsNotOurConnection,
        ConnectionIsNotOrgFreedesktopDBus
    ]


def _filter_lookup_map():
    return dict(
        connection_name=ConnectionHasName,
        application_name=ConnectionHasAppName,
        object_path=ConnectionHasPathWithAPInterface,
        pid=ConnectionHasPid,
    )


def _filters_from_search_parameters(parameters, filter_lookup=None):
    parameter_filter_lookup = filter_lookup or _filter_lookup_map()
    try:
        filter_list = list({
            parameter_filter_lookup[key]
            for key in parameters.keys()
        })
        return filter_list
    except KeyError as e:
        raise KeyError(
            "Search parameter %s doesn't have a corresponding filter in %r"
            % (e, parameter_filter_lookup),
        )


def _filter_function_with_sorted_filters(filters, search_params):
    """Returns a callable filter function that will take the argument
    (dbus_tuple).

    The returned filter function will be bound to use a prioritised filter list
    and the supplied search parameters dictionary.

    """

    sorted_filter_list = _priority_sort_filters(filters)
    return partial(_filter_runner, sorted_filter_list, search_params)


def _priority_sort_filters(filter_list):
    return sorted(filter_list, key=methodcaller('priority'), reverse=True)


def _filter_runner(filter_list, search_parameters, dbus_tuple):
    """Helper function to run filters over dbus connections.

    :param filter_list: List of filters to call matches on passing the provided
      dbus details and search parameters.
    :param dbus_tuple: 2 length tuple containing (bus, connection_name) where
      bus is a SessionBus, SystemBus or BusConnection object and
      connection_name is a string.
    :param search_parameters: Dictionary of search parameters that the filters
      will consume to make their decisions.

    """
    if not filter_list:
        raise ValueError("Filter list must not be empty")
    return all(
        f.matches(dbus_tuple, search_parameters)
        for f in filter_list
    )


def _find_matching_connections(bus, connection_matcher, process=None):
    """Returns a list of connection names that have passed the
    connection_matcher.

    :param dbus_bus: A DBus bus object to search
        (i.e. SessionBus, SystemBus or BusConnection)
    :param connection_matcher: Callable that takes a connection name and
        returns True if it is what we're looking for, False otherwise.
    :param process: (optional) A process object that we're looking for it's
        dbus connection.
        Used to ensure that the process is in fact still running
        while we're searching for it.

    """
    for _ in Timeout.default():
        _get_child_pids.reset_cache()
        _raise_if_process_has_exited(process)

        connections = bus.list_names()

        valid_connections = [
            c for c
            in connections
            if connection_matcher((bus, c))
        ]

        if len(valid_connections) >= 1:
            return _dedupe_connections_on_pid(valid_connections, bus)

    return []


def _raise_if_process_has_exited(process):
    """Raises ProcessSearchError if process is no longer running."""
    if process is not None and not _process_is_running(process):
        return_code = process.poll()
        raise ProcessSearchError(
            "Process exited with exit code: %d"
            % return_code
        )


def _process_is_running(process):
    return process.poll() is None


def _dedupe_connections_on_pid(valid_connections, bus):
    seen_pids = []
    deduped_connections = []

    for connection in valid_connections:
        pid = _get_bus_connections_pid(bus, connection)
        if pid not in seen_pids:
            seen_pids.append(pid)
            deduped_connections.append(connection)
    return deduped_connections


def _raise_if_not_single_result(connections, criteria_string):
    if connections is None or len(connections) == 0:
        raise ProcessSearchError(
            "Search criteria (%s) returned no results" %
            (criteria_string)
        )

    if len(connections) > 1:
        raise RuntimeError(
            "Search criteria (%s) returned multiple results"
            % (criteria_string)
        )


def _get_search_criteria_string_representation(**kwargs):
    # Some slight re-naming for process objects
    if kwargs.get('process') is not None:
        kwargs['process_object'] = "%r" % kwargs.pop('process')

    return ", ".join([
        "%s = %r" % (k.replace("_", " "), v)
        for k, v
        in kwargs.items()
    ])


def _make_proxy_object(dbus_address, emulator_base):
    """Returns a root proxy object given a DBus service name.

    :param dbus_address: The DBusAddress object we're querying.
    :param emulator_base: The emulator base object (or None), as provided by
        the user.
    """
    # make sure we always have an emulator base. Either use the one the user
    # gave us, or make one:
    emulator_base = emulator_base or _make_default_emulator_base()
    _raise_if_base_class_not_actually_base(emulator_base)

    # Get the dbus introspection Xml for the backend.
    intro_xml = _get_introspection_xml_from_backend(dbus_address)
    try:
        # Figure out if the backend has any extension methods, and return
        # classes that understand how to use each of those extensions:
        extension_classes = _get_proxy_bases_from_introspection_xml(intro_xml)

        # Register those base classes for everything that will derive from this
        # emulator base class.
        _object_registry.register_extension_classes_for_proxy_base(
            emulator_base,
            extension_classes,
        )
    except RuntimeError as e:
        e.args = (
            "Could not find Autopilot interface on dbus address '%s'."
            % dbus_address,
        )
        raise e

    cls_name, path, cls_state = _get_proxy_object_class_name_and_state(
        dbus_address
    )

    proxy_class = _object_registry._get_proxy_object_class(
        emulator_base._id,
        path,
        cls_state
    )
    # For this object only, add the ApplicationProxy class, since it's the
    # root of the tree. Ideally this would be nicer...
    if ApplicationProxyObject not in proxy_class.__bases__:
        proxy_class.__bases__ += (ApplicationProxyObject, )
    return proxy_class(cls_state, path, backends.Backend(dbus_address))


def _make_default_emulator_base():
    """Make a default base class for all proxy classes to derive from."""
    return type("DefaultEmulatorBase", (ap_dbus.DBusIntrospectionObject,), {})


WRONG_CPO_CLASS_MSG = '''\
base_class: {passed} does not appear to be the actual base CPO class.
Perhaps you meant to use: {actual}.'''


def _raise_if_base_class_not_actually_base(base_class):
    """Raises ValueError if the provided base_class is not actually the
       base_class

    To ensure that the expected base classes are used when creating proxy
    objects.

    :param base_class: The base class to check.
    :raises ValueError: The actual base class is not the one provided

    """
    actual_base_class = base_class
    for cls in base_class.mro():
        if hasattr(cls, '_id'):
            actual_base_class = cls

    if actual_base_class != base_class:
        raise(
            ValueError(
                WRONG_CPO_CLASS_MSG.format(
                    passed=base_class,
                    actual=actual_base_class
                )
            )
        )


def _make_proxy_object_async(
        data_source, emulator_base, reply_handler, error_handler):
    """Make a proxy object for a dbus backend.

    Similar to :meth:`_make_proxy_object` except this method runs
    asynchronously and must have a reply_handler callable set. The
    reply_handler will be called with a single argument: The proxy object.

    """
    # Note: read this function backwards!
    #
    # Due to the callbacks, I need to define the end of the callback chain
    # first, so start reading from the bottom of the function upwards, and
    # it'll make a whole lot more sense.

    # Final phase: We have all the information we need, now we construct
    # everything. This phase has no dbus calls, and so is very fast:
    def build_proxy(introspection_xml, cls_name, path, cls_state):
        # Figure out if the backend has any extension methods, and return
        # classes that understand how to use each of those extensions:
        extension_classes = _get_proxy_bases_from_introspection_xml(
            introspection_xml
        )
        # Register those base classes for everything that will derive from this
        # emulator base class.
        _object_registry.register_extension_classes_for_proxy_base(
            emulator_base,
            extension_classes,
        )
        proxy_class = _object_registry._get_proxy_object_class(
            emulator_base._id,
            path,
            cls_state
        )
        reply_handler(
            proxy_class(cls_state, path, backends.Backend(data_source))
        )

    # Phase 2: We recieve the introspection string, and make an asynchronous
    # dbus call to get the state information for the root of this applicaiton.
    def get_root_state(introspection_xml):
        _get_proxy_object_class_name_and_state(
            data_source,
            reply_handler=partial(build_proxy, introspection_xml),
            error_handler=error_handler,
        )

    # Phase 1: Make an asynchronous dbus call to get the introspection xml
    # from the data_source provided for us.
    emulator_base = emulator_base or _make_default_emulator_base()

    _get_introspection_xml_from_backend(
        data_source,
        reply_handler=get_root_state,
        error_handler=error_handler
    )


def _get_introspection_xml_from_backend(
        backend, reply_handler=None, error_handler=None):
    """Get DBus Introspection xml from a backend.

    :param backend: The backend object to query.
    :param reply_handler: If set, makes a dbus async call, and the result will
        be sent to reply_handler. This must be a callable object.
    :param error_handler: If set, this callable will recieve any errors, and
        the call will be made asyncronously.
    :returns: A string containing introspection xml, if called synchronously.
    :raises ValueError: if one, but not both of 'reply_handler' and
        'error_handler' are set.

    """
    if callable(reply_handler) and callable(error_handler):
        backend.dbus_introspection_iface.Introspect(
            reply_handler=reply_handler,
            error_handler=error_handler,
        )
    elif reply_handler or error_handler:
        raise ValueError(
            "Both 'reply_handler' and 'error_handler' must be set."
        )
    else:
        return backend.dbus_introspection_iface.Introspect()


def _get_proxy_object_class_name_and_state(
        backend, reply_handler=None, error_handler=None):
    """Get details about this autopilot backend via a dbus GetState call.

    :param reply_handler: A callable that must accept three positional
        arguments, which correspond to the return value of this function when
        called synchronously.

    :param error_handler: A callable which will recieve any dbus errors, should
        they occur.

    :raises ValueError: if one, but not both of reply_handler and error_handler
        are set.

    :returns: A tuple containing the class name of the root of the
        introspection tree, the full path to the root of the introspection
        tree, and the state dictionary of the root node in the introspection
        tree.

    """
    if callable(reply_handler) and callable(error_handler):
        # Async call:
        # Since we get an array of state, and we only care about the first one
        # we use a lambda to unpack it and get the details we want.
        backend.introspection_iface.GetState(
            "/",
            reply_handler=lambda r: reply_handler(
                *_get_details_from_state_data(r[0])
            ),
            error_handler=error_handler,
        )
    elif reply_handler or error_handler:
        raise ValueError(
            "Both 'reply_handler' and 'error_handler' must be set."
        )
    else:
        # Sync call
        state = backend.introspection_iface.GetState("/")[0]
        return _get_details_from_state_data(state)


def _get_details_from_state_data(state_data):
    """Get details from a state data array.

    Returns class name, path, and state dictionary.
    """
    object_path, object_state = state_data
    return (
        get_classname_from_path(object_path),
        object_path.encode('utf-8'),
        object_state,
    )


def _get_proxy_bases_from_introspection_xml(introspection_xml):
    """Return  tuple of the base classes to use when creating a proxy object.

    Currently this works by looking for certain interface names in the XML. In
    the future we may want to parse the XML and perform more rigerous checks.

    :param introspection_xml: An xml string that describes the exported object
        on the dbus backend. This determines which capabilities are present in
        the backend, and therefore which base classes should be used to create
        the proxy object.

    :raises RuntimeError: if the autopilot interface cannot be found.

    """

    bases = []

    if constants.AP_INTROSPECTION_IFACE not in introspection_xml:
        raise RuntimeError("Could not find Autopilot interface.")

    if constants.QT_AUTOPILOT_IFACE in introspection_xml:
        from rocketpilot.introspection.qt import QtObjectProxyMixin
        bases.append(QtObjectProxyMixin)

    return tuple(bases)


class ApplicationProxyObject(object):
    """A class that better supports query data from an application."""

    def __init__(self):
        self._process = None

    def set_process(self, process):
        """Set the subprocess.Popen object of the process that this is a proxy
        for.

        You should never normally need to call this method.

        """
        self._process = process

    @property
    def pid(self):
        return self._process.pid

    @property
    def process(self):
        return self._process

    @deprecated(
        "the AutopilotTestCase launch_test_application method to handle"
        " cleanup of launched applications."
    )
    def kill_application(self):
        """Kill the running process that this is a proxy for using
        'kill `pid`'."""
        subprocess.call(["kill", "%d" % self._process.pid])


def _extend_proxy_bases_with_emulator_base(proxy_bases, emulator_base):
    if emulator_base is None:
        emulator_base = type(
            'DefaultEmulatorBase',
            (ap_dbus.CustomEmulatorBase,),
            {}
        )
    return proxy_bases + (emulator_base, )


def _get_dbus_address_object(connection_name, object_path, bus):
    return backends.DBusAddress(bus, connection_name, object_path)


class _cached_get_child_pids(object):
    """Get a list of all child process Ids, for the given parent.

    Since we call this often, and it's a very expensive call, we optimise this
    such that the return value will be cached for each scan through the dbus
    bus.

    Calling reset_cache() at the end of each dbus scan will ensure that you get
    fresh values on the next call.
    """

    def __init__(self):
        self._cached_result = None

    def __call__(self, pid):
        if self._cached_result is None:
            self._cached_result = [
                p.pid for p in psutil.Process(pid).children(recursive=True)
            ]
        return self._cached_result

    def reset_cache(self):
        self._cached_result = None


_get_child_pids = _cached_get_child_pids()


# Filters

class ConnectionIsNotOrgFreedesktopDBus(object):

    """Not interested in any connections with names 'org.freedesktop.DBus'."""

    @classmethod
    def priority(cls):
        """A connection with this name will never be valid."""
        return 13

    @classmethod
    def matches(cls, dbus_tuple, params):
        bus, connection_name = dbus_tuple
        return connection_name != 'org.freedesktop.DBus'


class ConnectionIsNotOurConnection(object):

    """Ensure we're not inspecting our own bus connection."""

    @classmethod
    def priority(cls):
        """The connection from this process will never be valid."""
        return 12

    @classmethod
    def matches(cls, dbus_tuple, params):
        try:
            bus, connection_name = dbus_tuple
            bus_pid = _get_bus_connections_pid(bus, connection_name)
            return bus_pid != os.getpid()
        except dbus.DBusException as e:
            return False


class ConnectionHasName(object):

    """Ensure connection_name within dbus_tuple is the name we want."""

    @classmethod
    def priority(cls):
        """Connection name is easy to check for and if not valid, nothing else
        will be.

        """
        return 11

    @classmethod
    def matches(cls, dbus_tuple, params):
        """Returns true if the connection name in dbus_tuple is the name
        in the search criteria params.

        """
        requested_connection_name = params['connection_name']
        bus, connection_name = dbus_tuple

        return connection_name == requested_connection_name


class ConnectionHasPid(object):

    """Match a connection based on the connections pid."""

    @classmethod
    def priority(cls):
        return 9

    @classmethod
    def matches(cls, dbus_tuple, params):
        """Match a connection based on the connections pid.

        :raises KeyError: if the pid parameter isn't passed in params.

        """

        pid = params['pid']
        bus, connection_name = dbus_tuple

        try:
            bus_pid = _get_bus_connections_pid(bus, connection_name)
        except dbus.DBusException as e:
            logger.info(
                "dbus.DBusException while attempting to get PID for %s: %r" %
                (connection_name, e))
            return False

        eligible_pids = [pid] + _get_child_pids(pid)
        return bus_pid in eligible_pids


class ConnectionHasPathWithAPInterface(object):

    """Ensure that the connection exposes the Autopilot interface."""

    @classmethod
    def priority(cls):
        return 8

    @classmethod
    def matches(cls, dbus_tuple, params):
        """Ensure the connection has the path that we expect to be there.

        :raises KeyError: if the object_path parameter isn't included in
        params.

        """
        try:
            bus, connection_name = dbus_tuple
            path = params['object_path']
            obj = bus.get_object(connection_name, path)
            dbus.Interface(
                obj,
                'com.canonical.Autopilot.Introspection'
            ).GetVersion()
            return True
        except dbus.DBusException:
            return False


class ConnectionHasAppName(object):

    """Ensure the connection has the requested Application name."""

    @classmethod
    def priority(cls):
        return 0

    @classmethod
    def matches(cls, dbus_tuple, params):
        """Returns True if dbus_tuple has the required application name.

        Can be provided an optional object_path parameter. This defaults to
        :py:data:`autopilot.introspection.constants.AUTOPILOT_PATH` if not
        provided.

        This filter should only activated if the application_name is provided
        in the search criteria.

        :raises KeyError: if the 'application_name' parameter isn't passed in
            params

        """
        requested_app_name = params['application_name']
        object_path = params.get('object_path', constants.AUTOPILOT_PATH)
        bus, connection_name = dbus_tuple

        try:
            app_name = cls._get_application_name(
                bus,
                connection_name,
                object_path
            )
            return app_name == requested_app_name
        except WireProtocolVersionMismatch:
            return False

    @classmethod
    def _get_application_name(cls, bus, connection_name, object_path):
        dbus_object = _get_dbus_address_object(
            connection_name,
            object_path,
            bus
        )
        return cls._get_application_name_from_dbus_address(dbus_object)

    @classmethod
    def _get_application_name_from_dbus_address(cls, dbus_address):
        """Return the application name from a dbus_address object."""
        return get_classname_from_path(
            dbus_address.introspection_iface.GetState('/')[0][0]
        )
