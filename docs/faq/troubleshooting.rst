===============
Troubleshooting
===============

.. contents::

.. _troubleshooting_general_techniques:

------------------
General Techniques
------------------

The single hardest thing to do while writing autopilot tests is to understand the state of the application's object tree. This is especially important for applications that change their object tree during the lifetime of the test. There are three techniques you can use to discover the state of the object tree:

**Using Autopilot Vis**

The :ref:`Autopilot vis tool <visualise_introspection_tree>` is a useful tool for exploring the entire structure of an application, and allows you to search for a particular node in the object tree. If you want to find out what parts of the application to select to gain access to certain information, the vis tool is probably the best way to do that.

**Using print_tree**

The :meth:`~autopilot.introspection.ProxyBase.print_tree` method is available on every proxy class. This method will print every child of the proxy object recursively, either to ``stdout`` or a file on disk. This technique can be useful when:

* The application cannot easily be put into the state required before launching autopilot vis, so the vis tool is no longer an option.
* The application state that has to be captured only exists for a short amount of time.
* The application only runs on platforms where the vis tool isn't available.

The :meth:`~autopilot.introspection.ProxyBase.print_tree` method often produces a lot of output. There are two ways this information overload can be handled:

#. Specify a file path to write to, so the console log doesn't get flooded. This log file can then be searched with tools such as ``grep``.
#. Specify a ``maxdepth`` limit. This controls how many levels deep the recursive search will go.

Of course, these techniques can be used in combination.

**Using get_properties**

The :meth:`~autopilot.introspection.ProxyBase.get_properties` method can be used on any proxy object, and will return a python dictionary containing all the properties of that proxy object. This is useful when you want to explore what information is provided by a single proxy object. The information returned by this method is exactly the same as is shown in the right-hand pane of ``autopilot vis``.

----------------------------------------
Common Questions regarding Failing Tests
----------------------------------------

.. _failing_tests:

Q. Why is my test failing? It works some of the time. What causes "flakyness?"
==============================================================================

Sometimes a tests fails because the application under tests has issues, but what happens when the failing test can't be reproduced manually? It means the test itself has an issue.

Here is a troubleshooting guide you can use with some of the common problems that developers can overlook while writing tests.

StateNotFoundError Exception
============================

.. _state_not_found:

1. Not waiting for an animation to finish before looking for an object. Did you add animations to your app recently?

         * problem::

            self.main_view.select_single('Button', text='click_this')

         * solution::

            page.animationRunning.wait_for(False)
            self.main_view.select_single('Button', text='click_this')

2. Not waiting for an object to become visible before trying to select it. Is your app slower than it used to be for some reason? Does its properties have null values? Do you see errors in stdout/stderr while using your app, if you run it from the commandline?

 Python code is executed in series which takes milliseconds, whereas the actions (clicking a button etc.) will take longer as well as the dbus query time. This is why wait_select_* is useful i.e. click a button and wait for that click to happen (including the dbus query times taken).

         * problem::

            self.main_view.select_single('QPushButton', objectName='clickme')

         * solution::

            self.main_view.wait_select_single('QPushButton', objectName='clickme')

3. Waiting for an item that is destroyed to be not visible, sometimes the objects is destroyed before it returns false:
        * problem::

            self.assertThat(dialogButton.visible, Eventually(Equals(False)))

        * problem::

            self._get_activity_indicator().running.wait_for(False)


        * solution::

            dialogButton.wait_for_destroyed()

        * solution::

            self._get_activity_indicator().running.wait_for_destroyed()

4. Trying to use select_many like a list. The order in which the objects are returned are non-deterministic.
        * problem::

            def get_first_photo(self):
                """Returns first photo"""
                return event.select_many(
                    'OrganicItemInteraction',
                    objectName='eventsViewPhoto'
                )[0]

        * solution::

            def _get_named_photo_element(self, photo_name):
                """Return the ShapeItem container object for the named photo
                This object can be clicked to enable the photo to be selected.
                """
                photo_element = self.grid_view().wait_select_single(
                    'QQuickImage',
                    source=photo_name
                )
                return photo_element.get_parent()

            def select_named_photo(self, photo_name):
                """Select the named photo from the picker view."""
                photo_element = self._get_named_photo_element(photo_name)
                self.pointing_device.click_object(photo_element)
