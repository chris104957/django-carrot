.. _carrot-settings:

Carrot configuration
====================

Carrot is configured via your Django project's settings modules. This page lists all available configuration options for
carrot


The Carrot settings dictionary
------------------------------

All Carrot configuration is done by adding a **CARROT** dictionary to your Django project's settings module

.. code-block:: python

    CARROT = {
        ...
    }


All of the configuration options described below should go inside this dictionary

The default broker
------------------

Carrot needs to be able to connect to at least one RabbitMQ broker in order to work. The default broker should be
defined as follows:

.. code-block:: python

   CARROT = {
        'default_broker': 'amqp://myusername:mypassword@192.168.0.1:5672/my-virtual-host'
   }

Alternatively, you can supply the default broker credentials in the following format:

.. code-block:: python

   CARROT = {
        'default_broker': {
            'host': '192.168.0.1', # host of your RabbitMQ server
            'port': 5672, # your RabbitMQ port. The default is 5672
            'name': 'my-virtual-host', # the name of your virtual host. Can be omitted if you do not use VHOSTs
            'username': 'my-rabbit-username', # your RabbitMQ username
            'password': 'my-rabbit-password', # your RabbitMQ password
            'secure': False # Use SSL
        }
    }

.. note::
    If you do not supply the **default_broker** to your carrot settings, it will default to the following assumed
    default rabbit config, `amqp://guest:guest@localhost:5672/`

Queue configuration
-------------------

As long as you have configured a broker, the Carrot service will automatically create a queue for you at runtime.

However, you may wish to define your own queues in order to access additional functionality such as:
- Sending tasks to different queues (e.g. high/low priority)
- Increasing the number of consumers attached to each queue

To define your own queues, add a list of *queues* to your carrot configuration:

.. code-block:: python

   CARROT = {
        'queues': [
            {
                'name': 'my-queue-1',
                'host': 'amqp://myusername:mypassword@192.168.0.1:5672/my-virtual-host',
                'concurrency': 5,
            },
            {
                'name': 'my-queue-2',
                'host': 'amqp://myusername:mypassword@192.168.0.1:5672/my-virtual-host-2',
                'consumable': False,
            },
        ]
   }

Each *queue* supports the following configuration options:

:name:
    the queue name, as a string
:host:
    the queue host. Can either be a URL as a string (as in the above example) or a dict in the following format:

    .. code-block:: python

       'name':'my-queue',
       'host': {
                'host': '192.168.0.1',
                'port': 5672,
                'name': 'my-virtual-host',
                'username': 'my-rabbit-username',
                'password': 'my-rabbit-password',
                'secure': False
            }

:concurrency:
    the number of consumers to be attached to the queue, as an integer. Defaults to *1*

:consumable:
    Whether or not the service should consume messages in this queue, as a Boolean. Defaults to *True*

Task modules
------------

This is a helper setting used by :ref:`carrot-monitor-configuration` to allow you to select functions to be scheduled
from a drop down list, rather than having to type in the import path manually.

.. figure:: /images/no-task-modules.png
    :width: 600px
    :align: center
    :height: 100px
    :figclass: align-center

    without task modules

.. figure:: /images/with-task-modules.png
    :width: 600px
    :align: center
    :height: 100px
    :figclass: align-center

    with task modules

The *task_modules* option is used to enable this functionality. It can be added to the Carrot configuration as follows:

.. code-block:: python

   CARROT = {
       ...
       'task_modules': ['myapp.mymodule', 'myapp.myothermodule',]
   }

.. note::
    Any Python function in your Django project, from any module, can be handled asynchronously with Carrot. However, for
    the purposes of *Scheduled* tasks, you should aim to limit the number of modules containing functions that are to be
    executed as scheduled tasks. Additionally, you should aim to keep modules which *only* contain functions that are
    intended to be used as scheduled tasks, as all functions listed in these modules will appear in the drop down list
    in Carrot monitor

Monitor Authentication
----------------------

By default, all views provided by :ref:`carrot-monitor-configuration` are public. If you want to limit access to these
views to certain users of your Django app, you can list the decorators to apply to these views. This is done with the
*monitor_authentication* setting:

.. code-block:: python

   CARROT = {
       'monitor_authentication': ['django.contrib.auth.decorators.login_required', 'myapp.mymodule.mydecorator']
   }

The above example will apply Django's :func:`login_required` decorator to all of Carrot monitor's views, as well as
whatever custom decorators you specify.



