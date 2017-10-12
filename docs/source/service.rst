.. _admin-command:

The Carrot service
------------------

This module implements a command line interface for starting and stopping the carrot service. It can be executed from
your Django project's main folder with this command

.. code-block:: bash

    python manage.py carrot


The following options are available:

.. code-block:: bash

    optional arguments:
      -h, --help            show this help message and exit
      --version             show program's version number and exit
      -v {0,1,2,3}, --verbosity {0,1,2,3}
                            Verbosity level; 0=minimal output, 1=normal output,
                            2=verbose output, 3=very verbose output
      --settings SETTINGS   The Python path to a settings module, e.g.
                            "myproject.settings.main". If this isn't provided, the
                            DJANGO_SETTINGS_MODULE environment variable will be
                            used.
      --pythonpath PYTHONPATH
                            A directory to add to the Python path, e.g.
                            "/home/djangoprojects/myproject".
      --traceback           Raise on CommandError exceptions
      --no-color            Don't colorize the command output.
      -l LOGFILE, --logfile LOGFILE
                            The path to the log file
      --no-scheduler        Do not start scheduled tasks (only runs consumer sets)
      --consumer-class CONSUMER_CLASS
                            The consumer class to use. Must be an extension of 'carrot.objects.Consumer'
      --loglevel LOGLEVEL   The logging level. Must be one of DEBUG, INFO,
                            WARNING, ERROR, CRITICAL





.. automodule:: carrot.management.commands.carrot
   :members:
