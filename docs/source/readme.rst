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

    pip install django-carrot-0.1.dev0.tar.gz

Setting up RabbitMQ
*******************

Carrot requires a connection to a RabbitMQ server. Installing and configuring RabbitMQ is currently beyond the scope of
this tutorial. Refer to the `RabbitMQ download page <http://www.rabbitmq.com/download.html>`_

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

Scheduling tasks
****************

Scheduled tasks are stored in your Django project's database as **ScheduledTask** objects. To
scheduled the **my_task** function to run every 5 seconds, use the following code:

.. code-block:: python

    from carrot.utilities import create_scheduled_task

    create_scheduled_task(my_task, {'seconds': 5}, hello=True)

The above will schedule the **my_task** function to run every 5 seconds (while the Carrot service is running)


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



Contribute
----------

- Issue Tracker: https://github.com/chris104957/django-carrot/issues
- Source Code: https://github.com/chris104957/django-carrot

Support
-------

If you are having issues, please contact christopherdavies553@gmail.com

License
-------

The project is licensed under the Apache license.
