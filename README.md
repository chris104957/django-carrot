# django-carrot
A lightweight task queue for Django using RabbitMQ


Features
--------

- Minimal configuration required
- Task scheduling
- Task prioritization
- Task-level monitoring via the Carrot monitor
- Multithreaded queue consumers

Installation
------------

pip install django-carrot


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

Full documentation
------------------

Please refer to [Carrot documentation on readthedocs.io](http://django-carrot.readthedocs.io/en/latest/index.html)

Further help
------------

If you encounter any issues using Carrot, please [Log an issue](https://github.com/chris104957/django-carrot/issues)

