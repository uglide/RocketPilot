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

from dbus import DBusException
import os
from unittest.mock import call, patch, Mock
from testtools import TestCase
from testtools.matchers import (
    Contains,
    Equals,
    MatchesAll,
    MatchesListwise,
    MatchesSetwise,
    Not,
    raises,
)

from autopilot.exceptions import ProcessSearchError
from autopilot.utilities import sleep
from autopilot.introspection import _search as _s

from autopilot.introspection import CustomEmulatorBase
from autopilot.introspection.constants import AUTOPILOT_PATH


def ListContainsOnly(value_list):
    """Returns a MatchesAll matcher for comparing a list."""
    return MatchesSetwise(*map(Equals, value_list))


class PassingFilter(object):

    @classmethod
    def matches(cls, dbus_tuple, params):
        return True


class FailingFilter(object):

    @classmethod
    def matches(cls, dbus_tuple, params):
        return False


class LowPriorityFilter(object):

    @classmethod
    def priority(cls):
        return 0


class HighPriorityFilter(object):

    @classmethod
    def priority(cls):
        return 10


class MatcherCallableTests(TestCase):

    def test_can_provide_list_of_filters(self):
        _s._filter_runner([PassingFilter], None, None)

    def test_passing_empty_filter_list_raises(self):
        self.assertThat(
            lambda: _s._filter_runner([], None, None),
            raises(ValueError("Filter list must not be empty"))
        )

    def test_matches_returns_True_with_PassingFilter(self):
        self.assertTrue(_s._filter_runner([PassingFilter], None, None))

    def test_matches_returns_False_with_FailingFilter(self):
        self.assertFalse(_s._filter_runner([FailingFilter], None, None))

    def test_fails_when_first_filter_fails(self):
        self.assertFalse(
            _s._filter_runner([FailingFilter, PassingFilter], None, None)
        )

    def test_fails_when_second_filter_fails(self):
        self.assertFalse(
            _s._filter_runner([PassingFilter, FailingFilter], None, None)
        )

    def test_passes_when_two_filters_pass(self):
        self.assertTrue(
            _s._filter_runner([PassingFilter, PassingFilter], None, None)
        )

    def test_fails_when_two_filters_fail(self):
        self.assertFalse(
            _s._filter_runner([FailingFilter, FailingFilter], None, None)
        )

    def test_filter_returning_False_results_in_failure(self):
        class FalseFilter(object):
            @classmethod
            def matches(cls, dbus_tuple, params):
                return False

        _s._filter_runner([FalseFilter], None, None)
        self.assertFalse(
            _s._filter_runner([FalseFilter], None, None)
        )

    def test_runner_matches_passes_dbus_tuple_to_filter(self):
        DBusConnectionFilter = Mock()
        dbus_tuple = ("bus", "connection_name")

        _s._filter_runner([DBusConnectionFilter], {}, dbus_tuple)

        DBusConnectionFilter.matches.assert_called_once_with(
            dbus_tuple, {}
        )


class FilterFunctionGeneratorTests(TestCase):

    """Tests to ensure the correctness of the
    _filter_function_from_search_params function.

    """

    def test_uses_priority_sorted_filter_list(self):
        unsorted_filters = [LowPriorityFilter, HighPriorityFilter]
        matcher = _s._filter_function_with_sorted_filters(unsorted_filters, {})
        self.assertThat(
            matcher.args[0],
            Equals([HighPriorityFilter, LowPriorityFilter])
        )


class FiltersFromSearchParametersTests(TestCase):

    def test_raises_with_unknown_search_parameter(self):
        search_parameters = dict(unexpected_key=True)
        placeholder_lookup = dict(noop_lookup=True)

        self.assertThat(
            lambda: _s._filters_from_search_parameters(
                search_parameters,
                placeholder_lookup
            ),
            raises(
                KeyError(
                    "Search parameter 'unexpected_key' doesn't have a "
                    "corresponding filter in %r"
                    % placeholder_lookup
                )
            )
        )

    def test_returns_only_required_filters(self):
        search_parameters = dict(high=True, low=True)
        filter_lookup = dict(
            high=HighPriorityFilter,
            low=LowPriorityFilter,
            passing=PassingFilter,
        )

        self.assertThat(
            _s._filters_from_search_parameters(
                search_parameters,
                filter_lookup
            ),
            ListContainsOnly([HighPriorityFilter, LowPriorityFilter])
        )

    def test_creates_unique_list_of_filters(self):
        search_parameters = dict(pid=True, process=True)
        filter_lookup = dict(
            pid=HighPriorityFilter,
            process=HighPriorityFilter
        )
        self.assertThat(
            _s._filters_from_search_parameters(
                search_parameters,
                filter_lookup
            ),
            ListContainsOnly([HighPriorityFilter])
        )

    def test_doesnt_modify_search_parameters(self):
        search_parameters = dict(high=True)
        filter_lookup = dict(high=HighPriorityFilter)

        _s._filters_from_search_parameters(
            search_parameters,
            filter_lookup
        )

        self.assertThat(search_parameters.get('high', None), Not(Equals(None)))


class MandatoryFiltersTests(TestCase):

    def test_returns_list_containing_mandatory_filters(self):
        self.assertThat(
            _s._mandatory_filters(),
            ListContainsOnly([
                _s.ConnectionIsNotOurConnection,
                _s.ConnectionIsNotOrgFreedesktopDBus
            ])
        )


class PrioritySortFiltersTests(TestCase):

    def test_sorts_filters_based_on_priority(self):
        self.assertThat(
            _s._priority_sort_filters(
                [LowPriorityFilter, HighPriorityFilter]
            ),
            Equals([HighPriorityFilter, LowPriorityFilter])
        )

    def test_sorts_single_filter_based_on_priority(self):
        self.assertThat(
            _s._priority_sort_filters(
                [LowPriorityFilter]
            ),
            Equals([LowPriorityFilter])
        )


class FilterFunctionFromFiltersTests(TestCase):

    def test_returns_a_callable(self):
        self.assertTrue(
            callable(_s._filter_function_with_sorted_filters([], {}))
        )

    def test_uses_sorted_filter_list(self):
        matcher = _s._filter_function_with_sorted_filters(
            [HighPriorityFilter, LowPriorityFilter],
            {}
        )

        self.assertThat(
            matcher.args[0], Equals([HighPriorityFilter, LowPriorityFilter])
        )


class ConnectionHasNameTests(TestCase):

    """Tests specific to the ConnectionHasName filter."""

    def test_raises_KeyError_when_missing_connection_name_param(self):
        dbus_tuple = ("bus", "name")
        self.assertThat(
            lambda: _s.ConnectionHasName.matches(dbus_tuple, {}),
            raises(KeyError('connection_name'))
        )

    def test_returns_True_when_connection_name_matches(self):
        dbus_tuple = ("bus", "connection_name")
        search_params = dict(connection_name="connection_name")
        self.assertTrue(
            _s.ConnectionHasName.matches(dbus_tuple, search_params)
        )

    def test_returns_False_when_connection_name_matches(self):
        dbus_tuple = ("bus", "connection_name")
        search_params = dict(connection_name="not_connection_name")
        self.assertFalse(
            _s.ConnectionHasName.matches(dbus_tuple, search_params)
        )


class ConnectionIsNotOurConnectionTests(TestCase):

    @patch.object(_s, '_get_bus_connections_pid')
    def test_doesnt_raise_exception_with_no_parameters(self, get_bus_pid):
        dbus_tuple = ("bus", "name")
        _s.ConnectionIsNotOurConnection.matches(dbus_tuple, {})

    @patch.object(_s, '_get_bus_connections_pid', return_value=0)
    def test_returns_True_when_pid_isnt_our_connection(self, get_bus_pid):
        dbus_tuple = ("bus", "name")
        self.assertTrue(
            _s.ConnectionIsNotOurConnection.matches(
                dbus_tuple,
                {}
            )
        )

    @patch.object(_s, '_get_bus_connections_pid', return_value=os.getpid())
    def test_returns_False_when_pid_is_our_connection(self, get_bus_pid):
        dbus_tuple = ("bus", "name")
        self.assertFalse(
            _s.ConnectionIsNotOurConnection.matches(
                dbus_tuple,
                {}
            )
        )

    @patch.object(_s, '_get_bus_connections_pid', side_effect=DBusException())
    def test_returns_False_exception_raised(self, get_bus_pid):
        dbus_tuple = ("bus", "name")
        self.assertFalse(
            _s.ConnectionIsNotOurConnection.matches(
                dbus_tuple,
                {}
            )
        )


class ConnectionHasPathWithAPInterfaceTests(TestCase):

    """Tests specific to the ConnectionHasPathWithAPInterface filter."""

    def test_raises_KeyError_when_missing_object_path_param(self):
        dbus_tuple = ("bus", "name")
        self.assertThat(
            lambda: _s.ConnectionHasPathWithAPInterface.matches(
                dbus_tuple,
                {}
            ),
            raises(KeyError('object_path'))
        )

    @patch.object(_s.dbus, "Interface")
    def test_returns_True_on_success(self, Interface):
        bus_obj = Mock()
        connection_name = "name"
        path = "path"
        dbus_tuple = (bus_obj, connection_name)

        self.assertTrue(
            _s.ConnectionHasPathWithAPInterface.matches(
                dbus_tuple,
                dict(object_path=path)
            )
        )

        bus_obj.get_object.assert_called_once_with("name", path)

    @patch.object(_s.dbus, "Interface")
    def test_returns_False_on_dbus_exception(self, Interface):
        bus_obj = Mock()
        connection_name = "name"
        path = "path"
        dbus_tuple = (bus_obj, connection_name)

        Interface.side_effect = DBusException()

        self.assertFalse(
            _s.ConnectionHasPathWithAPInterface.matches(
                dbus_tuple,
                dict(object_path=path)
            )
        )

        bus_obj.get_object.assert_called_once_with("name", path)


class ConnectionHasPidTests(TestCase):
    """Tests specific to the ConnectionHasPid filter."""

    def test_raises_when_missing_param(self):
        self.assertThat(
            lambda: _s.ConnectionHasPid.matches(None, {}),
            raises(KeyError('pid'))
        )

    def test_returns_True_when_bus_pid_matches(self):
        connection_pid = self.getUniqueInteger()
        dbus_tuple = ("bus", "org.freedesktop.DBus")
        params = dict(pid=connection_pid)
        with patch.object(
            _s,
            '_get_bus_connections_pid',
            return_value=connection_pid
        ):
            self.assertTrue(
                _s.ConnectionHasPid.matches(dbus_tuple, params)
            )

    def test_returns_False_with_DBusException(self):
        connection_pid = self.getUniqueInteger()
        dbus_tuple = ("bus", "org.freedesktop.DBus")
        params = dict(pid=connection_pid)
        with patch.object(
            _s,
            '_get_bus_connections_pid',
            side_effect=DBusException()
        ):
            self.assertFalse(
                _s.ConnectionHasPid.matches(dbus_tuple, params)
            )


class ConnectionIsNotOrgFreedesktopDBusTests(TestCase):

    """Tests specific to the ConnectionIsNotOrgFreedesktopDBus filter."""

    def test_returns_True_when_connection_name_isnt_DBus(self):
        dbus_tuple = ("bus", "connection.name")
        self.assertTrue(
            _s.ConnectionIsNotOrgFreedesktopDBus.matches(dbus_tuple, {})
        )

    def test_returns_False_when_connection_name_is_DBus(self):
        dbus_tuple = ("bus", "org.freedesktop.DBus")
        self.assertFalse(
            _s.ConnectionIsNotOrgFreedesktopDBus.matches(dbus_tuple, {})
        )


class ConnectionHasAppNameTests(TestCase):

    """Tests specific to the ConnectionHasAppName filter."""

    def test_raises_when_missing_app_name_param(self):
        self.assertThat(
            lambda: _s.ConnectionHasAppName.matches(None, {}),
            raises(KeyError('application_name'))
        )

    @patch.object(_s.ConnectionHasAppName, '_get_application_name')
    def test_uses_default_object_name_when_not_provided(self, app_name):
        dbus_tuple = ("bus", "connection_name")
        search_params = dict(application_name="application_name")
        _s.ConnectionHasAppName.matches(dbus_tuple, search_params)

        app_name.assert_called_once_with(
            "bus",
            "connection_name",
            AUTOPILOT_PATH
        )

    @patch.object(_s.ConnectionHasAppName, '_get_application_name')
    def test_uses_provided_object_name(self, app_name):
        object_name = self.getUniqueString()
        dbus_tuple = ("bus", "connection_name")
        search_params = dict(
            application_name="application_name",
            object_path=object_name
        )
        _s.ConnectionHasAppName.matches(dbus_tuple, search_params)

        app_name.assert_called_once_with(
            "bus",
            "connection_name",
            object_name
        )

    def get_mock_dbus_address_with_app_name(slf, app_name):
        mock_dbus_address = Mock()
        mock_dbus_address.introspection_iface.GetState.return_value = (
            ('/' + app_name, {}),
        )
        return mock_dbus_address

    def test_get_application_name_returns_application_name(self):
        with patch.object(_s, '_get_dbus_address_object') as gdbao:
            gdbao.return_value = self.get_mock_dbus_address_with_app_name(
                "SomeAppName"
            )
            self.assertEqual(
                _s.ConnectionHasAppName._get_application_name("", "", ""),
                "SomeAppName"
            )


class FilterHelpersTests(TestCase):

    """Tests for helpers around the Filters themselves."""

    def test_param_to_filter_includes_all(self):
        """Ensure all filters are used in the matcher when requested."""
        search_parameters = {
            f: True
            for f
            in _s._filter_lookup_map().keys()
        }
        self.assertThat(
            _s._filters_from_search_parameters(search_parameters),
            ListContainsOnly(_s._filter_lookup_map().values())
        )

    def test_filter_priority_order_is_correct(self):
        """Ensure all filters are used in the matcher when requested."""
        search_parameters = {
            f: True
            for f
            in _s._filter_lookup_map().keys()
        }
        search_filters = _s._filters_from_search_parameters(search_parameters)
        mandatory_filters = _s._mandatory_filters()
        sorted_filters = _s._priority_sort_filters(
            search_filters + mandatory_filters
        )

        expected_filter_order = [
            _s.ConnectionIsNotOrgFreedesktopDBus,
            _s.ConnectionIsNotOurConnection,
            _s.ConnectionHasName,
            _s.ConnectionHasPid,
            _s.ConnectionHasPathWithAPInterface,
            _s.ConnectionHasAppName,
        ]

        self.assertThat(
            sorted_filters,
            MatchesListwise(list(map(Equals, expected_filter_order)))
        )


class ProcessAndPidErrorCheckingTests(TestCase):

    def test_raises_ProcessSearchError_when_process_is_not_running(self):
        with patch.object(_s, '_pid_is_running') as pir:
            pir.return_value = False

            self.assertThat(
                lambda: _s._check_process_and_pid_details(pid=123),
                raises(ProcessSearchError("PID 123 could not be found"))
            )

    def test_raises_RuntimeError_when_pid_and_process_disagree(self):
        mock_process = Mock()
        mock_process.pid = 1

        self.assertThat(
            lambda: _s._check_process_and_pid_details(mock_process, 2),
            raises(RuntimeError("Supplied PID and process.pid do not match."))
        )

    def test_returns_pid_when_specified(self):
        expected = self.getUniqueInteger()
        with patch.object(_s, '_pid_is_running') as pir:
            pir.return_value = True

            observed = _s._check_process_and_pid_details(pid=expected)

        self.assertEqual(expected, observed)

    def test_returns_process_pid_attr_when_specified(self):
        fake_process = Mock()
        fake_process.pid = self.getUniqueInteger()

        with patch.object(_s, '_pid_is_running') as pir:
            pir.return_value = True
            observed = _s._check_process_and_pid_details(fake_process)

        self.assertEqual(fake_process.pid, observed)

    def test_returns_None_when_neither_parameters_present(self):
        self.assertEqual(
            None,
            _s._check_process_and_pid_details()
        )

    def test_returns_pid_when_both_specified(self):
        fake_process = Mock()
        fake_process.pid = self.getUniqueInteger()
        with patch.object(_s, '_pid_is_running') as pir:
            pir.return_value = True
            observed = _s._check_process_and_pid_details(
                fake_process,
                fake_process.pid
            )
        self.assertEqual(fake_process.pid, observed)


class FilterParentPidsFromChildrenTests(TestCase):

    def test_returns_all_connections_with_no_parent_match(self):
        search_pid = 123
        connections = ['1:0', '1:3']
        dbus_bus = Mock()
        pid_mapping = Mock(side_effect=[111, 222])
        self.assertThat(
            _s._filter_parent_pids_from_children(
                search_pid,
                connections,
                dbus_bus,
                _connection_pid_fn=pid_mapping
            ),
            Equals(connections)
        )

    def test_calls_connection_pid_fn_in_order(self):
        search_pid = 123
        connections = ['1:3', '1:0']
        dbus_bus = Mock()
        pid_mapping = Mock(side_effect=[222, 123])
        _s._filter_parent_pids_from_children(
            search_pid,
            connections,
            dbus_bus,
            _connection_pid_fn=pid_mapping
        )

        self.assertTrue(
            pid_mapping.call_args_list == [
                call('1:3', dbus_bus),
                call('1:0', dbus_bus)
            ]
        )

    def test_returns_just_parent_connection_with_pid_match(self):
        search_pid = 123
        # connection '1.0' has pid 123.
        connections = ['1:3', '1:0']
        dbus_bus = Mock()
        # Mapping returns parent pid on second call.
        pid_mapping = Mock(side_effect=[222, 123])
        self.assertThat(
            _s._filter_parent_pids_from_children(
                search_pid,
                connections,
                dbus_bus,
                _connection_pid_fn=pid_mapping
            ),
            Equals(['1:0'])
        )

        self.assertTrue(
            pid_mapping.call_args_list == [
                call('1:3', dbus_bus),
                call('1:0', dbus_bus)
            ]
        )

    def test_returns_all_connections_with_no_pids_returned_in_search(self):
        search_pid = 123
        connections = ['1:3', '1:0']
        dbus_bus = Mock()
        pid_mapping = Mock(side_effect=[None, None])
        self.assertThat(
            _s._filter_parent_pids_from_children(
                search_pid,
                connections,
                dbus_bus,
                _connection_pid_fn=pid_mapping
            ),
            Equals(connections)
        )


class ProcessSearchErrorStringRepTests(TestCase):

    """Various tests for the _get_search_criteria_string_representation
    function.

    """

    def test_get_string_rep_defaults_to_empty_string(self):
        observed = _s._get_search_criteria_string_representation()
        self.assertEqual("", observed)

    def test_pid(self):
        self.assertEqual(
            'pid = 123',
            _s._get_search_criteria_string_representation(pid=123)
        )

    def test_dbus_bus(self):
        self.assertEqual(
            "dbus bus = 'foo'",
            _s._get_search_criteria_string_representation(dbus_bus='foo')
        )

    def test_connection_name(self):
        self.assertEqual(
            "connection name = 'foo'",
            _s._get_search_criteria_string_representation(
                connection_name='foo'
            )
        )

    def test_object_path(self):
        self.assertEqual(
            "object path = 'foo'",
            _s._get_search_criteria_string_representation(object_path='foo')
        )

    def test_application_name(self):
        self.assertEqual(
            "application name = 'foo'",
            _s._get_search_criteria_string_representation(
                application_name='foo'
            )
        )

    def test_process_object(self):
        class FakeProcess(object):

            def __repr__(self):
                return 'foo'
        process = FakeProcess()
        self.assertEqual(
            "process object = 'foo'",
            _s._get_search_criteria_string_representation(process=process)
        )

    def test_all_parameters_combined(self):
        class FakeProcess(object):

            def __repr__(self):
                return 'foo'
        process = FakeProcess()
        observed = _s._get_search_criteria_string_representation(
            pid=123,
            dbus_bus='session_bus',
            connection_name='com.Canonical.Unity',
            object_path='/com/Canonical/Autopilot',
            application_name='MyApp',
            process=process
        )

        expected_strings = [
            "pid = 123",
            "dbus bus = 'session_bus'",
            "connection name = 'com.Canonical.Unity'",
            "object path = '/com/Canonical/Autopilot'",
            "application name = 'MyApp'",
            "process object = 'foo'",
        ]
        self.assertThat(
            observed,
            MatchesAll(*map(Contains, expected_strings))
        )


class ProxyObjectTests(TestCase):

    def test_raise_if_not_single_result_raises_on_0_connections(self):
        criteria_string = self.getUniqueString()
        self.assertThat(
            lambda: _s._raise_if_not_single_result(
                [],
                criteria_string
            ),
            raises(
                ProcessSearchError(
                    "Search criteria (%s) returned no results"
                    % criteria_string
                )
            )
        )

    def test_raise_if_not_single_result_raises_on_many_connections(self):
        criteria_string = self.getUniqueString()
        self.assertThat(
            lambda: _s._raise_if_not_single_result(
                [1, 2, 3, 4, 5],
                criteria_string
            ),
            raises(
                RuntimeError(
                    "Search criteria (%s) returned multiple results"
                    % criteria_string
                )
            )
        )

    def test_raise_if_not_single_result_doesnt_raise_with_single_result(self):
        _s._raise_if_not_single_result([1], "")

    class FMCTest:
        def list_names(self):
            return ["conn1"]

    def test_find_matching_connections_calls_connection_matcher(self):
        bus = ProxyObjectTests.FMCTest()
        connection_matcher = Mock(return_value=False)

        with sleep.mocked():
            _s._find_matching_connections(bus, connection_matcher)

        connection_matcher.assert_called_with((bus, "conn1"))

    def test_find_matching_connections_attempts_multiple_times(self):
        bus = ProxyObjectTests.FMCTest()
        connection_matcher = Mock(return_value=False)

        with sleep.mocked():
            _s._find_matching_connections(bus, connection_matcher)

        connection_matcher.assert_called_with((bus, "conn1"))
        self.assertEqual(connection_matcher.call_count, 11)

    def test_find_matching_connections_dedupes_results_on_pid(self):
        bus = ProxyObjectTests.FMCTest()

        with patch.object(_s, '_dedupe_connections_on_pid') as dedupe:
            with sleep.mocked():
                _s._find_matching_connections(bus, lambda *args: True)

                dedupe.assert_called_once_with(["conn1"], bus)


class ActualBaseClassTests(TestCase):

    def test_dont_raise_passed_base_when_is_only_base(self):
        class ActualBase(CustomEmulatorBase):
            pass

        try:
            _s._raise_if_base_class_not_actually_base(ActualBase)
        except ValueError:
            self.fail('Unexpected ValueError exception')

    def test_raises_if_passed_incorrect_base_class(self):
        class ActualBase(CustomEmulatorBase):
            pass

        class InheritedCPO(ActualBase):
            pass

        self.assertRaises(
            ValueError,
            _s._raise_if_base_class_not_actually_base,
            InheritedCPO
        )

    def test_raises_parent_with_simple_non_ap_multi_inheritance(self):
        """When mixing in non-customproxy classes must return the base."""

        class ActualBase(CustomEmulatorBase):
            pass

        class InheritedCPO(ActualBase):
            pass

        class TrickyOne(object):
            pass

        class FinalForm(InheritedCPO, TrickyOne):
            pass

        self.assertRaises(
            ValueError,
            _s._raise_if_base_class_not_actually_base,
            FinalForm
        )

    def test_raises_parent_with_non_ap_multi_inheritance(self):

        class ActualBase(CustomEmulatorBase):
            pass

        class InheritedCPO(ActualBase):
            pass

        class TrickyOne(object):
            pass

        class FinalForm(TrickyOne, InheritedCPO):
            pass

        self.assertRaises(
            ValueError,
            _s._raise_if_base_class_not_actually_base,
            FinalForm
        )

    def test_dont_raise_when_using_default_emulator_base(self):
        # _make_proxy_object potentially creates a default base.
        DefaultBase = _s._make_default_emulator_base()
        try:
            _s._raise_if_base_class_not_actually_base(DefaultBase)
        except ValueError:
            self.fail('Unexpected ValueError exception')

    def test_exception_message_contains_useful_information(self):
        class ActualBase(CustomEmulatorBase):
            pass

        class InheritedCPO(ActualBase):
            pass

        try:
            _s._raise_if_base_class_not_actually_base(InheritedCPO)
        except ValueError as err:
            self.assertEqual(
                str(err),
                _s.WRONG_CPO_CLASS_MSG.format(
                    passed=InheritedCPO,
                    actual=ActualBase
                )
            )
