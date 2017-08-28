# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2014, 2015 Canonical
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

"""Object registry.

This is an internal module, and is not supposed to be used directly.

This module contains the object registry, which keeps track to the various
classes we use when creating proxy classes. The object registry allows test
authors to write their own classes to be used instead of the generic one that
autopilot creates.

This module contains two global dictionaries, both are keys by unique
connection id's (UUID objects). The values are described below.

* ``_object_registry`` contains dictionaries of class names (as strings)
  to class objects. Custom proxy classes defined by test authors will end up
  with their class object in this dictionary. This is used when we want to
  create a proxy instance - if nothing matches in this dictionary then we
  create a generic proxy instance instead.

* ``_proxy_extensions`` contains a tuple of extension classes to mix in to
   *every proxy class*. This is used to extend the proxy API on a
   per-connection basis. For example, Qt-based apps allow us to monitor
   signals and slots in the application, but Gtk apps do not.

"""

from uuid import uuid4

from autopilot.introspection._xpathselect import get_classname_from_path
from autopilot.utilities import get_debug_logger
from contextlib import contextmanager

_object_registry = {}
_proxy_extensions = {}


def register_extension_classes_for_proxy_base(proxy_base, extensions):
    global _proxy_extensions
    _proxy_extensions[proxy_base._id] = (proxy_base,) + extensions


def _get_proxy_bases_for_id(id):
    global _proxy_extensions
    return _proxy_extensions.get(id, ())


class IntrospectableObjectMetaclass(type):
    """Metaclass to insert appropriate classes into the object registry."""

    def __new__(cls, classname, bases, classdict):
        """Create a new proxy class, possibly adding it to the object registry.

        Test authors may derive a class from DBusIntrospectionObject or the
        CustomEmulatorBase alias and use this as their 'emulator base'. This
        class will be given a unique '_id' attribute. That attribute is the
        first level index into the object registry. It's used so we can have
        custom proxy classes for more than one process at the same time and
        avoid clashes in the dictionary.
        """
        cls_id = None

        for base in bases:
            if hasattr(base, '_id'):
                cls_id = base._id
                break
        else:
            # Ignore classes that are in the autopilot class heirarchy:
            if classname not in (
                'ApplicationProxyObject',
                'CustomEmulatorBase',
                'DBusIntrospectionObject',
                'DBusIntrospectionObjectBase',
            ):
                # Add the '_id' attribute as a class attr:
                cls_id = classdict['_id'] = uuid4()

        # use the bases passed to us, but extend it with whatever is stored in
        # the proxy_extensions dictionary.
        extensions = _get_proxy_bases_for_id(cls_id)
        for extension in extensions:
            if extension not in bases:
                bases += (extension,)
        # make the object. Nothing special here.
        class_object = type.__new__(cls, classname, bases, classdict)

        if not classdict.get('__generated', False):
            # If the newly made object has an id, add it to the object
            # registry.
            if getattr(class_object, '_id', None) is not None:
                if class_object._id in _object_registry:
                    _object_registry[class_object._id][classname] = \
                        class_object
                else:
                    _object_registry[class_object._id] = \
                        {classname: class_object}
        # in all cases, return the class unchanged.
        return class_object


DBusIntrospectionObjectBase = IntrospectableObjectMetaclass(
    'DBusIntrospectionObjectBase',
    (object,),
    {}
)


def _get_proxy_object_class(object_id, path, state):
    """Return a custom proxy class, from the object registry or the default.

    This function first inspects the object registry using the object_id passed
    in. The object_id will be unique to all custom proxy classes for the same
    application.

    If that fails, we create a class on the fly based on the default class.

    :param object_id: The _id attribute of the class doing the lookup. This is
        used to index into the object registry to retrieve the dict of proxy
        classes to try.
    :param path: dbus path
    :param state: dbus state
    :returns: appropriate custom proxy class
    :raises ValueError: if more than one class in the dict matches

    """
    class_type = _try_custom_proxy_classes(object_id, path, state)

    return class_type or _get_default_proxy_class(
        object_id,
        get_classname_from_path(path)
    )


def _try_custom_proxy_classes(object_id, path, state):
    """Identify which custom proxy class matches the dbus path and state.

    If more than one class in proxy_class_dict matches, raise an exception.

    :param object_id: id to use to get the dict of proxy classes to  try
    :param path: dbus path
    :param state: dbus state dict
    :returns: matching custom proxy class
    :raises ValueError: if more than one class matches

    """
    proxy_class_dict = _object_registry[object_id]
    possible_classes = [c for c in proxy_class_dict.values() if
                        c.validate_dbus_object(path, state)]
    if len(possible_classes) > 1:
        raise ValueError(
            'More than one custom proxy class matches this object: '
            'Matching classes are: %s. State is %s.  Path is %s.' % (
                ','.join([repr(c) for c in possible_classes]),
                repr(state),
                path,
            )
        )
    if len(possible_classes) == 1:
        extended_proxy_bases = _get_proxy_bases_for_id(object_id)
        mixed = _combine_base_and_extensions(
            possible_classes[0],
            extended_proxy_bases
        )
        possible_classes[0].__bases__ = mixed
        return possible_classes[0]
    return None


def _combine_base_and_extensions(kls, extensions):
    """Returns the bases of the given class augmented with extensions

    In order to get the right bases tuple, the given class is removed
    from the result (to prevent cyclic dependencies), there's only one
    occurrence of each final base class in the result and the result
    is ordered following the inheritance order (classes lower in the
    inheritance tree are listed before in the resulting tuple)

    :param kls: class for which we are combining bases and extensions
    :param extensions: tuple of extensions to be added to kls' bases
    :returns: bases tuple for kls, including its former bases and the
             extensions

    """
    # set of bases + extensions removing the original class to prevent
    # TypeError: a __bases__ item causes an inheritance cycle
    unique_bases = {x for x in kls.__bases__ + extensions if x != kls}

    # sort them taking into account inheritance to prevent
    # TypeError: Cannot create a consistent method resolution order (MRO)
    return tuple(
        sorted(
            unique_bases,
            key=lambda cls: _get_mro_sort_order(cls, extensions),
            reverse=True
        )
    )


def _get_mro_sort_order(cls, promoted_collection=()):
    """Returns the comparable numerical order for the given class honouring
    its MRO

    It accepts an optional parameter for promoting classes in a certain
    group, this can give more control over the sorting when two classes
    have the a MRO of the same length

    :param cls: the subject class
    :param promoted_collection: tuple of classes which must be promoted
    :returns: comparable numerical order, higher for classes with MROs of
        greater length

    """
    # Multiplying by 2 the lenght of the MRO list gives the chance to promote
    # items in the promoted_collection by adding them 1 later: non promoted
    # classes will have even scores and promoted classes with MRO of the same
    # length will have odd scores one point higher
    order = 2 * len(cls.mro())

    if cls in promoted_collection:
        order += 1

    return order


def _get_default_proxy_class(id, name):
    """Return a custom proxy object class of the default or a base class.

    We want the object to inherit from the class that is set as the emulator
    base class, not the class that is doing the selecting. Using the passed id
    we retrieve the relevant bases from the object registry.

    :param id: The object id (_id attribute) of the class doing the lookup.
    :param name: name of new class
    :returns: custom proxy object class

    """
    get_debug_logger().warning(
        "Generating introspection instance for type '%s' based on generic "
        "class.", name)
    if isinstance(name, bytes):
        name = name.decode('utf-8')
    return type(name, _get_proxy_bases_for_id(id), dict(__generated=True))


@contextmanager
def patch_registry(new_registry):
    """A utility context manager that allows us to patch the object registry.

    Within the scope of the context manager, the object registry will be set
    to the 'new_registry' value passed in. When the scope exits, the old object
    registry will be restored.

    """
    global _object_registry
    old_registry = _object_registry
    _object_registry = new_registry
    try:
        yield
    except Exception:
        raise
    finally:
        _object_registry = old_registry
