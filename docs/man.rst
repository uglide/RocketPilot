Autopilot Man Page
##################

SYNOPSIS
--------
.. argparse_usage::

DESCRIPTION
-----------
autopilot is a tool for writing functional test suites for graphical applications for Ubuntu.

OPTIONS
-------
.. argparse_options::

General Options
       -h, --help
            Get help from autopilot. This command can also be present after  a
            sub-command (such as run or list) to get help on the specific com‐
            mand.  Further options are restricted to particular autopilot com‐
            mands.

       -v, --version
           Display autopilot version and exit.

       --enable-profile
           Enable collection of profile data for autopilot itself. If enabled,
           profile data will be stored in 'autopilot_<pid>.profile' in the
           current working directory.

   list [options] suite [suite...]
       List the autopilot tests found in the given test suite.

       suite
            See `SPECIFYING SUITES`_

       -ro, --run-order
            List tests in the order they will be run in, rather than alphabet‐
            ically (which is the default).

       --suites
            Lists only available suites, not tests contained within the suite.

   run [options] suite [suite...]
       Run one or more test suites.

       suite
            See `SPECIFYING SUITES`_

       -o FILE, --output FILE
            Specify where the test log should be written. Defaults to  stdout.
            If  a directory is specified the file will be created with a file‐
            name of <hostname>_<dd.mm.yyy_HHMMSS>.log

       -f FORMAT, --format FORMAT
            Specify the format for the log. Valid options are 'xml' and 'text'
            'subunit' for JUnit XML, plain text, and subunit, respectively.

       -ff, --failfast
            Stop the test run on the first error or failure.

       -r, --record
            Record failed tests. Using this option requires the 'recordmydesk‐
            top' application be installed. By default, videos  are  stored  in
            /tmp/autopilot

       --record-options
            Comma separated list of options to pass to recordmydesktop

       -rd DIR, --record-directory DIR
            Directory where videos should be stored (overrides the default set
            by the -r option).

       -ro, --random-order
            Run the tests in random order

       -v, --verbose
            Causes autopilot to print the test log to stdout while the test is
            running.

       --debug-profile
            Select a profile for what additional debugging information should
            be attached to failed test results.

       --timeout-profile
            Alter the timeout values Autopilot uses. Selecting 'long' will
            make autopilot use longer timeouts for various polling loops. This
            can be useful if autopilot is running on very slow hardware

   launch [options] application
       Launch an application with introspection enabled.

       -v, --verbose

            Show autopilot log messages. Set twice to also log data useful
            for debugging autopilot itself.

       -i INTERFACE, --interface INTERFACE
            Specify which introspection interace to load.  The default
            ('Auto') uses ldd to try and detect which interface to load.
            Options are Gtk and Qt.

   vis [options]
       Open the autopilot visualizer tool.

       -v, --verbose
            Show autopilot log messages. Set twice to also log data useful
            for debugging autopilot itself.

       -testability
            Start the vis tool in testability mode. Used for self-tests only.

SPECIFYING SUITES
-----------------
        Suites are listed as a python dotted package name. Autopilot will do a
        recursive import in order to find all tests within a python package.
