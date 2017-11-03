.. _admin-command:

The Carrot service
------------------

Carrot implements two *manage.py* commands in your django app - **carrot** and **carrot_daemon**

The **carrot** command is the base service which starts consuming messages from your defined RabbitMQ brokers, and
publishing any active scheduled tasks at the required intervals

**carrot_daemon** is a daemon which can be used the invoke the **carrot** service as a detached process, and allows
users to stop/restart the service safely, and to check the status. **carrot_daemon** can be invoked as follows:

.. code-block:: bash

    python manage.py carrot_daemon start
    python manage.py carrot_daemon stop
    python manage.py carrot_daemon restart
    python manage.py carrot_daemon status

Further options
---------------

The following additional arguments are also available:

- **logfile**: path to the log file. Defaults to /var/log/carrot.log
- **pidfile**: path to the pid file. Defaults to /var/run/carrot.pid
- **no-scheduler**: run the carrot service without the scheduler (only consumes tasks)
- **testmode**: Used for running the carrot tests. Not applicable for most users
- **loglevel**: The level of logging to use. Defaults to **DEBUG** and shouldn't be changed under most circumstances

More examples
-------------

Custom log/pid file paths
*************************

On some systems you may encounter OS errors while trying to run the service with the default log/pid file locations.
This can be fixed by specifying your own values for these paths:

.. code-block:: bash

    python manage.py carrot_daemon start --logfile carrot.log --pidfile carrot.pid

.. note::
    If you use a custom pid, you must also provide this same argument when attempting to stop, restart or check the
    status of the carrot service

Running without the scheduler
*****************************

Use the following to disabled **ScheduledTasks**

.. code-block:: bash

    python manage.py carrot_daemon --no-scheduler


Debugging
---------

Using the *carrot_daemon* will run in detached mode with no sys.out visible. If you are having issues getting the
service working properly, or want to check your broker configuration, you can use the *carrot* command instead, as
follows:

.. code-block:: bash

    python manage.py carrot

You will be able to read the system output using this command, which should help you to resolve any issues

.. note::
    The *carrot* command does not accept the **pidfile** or **mode** (e.g. start, stop, restart, status) arguments. No
    pid file gets created in this mode, and the process is the equivalent of *carrot_daemon start*. To stop the process,
    simply use CTRL+C


Classes and methods
-------------------

.. automodule:: carrot.management.commands.carrot_daemon
   :members:


.. automodule:: carrot.management.commands.carrot
   :members:

