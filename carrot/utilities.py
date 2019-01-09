"""
This module contains a number of helper functions for performing basic Carrot functions, e.g. publish, schedule and
consume

Most users should use the functions defined in this module, rather than attempting to subclass the base level objects

"""
import json
import importlib
from django.conf import settings
from carrot.objects import VirtualHost, Message
from carrot.models import ScheduledTask, MessageLog
from django.utils.decorators import method_decorator
from carrot import DEFAULT_BROKER
from carrot.exceptions import CarrotConfigException
from django.db.utils import IntegrityError
from typing import Dict, List


def get_host_from_name(name: str) -> VirtualHost:
    """
    Gets a host object from a given queue name based on the Django configuration

    If no queue name is provided (as may be the case from some callers), this function returns a VirtualHost based on
    the CARROT.default_broker value.

    May raise an exception if the given queue name is not registered in the settings.
    :rtype: object

    """
    try:
        carrot_settings = settings.CARROT
    except AttributeError:
        carrot_settings = {
            'default_broker': DEFAULT_BROKER,
            'queues': [
                {
                    'name': 'default',
                    'host': DEFAULT_BROKER
                }
            ]
        }

    try:
        if not name:
            try:
                conf = carrot_settings.get('default_broker', {})
            except AttributeError:
                conf = {}

            if not conf:
                conf = {'url': DEFAULT_BROKER}
            elif isinstance(conf, str):
                conf = {'url': conf}

            return VirtualHost(**conf)

        queues = carrot_settings.get('queues', [])
        queue_host = list(filter(lambda queue: queue['name'] == name, queues))[0]['host']
        try:
            vhost = VirtualHost(**queue_host)
        except TypeError:
            vhost = VirtualHost(url=queue_host)

        return vhost

    except IndexError:
        raise CarrotConfigException('Cannot find queue called %s in settings.CARROT queue list' % name)


def validate_task(task: str or function) -> str:
    """
    Helper function for dealing with task inputs which may either be a callable, or a path to a callable as a string

    In case of a string being provided, this function checks whether the import path leads to a valid callable

    Otherwise, the callable is converted back into a string (as the :class:`carrot.objects.Message` requires a string
    input)

    This function is used by the following other utility functions:
    - :func:`.create_scheduled_task`
    - :func:`.create_message`

    """
    mod, fname = (None, ) * 2

    if isinstance(task, str):
        try:
            fname = task.split('.')[-1]
            mod = '.'.join(task.split('.')[:-1])
            module = importlib.import_module(mod)
            getattr(module, fname)
        except ImportError as err:
            raise ImportError('Unable to find the module: %s' % err)

        except AttributeError as err:
            raise AttributeError('Unable to find a function called %s in the module %s: %s' % (fname, mod, err))
    else:
        task = '%s.%s' % (task.__module__, task.__name__)

    return task


def create_message(task: str or function, priority: int=0, task_args: tuple=(), queue: str=None, exchange: str='',
                   routing_key: str=None, task_kwargs: dict=None) -> Message:
    """
    Creates a :class:`carrot.objects.Message` object without publishing it

    The task to execute (as a string or a callable) needs to be supplied. All other arguments are optional
    """

    if not task_kwargs:
        task_kwargs = {}

    task = validate_task(task)

    vhost = get_host_from_name(queue)
    msg = Message(virtual_host=vhost, queue=queue, routing_key=routing_key, exchange=exchange, task=task,
                  priority=priority, task_args=task_args, task_kwargs=task_kwargs)

    return msg


def publish_message(task: str or function, *task_args, priority: int=0, queue: str=None, exchange: str='',
                    routing_key: str=None, **task_kwargs) -> MessageLog:
    """
    Wrapped for :func:`.create_message`, which publishes the task to the queue

    This function is the primary method of publishing tasks to a message queue
    """
    msg = create_message(task, priority, task_args, queue, exchange, routing_key, task_kwargs)
    return msg.publish()


def create_scheduled_task(task: str or function, interval: Dict[str, int], task_name: str=None, queue: str=None,
                          **kwargs) -> ScheduledTask:
    """
    Helper function for creating a :class:`carrot.models.ScheduledTask`
    """

    if not task_name:
        task_name = task

    task = validate_task(task)

    try:
        assert isinstance(interval, dict)
        assert len(interval.items()) == 1
    except AssertionError:
        raise AttributeError('Interval must be a dict with a single key value pairing, e.g.: {\'seconds\': 5}')

    type, count = list(*interval.items())

    try:
        t = ScheduledTask.objects.create(
            queue=queue,
            task_name=task_name,
            interval_type=type,
            interval_count=count,
            routing_key=queue,
            task=task,
            content=json.dumps(kwargs or '{}'),
        )
    except IntegrityError:
        raise IntegrityError('A ScheduledTask with this task_name already exists. Please specific a unique name using '
                             'the task_name parameter')

    return t


def get_mixin(decorator: callable) -> object:
    """
    Helper function that allows dynamic application of decorators to a class-based views

    :param func decorator: the decorator to apply to the view
    :return:
    """
    class Mixin:
        @method_decorator(decorator)
        def dispatch(self, request, *args, **kwargs):
            return super(Mixin, self).dispatch(request, *args, **kwargs)

    return Mixin


def create_class_view(view: object, decorator: callable) -> object:
    """
    Applies a decorator to the dispatch method of a given class based view. Can be chained

    :rtype: the updated class based view
    """
    class DecoratedView(get_mixin(decorator), view):
        pass

    return DecoratedView


def decorate_class_view(view_class: object, decorators: List[str]=None) -> create_class_view:
    """
    Loop through a list of string paths to decorator functions, and call :func:`.create_class_view` for each one
    """
    if decorators is None:
        decorators = []

    for decorator in decorators:
        _module = '.'.join(decorator.split('.')[:-1])
        module = importlib.import_module(_module)
        _decorator = getattr(module, decorator.split('.')[-1])
        view_class = create_class_view(view_class, _decorator)

    return view_class


def create_function_view(view: callable, decorator: callable) -> callable:
    """
    Similar to :func:`.create_class_view`, but attaches a decorator to a function based view, instead of a class-based
    one

    """
    @decorator
    def wrap(request, *args, **kwargs):
        return view(request, *args, **kwargs)

    return wrap


def decorate_function_view(view: object, decorators: List[str]=None) -> create_function_view:
    """
    Similar to :func:`.decorate_class_view`, but for function based views
    """
    if not decorators:
        decorators = []

    for decorator in decorators:
        _module = '.'.join(decorator.split('.')[:-1])
        module = importlib.import_module(_module)
        _decorator = getattr(module, decorator.split('.')[-1])
        view = create_function_view(view, _decorator)

    return view


def purge_queue() -> None:
    """
    Deletes all MessageLog objects with status `IN_PROGRESS` or `PUBLISHED` add iterate through and purge all RabbitMQ
    queues
    """
    queued_messages = MessageLog.objects.filter(status__in=['IN_PROGRESS', 'PUBLISHED'])
    queued_messages.delete()

    try:
        carrot_settings = settings.CARROT
    except AttributeError:
        carrot_settings = {
            'default_broker': DEFAULT_BROKER,
        }

    queues = carrot_settings.get('queues', [{'name': 'default', 'host': DEFAULT_BROKER}])
    for queue in queues:
        if type(queue['host']) is str:
            filters = {'url': queue['host']}
        else:
            filters = queue['host']
        host = VirtualHost(**filters)
        channel = host.blocking_connection.channel()
        channel.queue_purge(queue=queue['name'])


