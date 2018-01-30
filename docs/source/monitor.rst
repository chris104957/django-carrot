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

Usage
-----

Once configured, the monitor can be access from the path ``/carrot``, e.g. ``http://localhost:8000/carrot``

The monitor has 4 tabbed views:

Queued tasks
************

This view shows all tasks that are currently in the queue and will be processed by the consumer. To see more details about a particular task, click on the relevant row in the list. You will be able to see more details about the task, including where/when it is/was published

Failed tasks
************

This view shows all tasks that have failed during processing, along with the full log up to the failure, and a full traceback of the issue. Failed tasks can either be requeued or deleted from the queue, either in bulk or individually

Completed tasks
***************

Once tasks have been completed, they will appear in this section. At this point, the full log becomes available. You can use the drop down in the monitor to customize the level of visible logging.

Scheduled tasks
***************

You can manage scheduled tasks in this view. 

Use the **Create new scheduled task** button to schedule tasks to run at a given interval. The *task*, *queue*, *interval type* and *interval count* fields are mandatory. You can use the *active* slider to temporary prevent a scheduled task from running.

The *positional arguments* field must contain a valid list of python arguments. Here are some valid examples of input for this field:

.. code-block:: python

    True, 1, 'test', {'foo': 'bar'}


The *keyword arguments* field must contain valid json serializable content. For example:

.. code-block:: javascript

    {
        "parameter_1": true,
        "parateter_2": null,
        "parameter_3": ["list", "of", "things"],
        "parameter_4": {
            "more": "things"
        }
    }

.. warning::
    The *keyword arguments* input must be JSON, not a Python dict

.. note::
    - All task lists are refreshed every 5 seconds, or when certain actions are performed, e.g. on task deletion/requeue
    - Task logs are not available until a task completes or fails. This is because the task log only gets written to your Django project's database at the end of the process
    - *New in 0.5.1*: Scheduled tasks can now be run on demand by selecting the required task and clicking the **Run now** button


