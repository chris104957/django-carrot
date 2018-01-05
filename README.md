[![Documentation Status](https://readthedocs.org/projects/django-carrot/badge/?version=latest)](http://django-carrot.readthedocs.io/en/latest/?badge=latest)
[![Build Status](https://travis-ci.org/chris104957/django-carrot.svg?branch=master)](https://travis-ci.org/chris104957/django-carrot.svg?branch=master)
[![Coverage Status](https://coveralls.io/repos/github/chris104957/django-carrot/badge.svg?branch=master)](https://coveralls.io/github/chris104957/django-carrot?branch=master)
[![PyPI version](https://badge.fury.io/py/django-carrot.svg)](https://badge.fury.io/py/django-carrot)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

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

```
    pip install django-carrot
```


Configuration
-------------

1. Add carrot to your Django project's settings module:

```
    INSTALLED_APPS = [
        ...
        'carrot',
        ...
    ]
```

2. Create the carrot migrations and apply them to your project's database:

```
    python manage.py makemigrations carrot
    python manage.py migrate carrot
```

3. Set your default broker in your Django project's settings

```
    CARROT = {
        'default_broker': 'amqp://guest:guest@localhost:5672
    }
```

Usage
-----

To start the service:

```
    python manage.py carrot_daemon start
```

To run tasks asynchronously:

```
    from carrot.utilities import publish_message

    def my_task(**kwargs):
        return 'hello world'

    publish_message(my_task, hello=True)

```

To schedule tasks to run at a given interval

```
    from carrot.utilities import create_scheduled_task

    create_scheduled_task(my_task, {'seconds': 5}, hello=True)
```

Full documentation
------------------

The full documentation is available at [readthedocs.io](http://django-carrot.readthedocs.io/en/latest/index.html)

Contribute
----------

Please refer to [Contributing to Carrot](https://github.com/chris104957/django-carrot/blob/master/CONTRIBUTING.md>)

Support
-------

If you are having any issues, please contact christopherdavies553@gmail.com

License
-------

The project is licensed under the Apache license.
