.. image:: https://coveralls.io/repos/github/chris104957/django-carrot/badge.svg?branch=master
    :target: https://coveralls.io/github/chris104957/django-carrot?branch=master

.. image:: https://readthedocs.org/projects/django-carrot/badge/?version=latest
    :target: http://django-carrot.readthedocs.io/en/latest/?badge=
    
.. image:: https://travis-ci.org/chris104957/django-carrot.svg?branch=master
    :target: https://travis-ci.org/chris104957/django-carrot.svg?branch=master
    
.. image:: https://coveralls.io/repos/github/chris104957/django-carrot/badge.svg?branch=master
    :target: https://coveralls.io/github/chris104957/django-carrot?branch=master)
    
.. image:: https://badge.fury.io/py/django-carrot.svg
    :target: https://badge.fury.io/py/django-carrot
    
.. image:: https://img.shields.io/badge/License-Apache%202.0-blue.svg
    :target: https://opensource.org/licenses/Apache-2.0

.. image:: http://githubbadges.com/star.svg?user=chris104957&repo=django-carrot&style=flat
    :target: https://github.com/chris104957/django-carrot

.. image:: /docs/source/images/carrot-logo-big.png


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
- Built in django-admin daemon
- Supports Django 2.0


Installation
------------

Install django-carrot:

.. code-block:: bash

    pip install django-carrot

Install and run RabbitMQ

.. code-block:: bash 

    brew install rabbitmq
    brew services start rabbitmq
    
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

Support
-------

If you are having any issues, please contact christopherdavies553@gmail.com

License
-------

The project is licensed under the Apache license.
