import importlib
import json
import logging
import uuid
from typing import Tuple, Callable, Dict, Any, Union

import pika
from django.utils import timezone



class VirtualHost(object):
    """
    A RabbitMQ virtual host
    """

    def __init__(self,
                 url: str = None,
                 host: str = 'localhost',
                 name: str = '%2f',
                 port: int = 5672,
                 username: str = 'guest',
                 password: str = 'guest',
                 secure: bool = False) -> None:

        self.secure = secure
        if not url:
            self.host = host
            self.name = name
            self.port = port
            self.username = username
            self.password = password

        else:
            try:
                url = url.replace('amqp://', '')
                if '@' in url:
                    # user:pass@host:port/vhost
                    credentials, url = url.split('@')
                    self.username, self.password = credentials.split(':')

                else:
                    # host:port/vhost
                    self.username = username
                    self.password = password
                import pika

                try:
                    url, self.name = url.split('/')
                except ValueError:
                    url = url.split('/')[0]
                    self.name = name

                self.host, _port = url.split(':')
                self.port = int(_port)

            except Exception as err:
                raise Exception('Unable to parse the RabbitMQ server. Please check your configuration: %s' % err)

            if not self.name:
                self.name = '%2f'

    def __str__(self) -> str:
        """
        Returns the broker url
        """
        return 'amqp://%s:%s@%s:%s/%s' % (self.username, self.password, self.host, self.port, self.name)

    @property
    def blocking_connection(self) -> pika.BlockingConnection:
        """
        Connect to the VHOST
        """
        credentials = pika.PlainCredentials(username=self.username, password=self.password)
        if self.name == '%2f':
            vhost = '/'
        else:
            vhost = self.name

        params = pika.ConnectionParameters(host=self.host, port=self.port, virtual_host=vhost,
                                           credentials=credentials, connection_attempts=10, ssl=self.secure,
                                           heartbeat=1200)
        return pika.BlockingConnection(parameters=params)


class BaseMessageSerializer(object):
    """
    A class that defines how to convert a RabbitMQ message into an executable python function from your Django project,
    and back again

    :param Message message: the RabbitMQ message

    """
    content_type = 'application/json'
    type_header, message_type = ('',) * 2
    task_get_attempts = 20

    @classmethod
    def get_task(cls, properties: pika.BasicProperties, body: bytes) -> Callable:
        """
        Identifies the python function to be executed from the content of the RabbitMQ message. By default, Carrot
        returns the value of the self.type_header header in the properties.

        Once this string has been found, carrot uses importlib to return a callable python function.

        """
        mod = '.'.join(properties.headers[cls.type_header].split('.')[:-1])
        task = properties.headers[cls.type_header].split('.')[-1]
        module = importlib.import_module(mod)
        func = getattr(module, task)
        return func

    def __init__(self, message: 'Message') -> None:
        self.message = message

    def publish_kwargs(self) -> dict:
        """
        Returns a dictionary of keyword arguments to be passed to channel.basic_publish. In this implementation, the
        exchange, routing key and message body are returned

        """
        exchange = self.message.exchange or ''
        routing_key = self.message.routing_key or 'default'
        body = self.body()
        return dict(exchange=exchange, routing_key=routing_key, body=body, mandatory=True)

    def body(self) -> str:
        """
        Returns the content to be added to the RabbitMQ message body

        By default, this implementation returns a simple dict in the following format:

        .. code-block:: python

            {
                'args': ('tuple', 'of', 'positional', 'arguments'),
                'kwargs': {
                    'keyword1': 'value',
                    'keyword2': True
                }
            }

        """
        args = self.message.task_args
        kwargs = self.message.task_kwargs

        data: Dict[str, Any] = {}

        if args:
            data['args'] = args

        if kwargs:
            data['kwargs'] = kwargs

        return json.dumps(data)

    def properties(self) -> dict:
        """
        Returns a dict from which a :class:`pika.BasicProperties` object can be created

        In this implementation, the following is returned:
        - headers
        - content message_type
        - priority
        - message id
        - message message_type

        """
        headers = {self.type_header: self.message.task}
        content_type = self.content_type
        priority = self.message.priority
        message_id = str(self.message.uuid)
        message_type = self.message_type

        return dict(headers=headers, content_type=content_type, priority=priority, message_id=message_id,
                    type=message_type)

    def publish(self, connection: pika.BlockingConnection, channel: pika.channel.Channel) -> None:
        """
        Publishes a message to the channel
        """
        kwargs = self.publish_kwargs()
        kwargs['properties'] = pika.BasicProperties(**self.properties())
        channel.basic_publish(**kwargs)
        connection.close()

    @classmethod
    def serialize_arguments(cls, body: str) -> Tuple[tuple, dict]:
        """
        Extracts positional and keyword arguments to be sent to a function from the message body
        """
        content = json.loads(body)
        args = content.get('args', ())
        kwargs = content.get('kwargs', {})
        return args, kwargs


class DefaultMessageSerializer(BaseMessageSerializer):
    type_header = 'type'
    message_type = 'django-carrot message'


# noinspection PyUnresolvedReferences
class Message(object):
    """
    A message to publish to RabbitMQ. Takes the following parameters:

    .. note::
        Your RabbitMQ queue must support message priority for the *priority* parameter to have any affect. You need to
        define the x-max-priority header when creating your RabbitMQ queue to do this. See
        `Priority Queue Support <https://www.rabbitmq.com/priority.html>`_ for more details. Carrot applies a maximum
        priority of **255** by default to all queues it creates automatically.

    .. warning::
        You should not attempt to create instances of this object yourself. You should use the
        :func:`carrot.utilities.create_msg` function instead

    """

    def __init__(self,
                 task: str,
                 virtual_host: VirtualHost = None,
                 queue: str = 'default',
                 routing_key: str = None,
                 exchange: str = '',
                 priority: int = 0,
                 task_args: tuple = (),
                 task_kwargs: Union[str, dict] = None) -> None:

        if not task_kwargs or task_kwargs in ['{}', '"{}"']:
            task_kwargs = {}

        if not routing_key:
            routing_key = queue

        if not virtual_host:
            from carrot.utilities import get_host_from_name
            virtual_host = get_host_from_name(queue)

        assert isinstance(virtual_host, VirtualHost)

        self.uuid = str(uuid.uuid4())

        self.virtual_host = virtual_host
        self.exchange = exchange
        self.queue = queue
        self.routing_key = routing_key
        self.priority = priority

        self.task = task
        self.task_args = task_args
        self.task_kwargs = task_kwargs

        self.formatter = DefaultMessageSerializer(self)

    @property
    def connection_channel(self) -> Tuple[pika.BlockingConnection, pika.channel.Channel]:
        """
        Gets or creates the queue, and returns a tuple containing the object's VirtualHost's blocking connection,
        and its channel
        """
        connection = self.virtual_host.blocking_connection
        channel = connection.channel()

        return connection, channel

    def publish(self, pika_log_level: int = logging.ERROR) -> Any:
        """
        Publishes the message to RabbitMQ queue and creates a MessageLog object so the progress of the task can be
        tracked in the Django project's database
        """
        from carrot.models import MessageLog
        logging.getLogger("pika").setLevel(pika_log_level)
        connection, channel = self.connection_channel

        if isinstance(self.task_kwargs, str):
            try:
                json.dumps(self.task_kwargs)
                keyword_arguments = self.task_kwargs
            except json.decoder.JSONDecodeError:
                keyword_arguments = '{}'
        else:
            keyword_arguments = json.dumps(self.task_kwargs)

        log = MessageLog.objects.create(
            status='PUBLISHED',
            queue=self.queue,
            exchange=self.exchange or '',
            routing_key=self.routing_key or self.queue,
            uuid=str(self.uuid),
            priority=self.priority,
            task_args=self.task_args,
            content=keyword_arguments,
            task=self.task,
            publish_time=timezone.now(),
        )

        self.formatter.publish(connection, channel)
        return log
