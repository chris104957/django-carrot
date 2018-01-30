.. _monitor:

django-carrot monitor
=====================

Introduction
------------

django-carrot provides a simple interface for managing :class:`carrot.models.MessageLog` and
:class:`carrot.models.ScheduledTask` objects, known as the **django-carrot monitor**. This interface offers the
following functionality:

- Monitoring of tasks currently in the queue
- Viewing the log and traceback of failed tasks, and deleting/requeuing them
- Viewing the log for tasks that have completed successfully
- Allows users to view, edit and create scheduled tasks
- On demand publishing of scheduled tasks

For each task, the monitor displays:

- Basic information about the task, e.g. the virtualhost and queue it has been published to, the priority, and
  the dates/times it was published/completed/failed
- The arguments and keyword arguments the task was called with
- Where applicable, the task log, output and error traceback information

.. _carrot-monitor-configuration:

Configuration
-------------

To enable the django-carrot monitor, simply add the URLs to your project's main urls.py file:

.. code-block:: python

    urlpatterns = [
        ...
        url(r'^django-carrot/', include('django-carrot.urls')),
    ]

You will now be able to see the monitor at the path you have specified, eg: http://localhost:8000/carrot/

In order to create scheduled tasks using django-carrot monitor, it is also recommended that you specify your task
modules in your Django project's settings module. This is done as follows:

.. code-block:: python

    CARROT = {
        ...
        'task_modules': ['my_app.my_tasks_module'],
    }


Authentication
**************

By default, the django-carrot monitor interface is public. However, you can set authentication decorators from your
Django project's settings module:

.. code-block:: python

    CARROT = {
        ...
        'monitor_authentication': ['django.contrib.auth.decorators.login_required'],
    }

The above uses Django's built it :func:`django.contrib.auth.decorators.login_required` decorator to ensure that all
users are logged in before attempting to access the monitor. You can also specify your own decorators here.




