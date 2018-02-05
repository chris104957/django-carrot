[![Documentation Status](https://readthedocs.org/projects/django-carrot/badge/?version=latest)](http://django-carrot.readthedocs.io/en/latest/?badge=latest)
[![Build Status](https://travis-ci.org/chris104957/django-carrot.svg?branch=master)](https://travis-ci.org/chris104957/django-carrot.svg?branch=master)
[![Coverage Status](https://coveralls.io/repos/github/chris104957/django-carrot/badge.svg?branch=master)](https://coveralls.io/github/chris104957/django-carrot?branch=master)
[![PyPI version](https://badge.fury.io/py/django-carrot.svg)](https://badge.fury.io/py/django-carrot)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

![logo](/docs/source/images/carrot-logo-big.png)


django-carrot is a lightweight task queue backend for Django projects that uses the RabbitMQ message broker, with an emphasis
on quick and easy configuration and task tracking

Installation
------------

First, install RabbitMQ and start:
```
brew install rabbitmq
brew services start rabbitmq
```

Then, install django-carrot
```
    pip install django-carrot
```


Configuration
-------------
1. Create a django project, if you don't already have one:
```
django-admin.py startproject carrottest
```

2. Add carrot to your Django project's settings module:

```
    INSTALLED_APPS = [
        ...
        'carrot',
        ...
    ]
```

3. Create the carrot migrations and apply them to your project's database:

```
    python manage.py makemigrations carrot
    python manage.py migrate
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

The full documentation is available at [readthedocs.io](http://django-carrot.readthedocs.io/)

Support
-------

If you are having any issues, please [log an issue](https://github.com/chris104957/django-carrot/issues/new) and add the **help wanted** label

License
-------

The project is licensed under the Apache license.


Icons made by [Trinh Ho](https://www.flaticon.com/authors/trinh-ho)
