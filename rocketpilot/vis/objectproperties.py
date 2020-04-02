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


"""Code for introspection tree object properties."""

import dbus
from PyQt5 import QtGui, QtCore, QtWidgets


from rocketpilot.introspection.qt import QtObjectProxyMixin


__all__ = ['TreeNodeDetailWidget']


def dbus_string_rep(dbus_type):
    """Get a string representation of various dbus types."""
    if isinstance(dbus_type, dbus.Boolean):
        return repr(bool(dbus_type))
    if isinstance(dbus_type, dbus.String):
        return dbus_type.encode('utf-8', errors='ignore').decode('utf-8')
    if (isinstance(dbus_type, dbus.Int16) or
            isinstance(dbus_type, dbus.UInt16) or
            isinstance(dbus_type, dbus.Int32) or
            isinstance(dbus_type, dbus.UInt32) or
            isinstance(dbus_type, dbus.Int64) or
            isinstance(dbus_type, dbus.UInt64)):
        return repr(int(dbus_type))
    if isinstance(dbus_type, dbus.Double):
        return repr(float(dbus_type))
    if (isinstance(dbus_type, dbus.Array) or
            isinstance(dbus_type, dbus.Struct)):
        return ', '.join([dbus_string_rep(i) for i in dbus_type])
    else:
        return repr(dbus_type)


class TreeNodeDetailWidget(QtWidgets.QTabWidget):
    """A widget that shows tree node details."""

    def __init__(self, parent):
        super(TreeNodeDetailWidget, self).__init__(parent)
        self.views = []
        for view_class in ALL_VIEWS:
            view = view_class()
            self.views.append(view)

    def tree_node_changed(self, new_node):
        """Call when the selected tree node has changed.

        This method will update the available tabs to reflect those suitable
        for the new tree node selected.

        """
        for view in self.views:
            view_tab_idx = self.indexOf(view)
            if view_tab_idx == -1:
                # view is not currently shown.
                if view.is_relevant(new_node):
                    self.addTab(view, view.name())
            else:
                # view is in tab bar already.
                if not view.is_relevant(new_node):
                    self.removeTab(view_tab_idx)

        for i in range(self.count()):
            self.widget(i).new_node_selected(new_node)


class AbstractView(QtWidgets.QWidget):

    """An abstract class that outlines the methods required to be used in the
    details view widget.

    """

    def name(self):
        """Return the name of the view."""
        raise NotImplementedError(
            "This method must be implemented in subclasses!")

    def icon(self):
        """Return the icon for the view (optionsla)."""
        return QtGui.QIcon()

    def is_relevant(self, node):
        """Return true if the view can display data about this tree node."""
        raise NotImplementedError(
            "This method must be implemented in subclasses!")

    def new_node_selected(self, node):
        raise NotImplementedError(
            "This method must be implemented in subclasses!")


class PropertyView(AbstractView):

    """A view that displays the basic exported object properties in a table."""

    def __init__(self, *args, **kwargs):
        super(PropertyView, self).__init__(*args, **kwargs)

        header_titles = ["Name", "Value"]
        self.details_layout = QtWidgets.QVBoxLayout(self)

        self.table_view = QtWidgets.QTableWidget()
        self.table_view.setColumnCount(2)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setHorizontalHeaderLabels(header_titles)
        self.table_view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.details_layout.addWidget(self.table_view)

    def name(self):
        return "Properties"

    def is_relevant(self, node):
        return node is not None

    def new_node_selected(self, node):
        self.table_view.setSortingEnabled(False)
        self.table_view.clearContents()
        object_details = node.get_properties()
        # remove the Children property - we don't care about it:
        object_details.pop("Children", None)
        self.table_view.setRowCount(len(object_details))
        for i, key in enumerate(object_details):
            details_string = dbus_string_rep(object_details[key])
            item_name = QtWidgets.QTableWidgetItem(key)
            item_details = QtWidgets.QTableWidgetItem(
                details_string)
            self.table_view.setItem(i, 0, item_name)
            self.table_view.setItem(i, 1, item_details)
        self.table_view.setSortingEnabled(True)
        self.table_view.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.table_view.resizeColumnsToContents()


class SignalView(AbstractView):

    """A view that exposes signals available on an object."""

    def __init__(self, *args, **kwargs):
        super(SignalView, self).__init__(*args, **kwargs)

        self.details_layout = QtWidgets.QVBoxLayout(self)

        self.signals_table = QtWidgets.QTableWidget()
        self.signals_table.setColumnCount(1)
        self.signals_table.verticalHeader().setVisible(False)
        self.signals_table.setAlternatingRowColors(True)
        self.signals_table.setHorizontalHeaderLabels(["Signal Signature"])
        self.signals_table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers)
        self.details_layout.addWidget(self.signals_table)

    def name(self):
        return "Signals"

    def icon(self):
        return ""

    def is_relevant(self, node):
        return node is not None and isinstance(node, QtObjectProxyMixin)

    def new_node_selected(self, node):
        self.signals_table.setSortingEnabled(False)
        self.signals_table.clearContents()
        signals = node.get_signals()
        self.signals_table.setRowCount(len(signals))
        for i, signal in enumerate(signals):
            self.signals_table.setItem(
                i, 0, QtWidgets.QTableWidgetItem(str(signal)))
        self.signals_table.setSortingEnabled(True)
        self.signals_table.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.signals_table.resizeColumnsToContents()


class SlotView(AbstractView):

    """A View that exposes slots on an object."""

    def __init__(self, *args, **kwargs):
        super(SlotView, self).__init__(*args, **kwargs)

        self.details_layout = QtWidgets.QVBoxLayout(self)

        self.slots_table = QtWidgets.QTableWidget()
        self.slots_table.setColumnCount(1)
        self.slots_table.verticalHeader().setVisible(False)
        self.slots_table.setAlternatingRowColors(True)
        self.slots_table.setHorizontalHeaderLabels(["Slot Signature"])
        self.slots_table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers)
        self.details_layout.addWidget(self.slots_table)

    def name(self):
        return "Slots"

    def icon(self):
        return ""

    def is_relevant(self, node):
        return node is not None and isinstance(node, QtObjectProxyMixin)

    def new_node_selected(self, node):
        self.slots_table.setSortingEnabled(False)
        self.slots_table.clearContents()
        signals = node.get_slots()
        self.slots_table.setRowCount(len(signals))
        for i, signal in enumerate(signals):
            self.slots_table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(signal)))
        self.slots_table.setSortingEnabled(True)
        self.slots_table.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.slots_table.resizeColumnsToContents()


ALL_VIEWS = [
    PropertyView,
    SignalView,
    SlotView,
]
