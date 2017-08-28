.. _porting:

Porting Autopilot Tests
#######################

This document contains hints as to what is required to port a test suite from any version of autopilot to any newer version.

.. contents::

A note on Versions
==================

Autopilot releases are reasonably tightly coupled with Ubuntu releases. However, the autopilot authors maintain separate version numbers, with the aim of separating the autopilot release cadence from the Ubuntu platform release cadence.

Autopilot versions earlier than 1.2 were not publicly announced, and were only used within Canonical. For that reason, this document assumes that version 1.2 is the lowest version of autopilot present `"in the wild"`.

Porting to Autopilot v1.4.x
===========================

The 1.4 release contains several changes that required a break in the DBus wire protocol between autopilot and the applications under test. Most of these changes require no change to test code.

Gtk Tests and Boolean Parameters
++++++++++++++++++++++++++++++++

Version 1.3 of the autopilot-gtk backend contained `a bug <https://bugs.launchpad.net/autopilot-gtk/+bug/1214249>`_ that caused all Boolean properties to be exported as integers instead of boolean values. This in turn meant that test code would fail to return the correct objects when using selection criteria such as::

	visible_buttons = app.select_many("GtkPushButton", visible=True)

and instead had to write something like this::

	visible_buttons = app.select_many("GtkPushButton", visible=1)

This bug has now been fixed, and using the integer selection will fail.

:py:meth:`~autopilot.testcase.AutopilotTestCase.select_single` Changes
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The :meth:`~autopilot.introspection.dbus.DBusIntrospectionObject.select_single` method used to return ``None`` in the case where no object was found that matched the search criteria. This led to rather awkward code in places where the object you are searching for is being created dynamically::

	for i in range(10):
		my_obj = self.app.select_single("MyObject")
		if my_obj is not None:
			break
		time.sleep(1)
	else:
		self.fail("Object 'MyObject' was not found within 10 seconds.")

This makes the authors intent harder to discern. To improve this situation, two changes have been made:

1. :meth:`~autopilot.introspection.dbus.DBusIntrospectionObject.select_single` raises a :class:`~autopilot.introspection.dbus.StateNotFoundError` exception if the search terms returned no values, rather than returning ``None``.

2. If the object being searched for is likely to not exist, there is a new method: :meth:`~autopilot.introspection.dbus.DBusIntrospectionObject.wait_select_single` will try to retrieve an object for 10 seconds. If the object does not exist after that timeout, a :class:`~autopilot.exceptions.StateNotFoundError` exception is raised. This means that the above code example should now be written as::

	my_obj = self.app.wait_select_single("MyObject")

.. _dbus_backends:

DBus backends and :class:`~autopilot.introspection.dbus.DBusIntrospectionObject` changes
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Due to a change in how
:class:`~autopilot.introspection.dbus.DBusIntrospectionObject` objects store
their DBus backend a couple of classmethods have now become instance methods.

These affected methods are:

 * :meth:`~autopilot.introspection.dbus.DBusIntrospectionObject.get_all_instances`
 * :meth:`~autopilot.introspection.dbus.DBusIntrospectionObject.get_root_instance`
 * :meth:`~autopilot.introspection.dbus.DBusIntrospectionObject.get_state_by_path`

For example, if your old code is something along the lines of::

    all_keys = KeyCustomProxy.get_all_instances()

You will instead need to have something like this instead::

    all_keys = app_proxy.select_many(KeyCustomProxy)

.. _python3_support:

Python 3
++++++++

Starting from version 1.4, autopilot supports python 3 as well as python 2. Test authors can choose to target either version of python.

Porting to Autopilot v1.3.x
===========================

The 1.3 release included many API breaking changes. Earlier versions of autopilot made several assumptions about where tests would be run, that turned out not to be correct. Autopilot 1.3 brought several much-needed features, including:

* A system for building pluggable implementations for several core components. This system is used in several areas:

 * The input stack can now generate events using either the X11 client libraries, or the UInput kernel driver. This is necessary for devices that do not use X11.
 * The display stack can now report display information for systems that use both X11 and the mir display server.
 * The process stack can now report details regarding running processes & their windows on both Desktop, tablet, and phone platforms.

* A large code cleanup and reorganisation. In particular, lots of code that came from the Unity 3D codebase has been removed if it was deemed to not be useful to the majority of test authors. This code cleanup includes a flattening of the autopilot namespace. Previously, many useful classes lived under the ``autopilot.emulators`` namespace. These have now been moved into the ``autopilot`` namespace.


.. note:: There is an API breakage in autopilot 1.3. The changes outlined under
          the heading ":ref:`dbus_backends`" apply to version
          1.3.1+13.10.20131003.1-0ubuntu1 and onwards .

``QtIntrospectionTestMixin`` and ``GtkIntrospectionTestMixin`` no longer exist
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

In autopilot 1.2, tests enabled application introspection services by inheriting from one of two mixin classes: ``QtIntrospectionTestMixin`` to enable testing Qt4, Qt5, and Qml applications, and ``GtkIntrospectionTestMixin`` to enable testing Gtk 2 and Gtk3 applications. For example, a test case class in autopilot 1.2 might look like this::

	from autopilot.introspection.qt import QtIntrospectionTestMixin
	from autopilot.testcase import AutopilotTestCase


	class MyAppTestCase(AutopilotTestCase, QtIntrospectionTestMixin):

	    def setUp(self):
	        super(MyAppTestCase, self).setUp()
	        self.app = self.launch_test_application("../../my-app")

In Autopilot 1.3, the :class:`~autopilot.testcase.AutopilotTestCase` class contains this functionality directly, so the ``QtIntrospectionTestMixin`` and ``GtkIntrospectionTestMixin`` classes no longer exist. The above example becomes simpler::

	from autopilot.testcase import AutopilotTestCase


	class MyAppTestCase(AutopilotTestCase):

	    def setUp(self):
	        super(MyAppTestCase, self).setUp()
	        self.app = self.launch_test_application("../../my-app")

Autopilot will try and determine the introspection type automatically. If this process fails, you can specify the application type manually::

	from autopilot.testcase import AutopilotTestCase


	class MyAppTestCase(AutopilotTestCase):

	    def setUp(self):
	        super(MyAppTestCase, self).setUp()
	        self.app = self.launch_test_application("../../my-app", app_type='qt')

.. seealso::

	Method :py:meth:`autopilot.testcase.AutopilotTestCase.launch_test_application`
		Launch test applications.

``autopilot.emulators`` namespace has been deprecated
+++++++++++++++++++++++++++++++++++++++++++++++++++++

In autopilot 1.2 and earlier, the ``autopilot.emulators`` package held several modules and classes that were used frequently in tests. This package has been removed, and it's contents merged into the autopilot package. Below is a table showing the basic translations that need to be made:

+-------------------------------+--------------------------------------+
| Old module                    | New Module                           |
+===============================+======================================+
| ``autopilot.emulators.input`` | :py:mod:`autopilot.input`            |
+-------------------------------+--------------------------------------+
| ``autopilot.emulators.X11``   | Deprecated - use                     |
|                               | :py:mod:`autopilot.input` for input  |
|                               | and :py:mod:`autopilot.display` for  |
|                               | getting display information.         |
+-------------------------------+--------------------------------------+
| ``autopilot.emulators.bamf``  | Deprecated - use                     |
|                               | :py:mod:`autopilot.process` instead. |
+-------------------------------+--------------------------------------+



.. TODO - add specific instructions on how to port tests from the 'old and busted' autopilot to the 'new hotness'. Do this when we actually start the porting work ourselves.
