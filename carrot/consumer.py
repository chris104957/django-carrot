"""
This module provides a backend API for creating Consumers and Consumer Sets

"""

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.db.utils import OperationalError
from django.conf import settings

from carrot.models import MessageLog
from carrot.objects import VirtualHost, BaseMessageSerializer

import json
import traceback
import threading
import logging
import importlib
import pika
import time
from typing import Optional, Type, List, Dict, Any, Callable, Union


LOGGING_FORMAT = '%(threadName)-10s %(asctime)-10s %(levelname)s:: %(message)s'


# noinspection PyUnusedLocal,PyUnresolvedReferences
class Consumer(threading.Thread):
    """
    An individual Consumer object. This class is run on a detached thread and watches a specific RabbitMQ queue for
    messages, and consumes them when they appear. Multiple Consumers can be linked to the same queue using a
    :class:`.ConsumerSet` object.
    """

    serializer: Type[BaseMessageSerializer] = BaseMessageSerializer
    reconnect_timeout: int = 5
    task_log: List[str] = []
    exchange_arguments: Dict[str, Any] = {}
    active_message_log: Optional[MessageLog] = None
    remaining_save_attempts: int = 10
    get_message_attempts: int = 50

    def __init__(self, host: VirtualHost, queue: str, logger: logging.Logger, name: str, durable: bool = True,
                 queue_arguments: dict = None, exchange_arguments: dict = None):
        """
        :param host: the host the queue to consume from is attached to
        :type host: :class:`carrot.objects.VirtualHost`
        :param str queue: the queue to consume from
        :param logger: the logging object
        :param name: the name of the consumer

        """
        super().__init__()

        if queue_arguments is None:
            queue_arguments = {}

        if not exchange_arguments:
            exchange_arguments = {}

        self.failure_callbacks: List[Callable] = []
        self.name = name
        self.logger = logger
        self.queue = queue
        self.exchange = queue

        self.connection: pika.SelectConnection = None
        self.channel: pika.channel = None
        self.shutdown_requested = False
        self._consumer_tag = None
        self._url = str(host)

        self.queue_arguments = queue_arguments
        self.exchange_arguments = exchange_arguments
        self.durable = durable

    def add_failure_callback(self, cb: Callable) -> None:
        """
        Registers a callback that gets called when there is any kind of error with the `.consume()` method
        """
        self.failure_callbacks.append(cb)

    def fail(self, log: MessageLog, err: Union[str, Exception]) -> None:
        """
        This function is called whenever there is a failure executing a specific `MessageLog` object

        The exception message is logged, and the MessageLog is updated with the result

        """
        self.logger.error('Task %s failed due to the following exception: %s' % (log.task, err))

        for cb in self.failure_callbacks:
            try:
                cb(log, err)
                self.task_log.append('Failure callback %s succeeded' % str(cb))
            except Exception as error:
                self.task_log.append('Failure callback %s failed due to an error: %s' % (str(cb), error))

        if log.pk:
            if self.task_log:
                log.log = '\n'.join(self.task_log)

            log.status = 'FAILED'
            log.failure_time = timezone.now()
            log.exception = err
            log.traceback = traceback.format_exc()
            log.save()

    def get_task_type(self, properties: pika.spec.BasicProperties, body: bytes) -> str:
        """
        Identifies the task type, by looking up the attribute **self.task_type** in the message properties

        The parameter `body` is not used here - However, it is included as in some cases it is useful when extending
        the `Consumer` class

        """
        return properties[self.serializer.type_header]

    def __get_message_log(self, properties: pika.spec.BasicProperties, body: bytes) -> MessageLog:
        for i in range(0, self.get_message_attempts):
            log = self.get_message_log(properties, body)

            if log:
                return log
            time.sleep(0.1)

    def get_message_log(self, properties: pika.spec.BasicProperties, body: bytes) -> Optional[MessageLog]:
        """
        Finds a MessageLog based on the content of the RabbitMQ message

        By default, carrot finds this retrieving the MessageLog UUID from the RabbitMQ message properties.message_id
        attribute.

        This method can be extended by custom consumers. For example, if you are attempting to consume from a RabbitMQ
        queue containing messages that do not come from your Carrot instance, you may want to extend this method to
        create, instead of get, a MessageLog object

        The `body` parameter is not used here but is included in as in some cases it is useful for customer `Consumer`
        objects

        .. note::
            This method does not use self.get_task_type as the intention is to get the MessageLog object before the
            **consume** method tries to do anything else. This means that if any later part of the process fails,
            the traceback and exception information can be stored to the MessageLog object for easier debugging.

        .. warning::
            If this method fails to find a matching MessageLog object, then the RabbitMQ message will be rejected.
            Depending on the configuration of your RabbitMQ queue, this may cause a loss of data. If you are
            implementing a custom consumer, then you should use
            `dead letter exchange <http://www.rabbitmq.com/dlx.html>`_ to preserve your message content

        """
        try:
            log = MessageLog.objects.get(uuid=properties.message_id)
        except ObjectDoesNotExist:
            return None

        if log.status == 'PUBLISHED':
            return log

        return None

    def connect(self) -> pika.SelectConnection:
        """
        Connects to the broker
        """
        self.logger.info('Connecting to %s', self._url)
        return pika.SelectConnection(pika.URLParameters(self._url), self.on_connection_open, stop_ioloop_on_close=False)

    def on_connection_open(self, connection: pika.SelectConnection) -> None:
        """
        Callback that gets called when the connection is opened. Adds callback in case of a closed connection, and
        establishes the connection channel

        The `connection` parameter here is not used, as `self.connection` is defined elsewhere, but is included so that
        the signature matches as per Pika's requirements
        """
        self.logger.info('Connection opened')
        self.connection.add_on_close_callback(self.on_connection_closed)
        self.connection.channel(on_open_callback=self.on_channel_open)

    def on_connection_closed(self, *args) -> None:
        """
        Callback that gets called when the connection is closed. Checks for the self.shutdown_requested parameter first,
        which is used to idenfity whether the shutdown has been requested by the user or not. If not, carrot attempts to
        reconnect

        All arguments sent to this callback come from Pika but are not required by Carrot
        """

        self.channel = None
        if self.shutdown_requested:
            self.logger.warning('Connection closed')
            self.connection.ioloop.stop()
            self.logger.warning('Connection IO loop stopped')
        else:
            self.logger.warning('Connection closed unexpectedly. Trying again in %i seconds' % self.reconnect_timeout)
            self.connection.add_timeout(self.reconnect_timeout, self.reconnect)

    def reconnect(self) -> None:
        """
        Reconnect to the broker in case of accidental disconnection
        """
        self.connection.ioloop.stop()

        if not self.shutdown_requested:
            self.connection = self.connect()
            self.connection.ioloop.start()

    def on_channel_open(self, channel: pika.channel.Channel) -> None:
        """
        This function is invoked when the channel is established. It adds a callback in case of channel closure, and
        establishes the exchange
        """
        self.logger.info('Channel opened')
        self.channel = channel
        self.channel.add_on_close_callback(self.on_channel_closed)
        self.channel.exchange_declare(self.on_exchange_declare, self.exchange, **self.exchange_arguments)

    def on_channel_closed(self, channel: pika.channel.Channel, reply_code: int, reply_text: str) -> None:
        """
        Called when the channel is closed. Raises a warning and closes the connection

        Parameters are require to match the signature used by Pika but are not required by Carrot
        """
        if not self.shutdown_requested:
            self.logger.warning('Consumer %s not running: %s' % (self.name, reply_text))

        else:
            self.logger.warning('Channel closed by client. Closing the connection')

        self.connection.close()

    def on_exchange_declare(self, *args) -> None:
        """
        Invoked when the exchange has been successfully established

        Parameters are require to match the signature used by Pika but are not required by Carrot
        """
        self.logger.info('Exchange declared')
        self.channel.queue_declare(self.on_queue_declare, self.queue, durable=self.durable,
                                   arguments=self.queue_arguments)

    def on_queue_declare(self, *args) -> None:
        """
        Invoked when the queue has been successfully declared

        Parameters are require to match the signature used by Pika but are not required by Carrot
        """
        self.channel.queue_bind(self.on_bind, self.queue, self.exchange)

    def on_bind(self, *args) -> None:
        """
        Invoked when the queue has been successfully bound to the exchange

        Parameters are require to match the signature used by Pika but are not required by Carrot
        """
        self.logger.info('Queue bound')
        self.start_consuming()

    def start_consuming(self) -> None:
        """
        The main consumer process. Attaches a callback to be invoked whenever there is a new message added to the queue.

        This method sets a channel prefetch count of zero to prevent dropouts
        """
        self.logger.info('Starting consumer %s' % self.name)
        self.channel.add_on_cancel_callback(self.on_consumer_cancelled)
        self.channel.basic_qos(prefetch_count=1)
        self._consumer_tag = self.channel.basic_consume(self.on_message, self.queue)

    def on_consumer_cancelled(self, method_frame: pika.frame.Method) -> None:
        """
        Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer receiving messages.

        """
        self.logger.warning('Consumer was cancelled remotely, shutting down: %r', method_frame)
        if self.channel:
            self.channel.close()

    def on_message(self, channel: pika.channel.Channel, method_frame: pika.frame.Method,
                   properties: pika.BasicProperties, body: bytes) -> None:
        """
        The process that takes a single message from RabbitMQ, converts it into a python executable and runs it,
        logging the output back to the assoicated :class:`carrot.models.MessageLog`

        """
        self.channel.basic_ack(method_frame.delivery_tag)
        log = self.__get_message_log(properties, body)
        if log:
            self.active_message_log = log
            log.status = 'IN_PROGRESS'
            log.save()
        else:
            self.logger.error('Unable to find a MessageLog matching the uuid %s. Ignoring this task' %
                              properties.message_id)
            return

        try:
            task_type = self.get_task_type(properties.headers, body)
        except KeyError as err:
            return self.fail(log, 'Unable to identify the task type because a key was not found in the message header: %s' %
                      err)

        self.logger.info('Consuming task %s, ID=%s' % (task_type, properties.message_id))

        try:
            func = self.serializer.get_task(properties, body)
        except (ValueError, ImportError, AttributeError) as err:
            return self.fail(log, err)

        try:
            args, kwargs = self.serializer.serialize_arguments(body.decode())

        except Exception as err:
            return self.fail(log, 'Unable to process the message due to an error collecting the task arguments: %s' % err)

        start_msg = '{} {} INFO:: Starting task {}.{}'.format(self.name,
                                                              timezone.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3],
                                                              func.__module__, func.__name__)
        self.logger.info(start_msg)
        self.task_log = [start_msg]
        task = LoggingTask(func, self.logger, self.name, *args, **kwargs)

        try:
            output = task.run()

            task_logs = task.get_logs()
            if task_logs:
                self.task_log.append(task_logs)
                self.logger.info(task_logs)

            success = '{} {} INFO:: Task {} completed successfully with response {}'.format(self.name,
                                                                                            timezone.now().strftime(
                                                                                                    "%Y-%m-%d %H:%M:%S,%f")[
                                                                                            :-3],
                                                                                            log.task, output)
            self.logger.info(success)
            self.task_log.append(success)

            log.status = 'COMPLETED'
            log.completion_time = timezone.now()

            if isinstance(output, dict):
                log.output = json.dumps(output)
            else:
                log.output = output

            log.log = '\n'.join(self.task_log)

            save_attempts = 0

            while True:
                save_attempts += 1

                try:
                    log.save()
                    self.active_message_log = None

                    break
                except OperationalError:
                    if save_attempts > 10:
                        raise OperationalError('Unable to access the database. This is probably because the number '
                                               'of carrot threads is too high. Either reduce the amount of '
                                               'scheduled tasks consumers, or increase the max number of '
                                               'connections supported by your database')
                    self.connection.sleep(10)

        except Exception as err:
            task_logs = task.get_logs()
            if task_logs:
                self.task_log.append(task_logs)
            self.fail(log, str(err))

    def stop_consuming(self) -> None:
        """
        Stops the consumer and cancels the channel
        """
        if self.channel:
            self.shutdown_requested = True
            self.logger.warning('Shutdown received. Cancelling the channel')
            self.channel.basic_cancel(self.on_cancel, self._consumer_tag)

    def on_cancel(self, *args) -> None:
        """
        Invoked when the channel cancel is completed.

        Parameters provided by Pika but not required by Carrot
        """
        self.logger.info('Closing the channel')
        self.channel.close()

    def run(self) -> None:
        """
        Process starts here
        """
        self.connection = self.connect()
        self.connection.ioloop.start()

    def stop(self) -> None:
        """
        Cleanly exit the Consumer
        """
        self.logger.info('Stopping')
        self.shutdown_requested = True
        if self.channel:
            self.stop_consuming()
            self.connection.ioloop.start()
            self.logger.info('Consumer closed')
        else:
            self.logger.warning('Not running!')

    def close_connection(self) -> None:
        """This method closes the connection to RabbitMQ."""
        self.logger.info('Closing connection')
        self.connection.close()


class ListHandler(logging.Handler):
    """
    A :class:`logging.Handler` that records each log entry to a python list object, provided that the entry is coming
    from the correct thread.

    Allows for task-specific logging

    """

    def __init__(self, thread_name: str, level: int):
        self.output: List[str] = []
        self.thread_name = thread_name
        super(ListHandler, self).__init__(level)

    def emit(self, record: logging.LogRecord):
        msg = self.format(record)
        if msg.startswith(self.thread_name):
            self.output.append(msg)

    def parse_output(self) -> str:
        return '\n'.join([str(line) for line in self.output])


class LoggingTask(object):
    """
    Turns a function into a class with :meth:`.run()` method, and attaches a :class:`ListHandler` logging handler
    """

    def __init__(self, task: Callable, logger: logging.Logger, thread_name: str, *args, **kwargs):
        self.task = task
        self.args = args
        self.kwargs = kwargs

        self.logger = logger
        self.thread_name = thread_name
        self.stream_handler = ListHandler(thread_name, self.logger.getEffectiveLevel())
        self.stream_handler.setLevel(self.logger.getEffectiveLevel())
        formatter = logging.Formatter(LOGGING_FORMAT)
        self.stream_handler.setFormatter(formatter)

        self.logger.addHandler(self.stream_handler)

        self._keep_alive = None

    def run(self) -> Callable:
        output = self.task(*self.args, **self.kwargs)
        return output

    def get_logs(self) -> Optional[str]:
        try:
            self.logger.removeHandler(self.stream_handler)
            return self.stream_handler.parse_output()
        except:
            pass
        return None


class ConsumerSet(object):
    """
    Creates and starts 1 or more `.Consumer` objects. All consumers must belong to the same queue
    """
    durable = True
    queue_arguments = {'x-max-priority': 255}
    exchange_arguments: Dict[str, Any] = {}

    @staticmethod
    def get_consumer_class(consumer_class: str) -> Type[Consumer]:
        """
        Returns a `Consumer` object from a string using dynamic imports
        """
        module = '.'.join(consumer_class.split('.')[:-1])
        _cls = consumer_class.split('.')[-1]
        mod = importlib.import_module(module)
        return getattr(mod, _cls)

    def __init__(self, host: VirtualHost, queue: str, logger: logging.Logger, concurrency: int = 1,
                 name: str = 'consumer',
                 consumer_class: str = 'carrot.consumer.Consumer'):
        self.logger = logger
        self.host = host
        self.connection = host.blocking_connection
        self.channel = self.connection.channel()
        self.queue = queue

        self.concurrency = concurrency
        self.name = '%s-%s' % (self.queue, name)
        self.consumer_class = self.get_consumer_class(consumer_class)
        self.threads: List[Consumer] = []

        try:
            queue_settings = [q for q in settings.CARROT.get('queues', []) if q.get('name', None) == self.queue]
        except AttributeError:
            queue_settings = [{}]

        if queue_settings:
            q_settings = queue_settings[0]
            if q_settings.get('durable', None):
                self.durable = q_settings['durable']

            if q_settings.get('queue_arguments', None):
                self.queue_arguments = q_settings['queue_arguments']

            if q_settings.get('exchange_arguments', None):
                self.exchange_arguments = q_settings['exchange_arguments']

    def stop_consuming(self) -> None:
        """
        Stops all running threads. Loops through the threads twice - firstly, to set the signal to **False** on all
        threads, secondly to wait for them all to finish

        If a single loop was used here, the latter threads could still consume new tasks while the parent process waited
        for the earlier threads to finish. The second loop allows for quicker consumer stoppage and stops all consumers
        from consuming new tasks from the moment the signal is received
        """
        for t in self.threads:
            t.stop()

        for t in self.threads:
            print('Closing consumer %s' % t)
            t.join()
            print('Closed consumer %s' % t)

    def start_consuming(self) -> None:
        """
        Creates a thread for each concurrency level, e.g. if concurrency is set to 5, 5 threads are created.

        A :class:`.Consumer` is attached to each thread and is started
        """
        for i in range(0, self.concurrency):
            consumer = self.consumer_class(host=self.host, queue=self.queue, logger=self.logger,
                                           name='%s-%i' % (self.name, i + 1),
                                           durable=self.durable, queue_arguments=self.queue_arguments,
                                           exchange_arguments=self.exchange_arguments)
            self.threads.append(consumer)
            consumer.start()
