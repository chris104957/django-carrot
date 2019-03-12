# django-carrot configuration

django-carrot is configured via your Django project's settings modules. All possible configuration options are listed in
this page. All configuration options are inserted as follows:



```python
CARROT = {
    # settings go here
}
```


## ``default_broker``

> default value: `amqp://guest:guest@localhost:5672/` (`str` or `dict`)

Carrot needs to be able to connect to at least one RabbitMQ broker in order to work. The default broker can either be
provided as a string:

```python
CARROT = {
    'default_broker': 'amqp://myusername:mypassword@192.168.0.1:5672/my-virtual-host'
}
```

or alternatively, in the following format:

```python
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
```

## `queues`

> default value: `[]` (`list`)

django-carrot will automatically create a queue called `default`. However, you may wish to define your own queues in
order to access additional functionality such as:

- Sending tasks to different queues
- Increasing the number of consumers attached to each queue

To define your own queues, add a list of *queues* to your carrot configuration:


```python
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
```

Each queue supports the following configuration options:

- `name`: the queue name, as a string
- `host`: the queue host. Can either be a URL as a string (as in the above example) or a dict in the following format: 
   ```python
   'name':'my-queue',
   'host': {
            'host': '192.168.0.1',
            'port': 5672,
            'name': 'my-virtual-host',
            'username': 'my-rabbit-username',
            'password': 'my-rabbit-password',
            'secure': False
        }
   ```
- `concurrency`: the number of consumers to be attached to the queue, as an integer. Defaults to `1`
- `consumable`: Whether or not the service should consume messages in this queue, as a Boolean. Defaults to `True`

## `task_modules`

> default value: `[]` (`list`)

This setting is required while using **django-carrot monitor** and should point at the python module where your tasks
are kept. It will populate the task selection drop down while creating/editing scheduled tasks:

![with task modules](images/1.0/with-task-modules.png "with task modules")

The *task_modules* option is used to enable this functionality. It can be added to the Carrot configuration as follows:

```python
CARROT = {
   #...
   'task_modules': ['myapp.mymodule', 'myapp.myothermodule',]
}
```


## `monitor_authentication`

> default: `[]` (`list`)

By default, all views provided by :ref:`carrot-monitor-configuration` are public. If you want to limit access to these
views to certain users of your Django app, you can list the decorators to apply to these views. This is done with the
*monitor_authentication* setting:


```python
CARROT = {
   'monitor_authentication': ['django.contrib.auth.decorators.login_required', 'myapp.mymodule.mydecorator']
}
```

The above example will apply Django's `login_required` decorator to all of Carrot monitor's views, as well as
whatever custom decorators you specify.



