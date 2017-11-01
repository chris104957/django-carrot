Getting started with Carrot
===========================

Introduction
------------

Carrot is a lightweight task queue backend for Django projects that uses the RabbitMQ message broker, with an emphasis
on quick and easy configuration and task tracking

Features
--------

- Minimal configuration required
- Task scheduling
- Task prioritization
- Task-level monitoring via the Carrot monitor
- Multithreaded queue consumers


Installation and configuration
------------------------------

Install Carrot
**************

Install with *pip*

.. code-block:: bash

    pip install django-carrot

Setting up RabbitMQ
*******************

Carrot requires a connection to a RabbitMQ broker to work. If you do not already have a RabbitMQ server to connect to,
you can refer to the `RabbitMQ download page <http://www.rabbitmq.com/download.html>`_

Configuring your Django project
*******************************

#. Add carrot to your Django project's settings module:

.. code-block:: python

    INSTALLED_APPS = [
        ...
        'carrot',
        ...
    ]

#. Create the carrot migrations and apply them to your project's database:

.. code-block:: bash

    python manage.py makemigrations carrot
    python manage.py migrate carrot

#. Set your default broker in your Django project's settings

.. code-block:: python

    CARROT = {
        'default_broker': 'amqp://guest:guest@localhost:5672
    }


Using Carrot
------------

Starting the service
********************

Once you have configured carrot, you can start the service using the following django-admin command:

.. code-block:: bash

    python manage.py carrot


Publishing tasks
****************

While the service is running, tasks will be consumed from your RabbitMQ queue. To publish messages to the queue, use
provided helper function:

.. code-block:: python

    from carrot.utilities import publish_message

    def my_task(**kwargs):
        return 'hello world'

    publish_message(my_task, hello=True)


The above will publish the **my_task** function to the default carrot queue. Once consumed, it will be
called with the keyword argument *hello=True*

Task logging
************

In order to view the task output in :ref:`carrot-monitor`, you will need to use Carrot's logger object. This is done
as follows:

.. code-block:: python

    from carrot.utilities import publish_message
    import logging

    logger = logging.getLogger('carrot')

    def my_task(**kwargs):
        logger.debug('hello world')
        logger.info('hello world')
        logger.warning('hello world')
        logger.error('hello world')
        logger.critical('hello world')

    publish_message(my_task, hello=True)

This will be rendered as follows in the carrot monitor output for this task:

.. figure:: /images/0.2/task-logging.png
    :width: 600px
    :align: center
    :height: 100px
    :figclass: align-center

    using the carrot logger

.. note::
    By default, Carrot Monitor only shows log entries with a level of *info* or higher. The entry logged with
    `logger.debug` only becomes visible if you change the **Log level** drop down


Scheduling tasks
****************

Scheduled tasks are stored in your Django project's database as **ScheduledTask** objects. The Carrot service will
publish tasks to your RabbitMQ queue at the required intervals. To scheduled the **my_task** function to run every 5
seconds, use the following code:

.. code-block:: python

    from carrot.utilities import create_scheduled_task

    create_scheduled_task(my_task, {'seconds': 5}, hello=True)

The above will publish the **my_task** function to the queue every 5 seconds


Daemonizing the service
-----------------------

As of V0.2, Carrot comes with its own daemon. To run the carrot service in the background, simply use `carrot_daemon`
instead of `carrot`, as follows:

.. code-block:: bash

    python manage.py carrot_daemon start
    python manage.py carrot_daemon stop
    python manage.py carrot_daemon restart
    python manage.py carrot_daemon status


The Carrot monitor
------------------

Carrot comes with it's own monitor view which allows you to:
    - View the list of queued tasks
    - View the traceback of failed tasks, and push them back into the message queue
    - View the traceback and output of successfully completed tasks

To implement it, simply add the carrot url config to your Django project's main url file:

.. code-block:: python

    urlpatterns = [
        ...
        url(r'^carrot/', include('carrot.urls')),
    ]

You will also need to register Carrot's template filters in your Django project's settings:


.. code-block:: python

    TEMPLATES = [
        ...
        'OPTIONS': {
            ...
            'builtins': [
                ...
                'carrot.templatetags.filters'
            ]
        }
    ]

For more information, refer to :ref:`carrot-monitor`

Contribute
----------

Please refer to `Contributing to Carrot <https://github.com/chris104957/django-carrot/blob/master/CONTRIBUTING.md>`_

Support
-------

If you are having issues, please contact christopherdavies553@gmail.com

License
-------

The project is licensed under the Apache license.
