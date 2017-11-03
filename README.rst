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
- **new in v0.2** built in django-admin daemon


Installation
------------

.. code-block:: bash

    pip install django-carrot


Configuration
-------------

1. Add carrot to your Django project's settings module:

.. code-block:: python

    INSTALLED_APPS = [
        ...
        'carrot',
        ...
    ]


2. Create the carrot migrations and apply them to your project's database:

.. code-block:: python

    python manage.py makemigrations carrot
    python manage.py migrate carrot

3. Set your default broker in your Django project's settings

.. code-block:: python

    CARROT = {
        'default_broker': 'amqp://guest:guest@localhost:5672
    }


Usage
-----

To start the service:

.. code-block:: bash

    python manage.py carrot_daemon start


To run tasks asynchronously:

.. code-block:: python

    from carrot.utilities import publish_message

    def my_task(**kwargs):
        return 'hello world'

    publish_message(my_task, hello=True)



To schedule tasks to run at a given interval

.. code-block:: python

    from carrot.utilities import create_scheduled_task

    create_scheduled_task(my_task, {'seconds': 5}, hello=True)


Full documentation
------------------

The full documentation is available at `readthedocs.io <http://django-carrot.readthedocs.io/en/latest/index.html>`

Contribute
----------

Please refer to `Contributing to Carrot <https://github.com/chris104957/django-carrot/blob/master/CONTRIBUTING.md>`

Support
-------

If you are having any issues, please contact christopherdavies553@gmail.com

License
-------

The project is licensed under the Apache license.
