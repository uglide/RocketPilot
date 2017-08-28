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


"""Utility functions to get shortcut keybindings for various parts of Unity.

Inside Autopilot we deal with keybindings by naming them with unique names. For
example, instead of hard-coding the fact that 'Alt+F2' opens the command lens,
we might call:

>>> keybindings.get('lens_reveal/command')
'Alt+F2'

Keybindings come from two different places:
 1) Keybindings from compiz. We can get these if we have the plugin name and
    setting name.
 2) Elsewhere. Right now we're hard-coding these in a separate dictionary.
"""

import logging
import re

from autopilot.input import Keyboard
from autopilot.utilities import Silence

_logger = logging.getLogger(__name__)


#
# Fill this dictionary with keybindings we want to store.
#
# If keybindings are from compizconfig, the value should be a 2-value tuple
# containging (plugin_name, setting_name).
#
# If keybindings are elsewhere, just store the keybinding string.
_keys = {
    # Launcher:
    "launcher/reveal": ('unityshell', 'show_launcher'),
    "launcher/keynav": ('unityshell', 'keyboard_focus'),
    "launcher/keynav/next": "Down",
    "launcher/keynav/prev": "Up",
    "launcher/keynav/activate": "Enter",
    "launcher/keynav/exit": "Escape",
    "launcher/keynav/open-quicklist": "Right",
    "launcher/keynav/close-quicklist": "Left",
    "launcher/switcher": ('unityshell', 'launcher_switcher_forward'),
    "launcher/switcher/exit": "Escape",
    "launcher/switcher/next": "Tab",
    "launcher/switcher/prev": "Shift+Tab",
    "launcher/switcher/down": "Down",
    "launcher/switcher/up": "Up",
    # Quicklist:
    "quicklist/keynav/first": "Home",
    "quicklist/keynav/last": "End",
    "quicklist/keynav/next": "Down",
    "quicklist/keynav/prev": "Up",
    "quicklist/keynav/activate": "Enter",
    "quicklist/keynav/exit": "Escape",
    # Panel:
    "panel/show_menus": "Alt",
    "panel/open_first_menu": ('unityshell', 'panel_first_menu'),
    "panel/next_indicator": "Right",
    "panel/prev_indicator": "Left",
    # Dash:
    "dash/reveal": "Super",
    "dash/lens/next": "Ctrl+Tab",
    "dash/lens/prev": "Ctrl+Shift+Tab",
    # Lenses:
    "lens_reveal/command": ("unityshell", "execute_command"),
    "lens_reveal/apps": "Super+a",
    "lens_reveal/files": "Super+f",
    "lens_reveal/music": "Super+m",
    "lens_reveal/video": "Super+v",
    # Hud:
    "hud/reveal": ("unityshell", "show_hud"),
    # Switcher:
    "switcher/reveal_normal": ("unityshell", "alt_tab_forward"),
    "switcher/reveal_impropper": "Alt+Right",
    "switcher/reveal_details": "Alt+`",
    "switcher/reveal_all": ("unityshell", "alt_tab_forward_all"),
    "switcher/cancel": "Escape",
    # Shortcut Hint:
    "shortcuthint/reveal": ('unityshell', 'show_launcher'),
    "shortcuthint/cancel": "Escape",
    # These are in compiz as 'Alt+Right' and 'Alt+Left', but the fact that it
    # lists the Alt key won't work for us, so I'm defining them manually.
    "switcher/next": "Tab",
    "switcher/prev": "Shift+Tab",
    "switcher/right": "Right",
    "switcher/left": "Left",
    "switcher/detail_start": "Down",
    "switcher/detail_stop": "Up",
    "switcher/detail_next": "`",
    "switcher/detail_prev": "`",
    # Workspace switcher (wall):
    "workspace/move_left": ("wall", "left_key"),
    "workspace/move_right": ("wall", "right_key"),
    "workspace/move_up": ("wall", "up_key"),
    "workspace/move_down": ("wall", "down_key"),
    # Window management:
    "window/show_desktop": ("unityshell", "show_desktop_key"),
    "window/minimize": ("core", "minimize_window_key"),
    "window/maximize": ("core", "maximize_window_key"),
    "window/left_maximize": ("unityshell", "window_left_maximize"),
    "window/right_maximize": ("unityshell", "window_right_maximize"),
    "window/restore": ("core", "unmaximize_or_minimize_window_key"),
    "window/close": ("core", "close_window_key"),
    # expo plugin:
    "expo/start": ("expo", "expo_key"),
    "expo/cancel": "Escape",
    # spread (scale) plugin:
    "spread/start": ("scale", "initiate_key"),
    "spread/cancel": "Escape",
}


def get(binding_name):
    """Get a keybinding, given its well-known name.

    :param string binding_name:
    :raises TypeError: if binding_name is not a string
    :raises ValueError: if binding_name cannot be found in the bindings
                        dictionaries.
    :returns: string for keybinding

    """
    if not isinstance(binding_name, str):
        raise TypeError("binding_name must be a string.")
    if binding_name not in _keys:
        raise ValueError("Unknown binding name '%s'." % (binding_name))
    v = _keys[binding_name]
    if isinstance(v, str):
        return v
    else:
        return _get_compiz_keybinding(v)


def get_hold_part(binding_name):
    """Return the part of a keybinding that must be held permanently.

    Use this function to split bindings like "Alt+Tab" into the part that must
    be held down. See :meth:`get_tap_part` for the part that must be tapped.

    :raises ValueError: if the binding specified does not have multiple
     parts.

    """
    binding = get(binding_name)
    parts = binding.split('+')
    if len(parts) == 1:
        _logger.warning(
            "Key binding '%s' does not have a hold part.", binding_name)
        return parts[0]
    return '+'.join(parts[:-1])


def get_tap_part(binding_name):
    """Return the part of a keybinding that must be tapped.

    Use this function to split bindings like "Alt+Tab" into the part that must
    be held tapped. See :meth:`get_hold_part` for the part that must be held
    down.

    :raises ValueError: if the binding specified does not have multiple
     parts.

    """
    binding = get(binding_name)
    parts = binding.split('+')
    if len(parts) == 1:
        _logger.warning(
            "Key binding '%s' does not have a tap part.", binding_name)
        return parts[0]
    return parts[-1]


def _get_compiz_keybinding(compiz_tuple):
    """Given a keybinding name, get the keybinding string from the compiz
    option.

    :raises ValueError: if the compiz setting described does not hold a
     keybinding.
    :raises RuntimeError: if the compiz keybinding has been disabled.
    :returns: compiz keybinding

    """
    plugin_name, setting_name = compiz_tuple
    plugin = _get_compiz_plugin(plugin_name)
    setting = _get_compiz_setting(plugin_name, setting_name)
    if setting.Type != 'Key':
        raise ValueError(
            "Key binding maps to a compiz option that does not hold a "
            "keybinding.")
    if not plugin.Enabled:
        _logger.warning(
            "Returning keybinding for '%s' which is in un-enabled plugin '%s'",
            setting.ShortDesc,
            plugin.ShortDesc)
    if setting.Value == "Disabled":
        raise RuntimeError(
            "Keybinding '%s' in compiz plugin '%s' has been disabled." %
            (setting.ShortDesc, plugin.ShortDesc))

    return _translate_compiz_keystroke_string(setting.Value)


def _translate_compiz_keystroke_string(keystroke_string):
    """Get a string representing the keystroke stored in *keystroke_string*.

    The returned value is suitable for passing into the Keyboard emulator.

    :param string keystroke_string: A compizconfig-style keystroke string.

    """
    if not isinstance(keystroke_string, str):
        raise TypeError("keystroke string must be a string.")

    translations = {
        'Control': 'Ctrl',
        'Primary': 'Ctrl',
    }
    regex = re.compile('[<>]')
    parts = regex.split(keystroke_string)
    result = []
    for part in parts:
        part = part.strip()
        if part != "" and not part.isspace():
            translated = translations.get(part, part)
            if translated not in result:
                result.append(translated)

    return '+'.join(result)


class KeybindingsHelper(object):

    """A helper class that makes it easier to use Unity keybindings."""

    @property
    def _keyboard(self):
        return Keyboard.create()

    def keybinding(self, binding_name, delay=None):
        """Press and release the keybinding with the given name.

        If set, the delay parameter will override the default delay set by the
        keyboard emulator.

        """
        if delay is not None and type(delay) != float:
            raise TypeError(
                "delay parameter must be a float if it is defined.")
        if delay:
            self._keyboard.press_and_release(get(binding_name), delay)
        else:
            self._keyboard.press_and_release(get(binding_name))

    def keybinding_hold(self, binding_name):
        """Hold down the hold-part of a keybinding."""
        self._keyboard.press(get_hold_part(binding_name))

    def keybinding_release(self, binding_name):
        """Release the hold-part of a keybinding."""
        self._keyboard.release(get_hold_part(binding_name))

    def keybinding_tap(self, binding_name):
        """Tap the tap-part of a keybinding."""
        self._keyboard.press_and_release(get_tap_part(binding_name))

    def keybinding_hold_part_then_tap(self, binding_name):
        self.keybinding_hold(binding_name)
        self.keybinding_tap(binding_name)


# Functions that wrap compizconfig to avoid some unpleasantness in that module.
# Local to the this keybindings for now until their removal in the very near
# future.
_global_compiz_context = None


def _get_global_compiz_context():
    """Get the compizconfig global context object.

    :returns: global compiz context, either already defined or from compiz
              config

    """
    global _global_compiz_context
    if _global_compiz_context is None:
        with Silence():
            from compizconfig import Context
            _global_compiz_context = Context()
    return _global_compiz_context


def _get_compiz_plugin(plugin_name):
    """Get a compizconfig plugin with the specified name.

    :raises KeyError: if the plugin named does not exist.
    :returns: compizconfig plugin

    """
    ctx = _get_global_compiz_context()
    with Silence():
        try:
            return ctx.Plugins[plugin_name]
        except KeyError:
            raise KeyError(
                "Compiz plugin '%s' does not exist." % (plugin_name))


def _get_compiz_setting(plugin_name, setting_name):
    """Get a compizconfig setting object, given a plugin name and setting name.

    :raises KeyError: if the plugin or setting is not found.
    :returns: compiz setting object

    """
    plugin = _get_compiz_plugin(plugin_name)
    with Silence():
        try:
            return plugin.Screen[setting_name]
        except KeyError:
            raise KeyError(
                "Compiz setting '%s' does not exist in plugin '%s'." %
                (setting_name, plugin_name))
