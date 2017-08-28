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

import json
import logging
import os
import re
import subprocess
import tempfile
from tempfile import mktemp
from testtools import skipIf
from testtools.matchers import (
    Contains,
    Equals,
    GreaterThan,
    IsInstance,
    LessThan,
    MatchesRegex,
    Not,
    StartsWith,
)
from textwrap import dedent
from unittest.mock import patch
from io import StringIO

from autopilot import platform
from autopilot.matchers import Eventually
from autopilot.testcase import AutopilotTestCase
from autopilot.tests.functional import QmlScriptRunnerMixin
from autopilot.tests.functional.fixtures import TempDesktopFile
from autopilot.introspection import CustomEmulatorBase
from autopilot.introspection import _object_registry as object_registry
from autopilot.introspection import _search
from autopilot.introspection.qt import QtObjectProxyMixin
from autopilot.display import Display


logger = logging.getLogger(__name__)


class EmulatorBase(CustomEmulatorBase):
    pass


@skipIf(platform.model() != "Desktop", "Only suitable on Desktop (WinMocker)")
class IntrospectionFeatureTests(AutopilotTestCase):
    """Test various features of the introspection code."""

    def start_mock_app(self, emulator_base):
        window_spec_file = mktemp(suffix='.json')
        window_spec = {"Contents": "MouseTest"}
        json.dump(
            window_spec,
            open(window_spec_file, 'w')
        )
        self.addCleanup(os.remove, window_spec_file)

        return self.launch_test_application(
            'window-mocker',
            window_spec_file,
            app_type='qt',
            emulator_base=emulator_base,
        )

    def test_can_get_custom_proxy_for_app_root(self):
        """Test two things:

        1) We can get a custom proxy object for the root object in the object
           tree.

        2) We can get a custom proxy object for an object in the tree which
           contains characters which are usually disallowed in python class
           names.
        """
        class WindowMockerApp(EmulatorBase):
            @classmethod
            def validate_dbus_object(cls, path, _state):
                return path == b'/window-mocker'

        # verify that the initial proxy object we get back is the correct type:
        app = self.start_mock_app(EmulatorBase)
        self.assertThat(type(app), Equals(WindowMockerApp))

        # verify that we get the correct type from get_root_instance:
        self.assertThat(
            type(app.get_root_instance()),
            Equals(WindowMockerApp)
        )

    def test_customised_proxy_classes_have_extension_classes(self):
        class WindowMockerApp(EmulatorBase):
            @classmethod
            def validate_dbus_object(cls, path, _state):
                return path == b'/window-mocker'

        app = self.start_mock_app(EmulatorBase)
        self.assertThat(app.__class__.__bases__, Contains(QtObjectProxyMixin))

    def test_customised_proxy_classes_have_multiple_extension_classes(self):
        with object_registry.patch_registry({}):
            class SecondEmulatorBase(CustomEmulatorBase):
                pass

            class WindowMockerApp(EmulatorBase, SecondEmulatorBase):
                @classmethod
                def validate_dbus_object(cls, path, _state):
                    return path == b'/window-mocker'

            app = self.start_mock_app(EmulatorBase)
            self.assertThat(app.__class__.__bases__, Contains(EmulatorBase))
            self.assertThat(
                app.__class__.__bases__,
                Contains(SecondEmulatorBase)
            )

    def test_handles_using_app_cpo_base_class(self):
        # This test replicates an issue found in an application test suite
        # where using the App CPO caused an exception.
        with object_registry.patch_registry({}):
            class WindowMockerApp(CustomEmulatorBase):
                @classmethod
                def validate_dbus_object(cls, path, _state):
                    return path == b'/window-mocker'

            self.start_mock_app(WindowMockerApp)

    def test_warns_when_using_incorrect_cpo_base_class(self):
        # Ensure the warning method is called when launching a proxy.
        with object_registry.patch_registry({}):
            class TestCPO(CustomEmulatorBase):
                pass

            class WindowMockerApp(TestCPO):
                @classmethod
                def validate_dbus_object(cls, path, _state):
                    return path == b'/window-mocker'

            with patch.object(_search, 'logger') as p_logger:
                self.start_mock_app(WindowMockerApp)
                self.assertTrue(p_logger.warning.called)

    def test_can_select_custom_emulators_by_name(self):
        """Must be able to select a custom emulator type by name."""
        class MouseTestWidget(EmulatorBase):
            pass

        app = self.start_mock_app(EmulatorBase)
        test_widget = app.select_single('MouseTestWidget')

        self.assertThat(type(test_widget), Equals(MouseTestWidget))

    def test_can_select_custom_emulators_by_type(self):
        """Must be able to select a custom emulator type by type."""
        class MouseTestWidget(EmulatorBase):
            pass

        app = self.start_mock_app(EmulatorBase)
        test_widget = app.select_single(MouseTestWidget)

        self.assertThat(type(test_widget), Equals(MouseTestWidget))

    def test_can_access_custom_emulator_properties(self):
        """Must be able to access properties of a custom emulator."""
        class MouseTestWidget(EmulatorBase):
            pass

        app = self.start_mock_app(EmulatorBase)
        test_widget = app.select_single(MouseTestWidget)

        self.assertThat(test_widget.visible, Eventually(Equals(True)))

    def test_selecting_generic_from_custom_is_not_inherited_from_custom(self):
        """Selecting a generic proxy object from a custom proxy object must not
        return an object derived of the custom object type.

        """
        class MouseTestWidget(EmulatorBase):
            pass

        app = self.start_mock_app(EmulatorBase)
        mouse_widget = app.select_single(MouseTestWidget)

        child_label = mouse_widget.select_many("QLabel")[0]

        self.assertThat(child_label, Not(IsInstance(MouseTestWidget)))

    def test_selecting_custom_from_generic_is_not_inherited_from_generic(self):
        """Selecting a custom proxy object from a generic proxy object must
        return an object that is of the custom type.

        """
        class MouseTestWidget(EmulatorBase):
            pass

        app = self.start_mock_app(EmulatorBase)
        generic_window = app.select_single("QMainWindow")

        mouse_widget = generic_window.select_single(MouseTestWidget)

        self.assertThat(
            mouse_widget,
            Not(IsInstance(type(generic_window)))
        )

    def test_print_tree_full(self):
        """Print tree of full application"""

        app = self.start_mock_app(EmulatorBase)
        win = app.select_single("QMainWindow")

        stream = StringIO()
        win.print_tree(stream)
        out = stream.getvalue()

        # starts with root node
        self.assertThat(
            out,
            StartsWith("== /window-mocker/QMainWindow ==\nChildren:")
        )
        # has root node properties
        self.assertThat(
            out,
            MatchesRegex(
                ".*windowTitle: [u]?'Default Window Title'.*",
                re.DOTALL
            )
        )

        # has level-1 widgets with expected indent
        self.assertThat(
            out,
            Contains("  == /window-mocker/QMainWindow/QRubberBand ==\n")
        )
        self.assertThat(
            out,
            MatchesRegex(".*  objectName: [u]?'qt_rubberband'\n", re.DOTALL)
        )
        # has level-2 widgets with expected indent
        self.assertThat(
            out,
            Contains(
                "    == /window-mocker/QMainWindow/QMenuBar/QToolButton =="
            )
        )
        self.assertThat(
            out,
            MatchesRegex(
                ".*    objectName: [u]?'qt_menubar_ext_button'.*",
                re.DOTALL
            )
        )

    def test_print_tree_depth_limit(self):
        """Print depth-limited tree for a widget"""

        app = self.start_mock_app(EmulatorBase)
        win = app.select_single("QMainWindow")

        stream = StringIO()
        win.print_tree(stream, 1)
        out = stream.getvalue()

        # has level-0 (root) node
        self.assertThat(out, Contains("== /window-mocker/QMainWindow =="))
        # has level-1 widgets
        self.assertThat(out, Contains("/window-mocker/QMainWindow/QMenuBar"))
        # no level-2 widgets
        self.assertThat(out, Not(Contains(
            "/window-mocker/QMainWindow/QMenuBar/QToolButton")))

    def test_window_geometry(self):
        """Window.geometry property

        Check that all Window geometry properties work and have a plausible
        range.
        """
        # ensure we have at least one open app window
        self.start_mock_app(EmulatorBase)

        display = Display.create()
        top = left = right = bottom = None
        # for multi-monitor setups, make sure we examine the full desktop
        # space:
        for monitor in range(display.get_num_screens()):
            sx, sy, swidth, sheight = Display.create().get_screen_geometry(
                monitor
            )
            logger.info(
                "Monitor %d geometry is (%d, %d, %d, %d)",
                monitor,
                sx,
                sy,
                swidth,
                sheight,
            )
            if left is None or sx < left:
                left = sx
            if top is None or sy < top:
                top = sy
            if right is None or sx + swidth >= right:
                right = sx + swidth
            if bottom is None or sy + sheight >= bottom:
                bottom = sy + sheight

        logger.info(
            "Total desktop geometry is (%d, %d), (%d, %d)",
            left,
            top,
            right,
            bottom,
        )
        for win in self.process_manager.get_open_windows():
            logger.info("Win '%r' geometry is %r", win, win.geometry)
            geom = win.geometry
            self.assertThat(len(geom), Equals(4))
            self.assertThat(geom[0], GreaterThan(left - 1))  # no GreaterEquals
            self.assertThat(geom[1], GreaterThan(top - 1))
            self.assertThat(geom[2], LessThan(right))
            self.assertThat(geom[3], LessThan(bottom))


class QMLCustomEmulatorTestCase(AutopilotTestCase):
    """Test the introspection of a QML application with a custom emulator."""

    def test_can_access_custom_emulator_properties_twice(self):
        """Must be able to run more than one test with a custom emulator."""

        class InnerTestCase(AutopilotTestCase):
            class QQuickView(EmulatorBase):
                pass

            test_qml = dedent("""\
                import QtQuick 2.0

                Rectangle {
                }

                """)

            def launch_test_qml(self):
                arch = subprocess.check_output(
                    ["dpkg-architecture", "-qDEB_HOST_MULTIARCH"],
                    universal_newlines=True).strip()
                qml_path = tempfile.mktemp(suffix='.qml')
                open(qml_path, 'w').write(self.test_qml)
                self.addCleanup(os.remove, qml_path)

                extra_args = ''
                if platform.model() != "Desktop":
                    # We need to add the desktop-file-hint
                    desktop_file = self.useFixture(
                        TempDesktopFile()
                    ).get_desktop_file_path()
                    extra_args = '--desktop_file_hint={hint_file}'.format(
                        hint_file=desktop_file
                    )

                return self.launch_test_application(
                    "/usr/lib/" + arch + "/qt5/bin/qmlscene",
                    qml_path,
                    extra_args,
                    emulator_base=EmulatorBase)

            def test_custom_emulator(self):
                app = self.launch_test_qml()
                test_widget = app.select_single(InnerTestCase.QQuickView)
                self.assertThat(test_widget.visible, Eventually(Equals(True)))

        result1 = InnerTestCase('test_custom_emulator').run()
        self.assertThat(
            result1.wasSuccessful(),
            Equals(True),
            '\n\n'.join(
                [e[1] for e in result1.decorated.errors]
            )
        )
        result2 = InnerTestCase('test_custom_emulator').run()
        self.assertThat(
            result2.wasSuccessful(),
            Equals(True),
            '\n\n'.join(
                [e[1] for e in result2.decorated.errors]
            )
        )


class CustomCPOTest(AutopilotTestCase, QmlScriptRunnerMixin):

    def launch_simple_qml_script(self):
        simple_script = dedent("""
        import QtQuick 2.0
        Rectangle {
            objectName: "ExampleRectangle"
        }
        """)
        return self.start_qml_script(simple_script)

    def test_cpo_can_be_named_different_to_underlying_type(self):
        """A CPO with the correct name match method must be matched if the
        class name is different to the Type name.

        """
        with object_registry.patch_registry({}):
            class RandomNamedCPORectangle(CustomEmulatorBase):
                @classmethod
                def get_type_query_name(cls):
                    return 'QQuickRectangle'

            app = self.launch_simple_qml_script()
            rectangle = app.select_single(RandomNamedCPORectangle)

            self.assertThat(rectangle.objectName, Equals('ExampleRectangle'))
