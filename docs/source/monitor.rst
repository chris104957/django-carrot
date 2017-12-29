.. _carrot-monitor:

The Carrot monitor
==================

Introduction
------------

Carrot provides a convenient set of views for :class:`carrot.models.MessageLog` and :class:`carrot.models.ScheduledTask`
objects, known as the **Carrot monitor**. These views offer the following functionality:
    - Displays the list of published tasks yet to be executed
    - Displays a list of tasks that failed to execute
    - Displays a list of the most recently completed tasks
    - Allows users to view, edit and create scheduled tasks

For each task, the monitor displays:
    - Basic information about the task, e.g. the virtualhost and queue it has been published to, the priority, and
      the dates/times it was published/completed/failed
    - The arguments and keyword arguments the task was called with, if any
    - The task log
    - The output of the completed task, if any
    - The traceback and error information, in case of failed tasks

Carrot monitor also gives you the option to requeue or delete failed tasks in the Failed tasks list

.. _carrot-monitor-configuration:

Configuration
-------------

To enable to carrot monitor, simply add the URLs to your project's main urls.py file:

.. code-block:: python

    urlpatterns = [
        ...
        url(r'^carrot/', include('carrot.urls')),
        ...
    ]

You will now be able to see the monitor at the path you have specified, eg: http://localhost:8000/carrot/

In order to create scheduled tasks using Carrot monitor, you should also specify your task modules in your Django
project's settings.module. This is done as follows:

.. code-block:: python

    CARROT = {
        ...
        'task_modules': ['my_app.my_tasks_module'],
        ...
    }


Authentication
**************

By default, all carrot monitor views are public. However, you can set authentication decorators from your Django
project's settings module:

.. code-block:: python

    CARROT = {
        ...
        'monitor_authentication': ['django.contrib.auth.decorators.login_required'],
    }

Adding the above line to your Carrot config will mean that all users must be authenticated in order to access the
monitor, by applying the :func:`django.contrib.auth.decorators.login_required` decorator to all of Carrot monitor's
views.

.. note::
    *new in v.04*: Carrot monitor now allows you to search for a task based on its function name, task arguments and
    keyword arguments
    *new in v0.2*: Carrot monitor now uses a reactive front end built in VueJS that uses a rest API to retrieve task
    information from your Django project's database. The authentication decorators defined above will also be used to
    control access to this API





