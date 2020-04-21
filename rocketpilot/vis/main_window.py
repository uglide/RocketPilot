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


import logging

from PyQt5 import QtGui, QtCore, QtWidgets

from rocketpilot.exceptions import StateNotFoundError
from rocketpilot.introspection.qt import QtObjectProxyMixin
from rocketpilot.vis.objectproperties import TreeNodeDetailWidget

_logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, dbus_bus):
        super(MainWindow, self).__init__()
        self.selectable_interfaces = {}
        self.initUI()
        self.readSettings()
        self._dbus_bus = dbus_bus
        self.proxy_object = None

    def readSettings(self):
        settings = QtCore.QSettings()
        geometry = settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry.data())
        window_state = settings.value("windowState")
        if window_state is not None:
            self.restoreState(window_state.data())
        try:
            self.toggle_overlay_action.setChecked(
                settings.value("overlayChecked", object_type="bool")
            )
        except TypeError:
            pass
            # raised when returned QVariant is invalid - probably on
            # first boot

    def closeEvent(self, event):
        settings = QtCore.QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue(
            "overlayChecked",
            self.toggle_overlay_action.isChecked()
        )
        self.visual_indicator.close()

    def initUI(self):
        self.setWindowTitle("RocketPilot Introspection Tool")
        self.statusBar().showMessage('Waiting for rocketpilot-driver at name.glide.rocketpilot')

        self.splitter = QtWidgets.QSplitter(self)
        self.splitter.setChildrenCollapsible(False)
        self.tree_view = ProxyObjectTreeViewWidget(self.splitter)
        self.detail_widget = TreeNodeDetailWidget(self.splitter)

        self.splitter.setStretchFactor(0, 2)
        self.splitter.setStretchFactor(1, 100)
        self.setCentralWidget(self.splitter)

        self.connection_list = ConnectionList()
        self.connection_list.currentIndexChanged.connect(
            self.conn_list_activated
        )

        self.toolbar = self.addToolBar('Connection')
        self.toolbar.setObjectName('Connection Toolbar')
        self.toolbar.addWidget(self.connection_list)
        self.toolbar.addSeparator()

        self.filter_widget = FilterPane()
        self.filter_widget.apply_filter.connect(self.on_filter)
        self.filter_widget.reset_filter.connect(self.on_reset_filter)
        self.filter_widget.set_enabled(False)

        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.filter_widget)
        self.toggle_dock_widget_action = self.filter_widget.toggleViewAction()
        self.toggle_dock_widget_action.setText('Show/Hide Filter Pane')
        self.toolbar.addAction(self.toggle_dock_widget_action)

        self.visual_indicator = VisualComponentPositionIndicator()
        self.toggle_overlay_action = self.toolbar.addAction(
            "Enable/Disable component overlay"
        )
        self.toggle_overlay_action.setCheckable(True)
        self.toggle_overlay_action.toggled.connect(
            self.visual_indicator.setEnabled
        )
        # our model object gets created later.
        self.tree_model = None

    def on_filter(self, attr_name, attr_value, filters):
        attr_value = str(attr_value)

        filter = {attr_name: attr_value}

        if self.proxy_object:
            self.proxy_object.refresh_state()
            p = self.proxy_object.select_many(**filter)
            self.tree_model.set_tree_roots(p)
            self.tree_view.set_filtered(True)
        # applying the filter will always invalidate the current overlay
        self.visual_indicator.tree_node_changed(None)

    def on_reset_filter(self):
        self.tree_model.set_tree_roots([self.proxy_object])
        self.tree_view.set_filtered(False)
        # resetting the filter will always invalidate the current overlay
        self.visual_indicator.tree_node_changed(None)

    def on_proxy_object_built(self, proxy_object):
        cls_name = proxy_object.__class__.__name__
        if cls_name not in self.selectable_interfaces:
            self.selectable_interfaces[cls_name] = proxy_object
            self.update_selectable_interfaces()
        self.statusBar().clearMessage()

    def on_dbus_error(*args):
        print(args)

    def update_selectable_interfaces(self):
        self.connection_list.clear()
        self.connection_list.addItem("Please select a connection", None)
        for name, proxy_obj in self.selectable_interfaces.items():
            if isinstance(proxy_obj, QtObjectProxyMixin):
                self.connection_list.addItem(
                    name,
                    proxy_obj
                )
            else:
                self.connection_list.addItem(name, proxy_obj)

        prev_selected = 1 if self.connection_list.count() == 2 else 0

        self.connection_list.setCurrentIndex(prev_selected)

    def conn_list_activated(self, index):
        proxy_object = self.connection_list.itemData(index)
        self.proxy_object = proxy_object
        if self.proxy_object:
            self.filter_widget.set_enabled(True)
            self.tree_model = VisTreeModel(self.proxy_object)
            self.tree_view.set_model(self.tree_model)
            self.tree_view.selection_changed.connect(self.tree_item_changed)
        else:
            self.filter_widget.set_enabled(False)
            self.tree_view.set_model(None)
            self.visual_indicator.tree_node_changed(None)
            self.detail_widget.tree_node_changed(None)

    def tree_item_changed(self, current, previous):
        tree_node = current.internalPointer()
        proxy = tree_node.dbus_object if tree_node is not None else None
        self.detail_widget.tree_node_changed(proxy)
        self.visual_indicator.tree_node_changed(proxy)


class VisualComponentPositionIndicator(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(VisualComponentPositionIndicator, self).__init__(None)
        self.setWindowFlags(
            QtCore.Qt.Window |
            QtCore.Qt.X11BypassWindowManagerHint |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setStyleSheet(
            """\
            QWidget {
                background-color: rgba(253, 255, 225, 128);
            }
            """
        )
        self.enabled = False
        self.proxy = None

    def tree_node_changed(self, proxy):
        self.proxy = proxy
        self._maybe_update()

    def paintEvent(self, paint_evt):
        opt = QtWidgets.QStyleOption()
        opt.initFrom(self)
        p = QtGui.QPainter(self)
        self.style().drawPrimitive(
            QtWidgets.QStyle.PE_Widget,
            opt,
            p,
            self
        )

    def setEnabled(self, enabled):
        self.enabled = enabled
        self._maybe_update()

    def _maybe_update(self):
        """Maybe update the visual overlay.

        Several things need to be taken into account:

        1. The state of the UI toggle button, which determines whether the
           user expects us to be visible or not. Stored in 'self.enabled'
        2. The current proxy object set, and whether it has a 'globalRect'
           attribute (stored in self.proxy) - the proxy object may be None as
           well.

        """

        position = getattr(self.proxy, 'globalRect', None)
        should_be_visible = self.enabled and (position is not None)

        if should_be_visible:
            self.setGeometry(*position)
        if should_be_visible != self.isVisible():
            self.setVisible(should_be_visible)


class ProxyObjectTreeView(QtWidgets.QTreeView):

    """A subclass of QTreeView with a few customisations."""

    def __init__(self, parent=None):
        super(ProxyObjectTreeView, self).__init__(parent)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.header().setStretchLastSection(False)

    def scrollTo(self, index, hint=QtWidgets.QAbstractItemView.EnsureVisible):
        """Scroll the view to make the node at index visible.

        Overriden to stop autoScroll from horizontally jumping when selecting
        nodes, and to make arrow navigation work correctly when scrolling off
        the bottom of the viewport.

        :param index: The node to be made visible.
        :param hint: Where the visible item should be - this is ignored.
        """
        # calculate the visual rect of the item we're scrolling to in viewport
        # coordinates. The default implementation gives us a rect that ends
        # in the RHS of the viewport, which isn't what we want. We use a
        # QFontMetrics instance to calculate the probably width of the text
        # beign rendered. This may not be totally accurate, but it seems good
        # enough.
        visual_rect = self.visualRect(index)
        fm = self.fontMetrics()
        text_width = fm.width(index.data())
        visual_rect.setRight(visual_rect.left() + text_width)

        # horizontal scrolling is done per-pixel, with the scrollbar value
        # being the number of pixels past the RHS of the VP. For some reason
        # one needs to add 8 pixels - possibly this is for the tree expansion
        # widget?
        hbar = self.horizontalScrollBar()
        if visual_rect.right() + 8 > self.viewport().width():
            offset = (visual_rect.right() -
                      self.viewport().width() +
                      hbar.value() + 8)
            hbar.setValue(offset)
        if visual_rect.left() < 0:
            offset = hbar.value() + visual_rect.left() - 8
            hbar.setValue(offset)

        # Vertical scrollbar scrolls in steps equal to the height of each item
        vbar = self.verticalScrollBar()
        if visual_rect.bottom() > self.viewport().height():
            offset_pixels = (visual_rect.bottom() -
                             self.viewport().height() +
                             vbar.value())
            new_position = max(
                offset_pixels / visual_rect.height(),
                1
            ) + vbar.value()
            vbar.setValue(new_position)
        if visual_rect.top() < 0:
            new_position = min(visual_rect.top() / visual_rect.height(), -1)
            vbar.setValue(vbar.value() + new_position)


class ProxyObjectTreeViewWidget(QtWidgets.QWidget):
    """A Widget that contains a tree view and a few other things."""

    selection_changed = QtCore.pyqtSignal('QModelIndex', 'QModelIndex')

    def __init__(self, parent=None):
        super(ProxyObjectTreeViewWidget, self).__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        self.tree_view = ProxyObjectTreeView()

        layout.addWidget(self.tree_view)

        self.status_label = QtWidgets.QLabel("Showing Filtered Results ONLY")
        self.status_label.hide()
        layout.addWidget(self.status_label)
        self.setLayout(layout)

    def set_model(self, model):
        self.tree_view.setModel(model)
        self.tree_view.selectionModel().currentChanged.connect(
            self.selection_changed
        )
        self.set_filtered(False)
        self.tree_view.setColumnWidth(0, 500)

    def set_filtered(self, is_filtered):
        if is_filtered:
            self.status_label.show()
            self.tree_view.setStyleSheet("""\
                QTreeView {
                    background-color: #fdffe1;
                }
            """)
        else:
            self.status_label.hide()
            self.tree_view.setStyleSheet("")


class ConnectionList(QtWidgets.QComboBox):
    """Used to show a list of applications we can connect to."""

    def __init__(self):
        super(ConnectionList, self).__init__()
        self.setObjectName("ConnectionList")
        self.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)

    @QtCore.pyqtSlot(str)
    def trySetSelectedItem(self, desired_text):
        index = self.findText(desired_text)
        if index != -1:
            self.setCurrentIndex(index)


class TreeNode(object):
    """Used to represent the tree data structure that is the backend of the
    treeview.

    Lazy loads a nodes children instead of waiting to load and store a static
    snapshot of the apps whole state.

    """
    def __init__(self, parent=None, dbus_object=None):
        self.parent = parent
        self.name = dbus_object.__class__.__name__
        self.dbus_object = dbus_object
        self._children = None

    @property
    def children(self):
        if self._children is None:
            self._children = []
            try:
                for child in self.dbus_object.get_children():
                    self._children.append(TreeNode(self, child))
            except StateNotFoundError:
                pass
        return self._children

    @property
    def num_children(self):
        """An optimisation that allows us to get the number of children without
        actually retrieving them all. This is useful since Qt needs to know if
        there are children (to draw the drop-down triangle thingie), but
        doesn't need to know about the details.

        """
        # Thomi - 2014-04-09 - the code below is subtly broken because
        # libautopilot-qt returns items in the Children property that it never
        # exports. I'm reverting this optimisation and doing the simple thing
        # until that gets fixed.
        # https://bugs.launchpad.net/autopilot-qt/+bug/1286985
        return len(self.children)
        # old code - re-enable once above bug has been fixed.
        num_children = 0
        with self.dbus_object.no_automatic_refreshing():
            if hasattr(self.dbus_object, 'Children'):
                num_children = len(self.dbus_object.Children)
        return num_children


class VisTreeModel(QtCore.QAbstractItemModel):

    def __init__(self, proxy_object):
        """Create a new proxy object tree model.

        :param proxy_object: A DBus proxy object representing the root of the
            tree to show.

        """
        super(VisTreeModel, self).__init__()
        self.tree_roots = [
            TreeNode(dbus_object=proxy_object),
        ]

    def set_tree_roots(self, new_tree_roots):
        """Call this method to change the root nodes the model shows.

        :param new_tree_roots: An iterable of dbus proxy objects, each one will
            be a root node in the model after calling this method.

        """
        self.beginResetModel()
        self.tree_roots = [TreeNode(dbus_object=r) for r in new_tree_roots]
        self.endResetModel()

    def index(self, row, col, parent):
        if not self.hasIndex(row, col, parent):
            return QtCore.QModelIndex()

        # If there's no parent, return the root of our tree:
        if not parent.isValid():
            if row < len(self.tree_roots):
                return self.createIndex(row, col, self.tree_roots[row])
            else:
                return QtCore.QModelIndex()
        else:
            parentItem = parent.internalPointer()

        try:
            childItem = parentItem.children[row]
            return self.createIndex(row, col, childItem)
        except IndexError:
            return QtCore.QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()

        childItem = index.internalPointer()
        if not childItem:
            return QtCore.QModelIndex()

        parentItem = childItem.parent

        if parentItem is None:
            return QtCore.QModelIndex()

        row = parentItem.children.index(childItem)
        return self.createIndex(row, 0, parentItem)

    def rowCount(self, parent):
        if not parent.isValid():
            return len(self.tree_roots)
        else:
            return parent.internalPointer().num_children

    def columnCount(self, parent):
        return 1

    def data(self, index, role):
        if not index.isValid():
            return None
        if role == QtCore.Qt.DisplayRole:
            return index.internalPointer().name

    def headerData(self, column, orientation, role):
        if (orientation == QtCore.Qt.Horizontal and
                role == QtCore.Qt.DisplayRole):
                return "Tree Node"

        return None


class FilterPane(QtWidgets.QDockWidget):

    """A widget that provides a filter UI."""

    apply_filter = QtCore.pyqtSignal(str, str, list)
    reset_filter = QtCore.pyqtSignal()

    class ControlWidget(QtWidgets.QWidget):

        def __init__(self, parent=None):
            super(FilterPane.ControlWidget, self).__init__(parent)
            self._layout = QtWidgets.QFormLayout(self)

            self.node_name_edit = QtWidgets.QLineEdit()
            self.node_value_edit = QtWidgets.QLineEdit()

            self._layout.addRow(
                QtWidgets.QLabel("Property name & value:"),
            )
            self._layout.addRow(
                self.node_name_edit,
                self.node_value_edit,
            )

            btn_box = QtWidgets.QDialogButtonBox()
            self.apply_btn = btn_box.addButton(QtWidgets.QDialogButtonBox.Apply)
            self.apply_btn.setDefault(True)
            self.reset_btn = btn_box.addButton(QtWidgets.QDialogButtonBox.Reset)
            self._layout.addRow(btn_box)

            self.setLayout(self._layout)

    def __init__(self, parent=None):
        super(FilterPane, self).__init__("Filter Tree", parent)
        self.setObjectName("FilterTreePane")
        self.control_widget = FilterPane.ControlWidget(self)

        self.control_widget.node_name_edit.returnPressed.connect(
            self.on_apply_clicked
        )
        self.control_widget.apply_btn.clicked.connect(self.on_apply_clicked)
        self.control_widget.reset_btn.clicked.connect(self.reset_filter)

        self.setWidget(self.control_widget)

    def on_apply_clicked(self):
        node_name = self.control_widget.node_name_edit.text()
        node_value = self.control_widget.node_value_edit.text()
        self.apply_filter.emit(node_name, node_value, [])

    def set_enabled(self, enabled):
        self.control_widget.setEnabled(enabled)
