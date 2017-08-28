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


"""Private module for wrapping Gdk/GdkX11 import workarounds.

The Gtk/Gdk/GdkX11 gi.repository bindings have an issue where importing Gdk,
running a Gdk method (specifically get_default_root_window) and then importing
GdkX11 will cause a different API to be loaded than if one had imported both
Gdk and GdkX11 at the same time.

This is captured in this bug:
https://bugs.launchpad.net/ubuntu/+source/gtk+3.0/+bug/1343069

To work around this we ensure that all the modules are loaded once at the same
time. This ensures that the call to _import_gdk will still import GdkX11 before
any Gdk calls are made.

"""

from autopilot.utilities import Silence


_Gtk = None
_Gdk = None
_GdkX11 = None


# Need to make sure that both modules are imported at the same time to stop any
# API changes happening under the covers.
def _import_gdk_modules():
    global _Gtk
    global _Gdk
    global _GdkX11
    version = '3.0'
    with Silence():
        from gi import require_version
        require_version('Gdk', version)
        require_version('GdkX11', version)
        require_version('Gtk', version)
        from gi.repository import Gtk, Gdk, GdkX11

        _Gtk = Gtk
        _Gdk = Gdk
        _GdkX11 = GdkX11


def _import_gtk():
    global _Gtk
    if _Gtk is None:
        _import_gdk_modules()
    return _Gtk


def _import_gdk():
    global _Gdk
    if _Gdk is None:
        _import_gdk_modules()
    return _Gdk


def _import_gdkx11():
    global _GdkX11
    if _GdkX11 is None:
        _import_gdk_modules()
    return _GdkX11
