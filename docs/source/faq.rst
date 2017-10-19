Frequently asked questions
==========================

Why not Celery?
***************

Carrot is intended as a lightweight alternative to Celery which has simpler installation/configuration.

Carrot also offers task-level logging. All published tasks are saved to the Django project's database, so that
they can easily be monitored, re-queued and debugged as necessary

There are a number of other lightweight Celery alternatives available for Python, but most of these use the Redis
message broker, whereas Carrot uses RabbitMQ.