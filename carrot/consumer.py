"""
This module provides a backend API for creating Consumers and Consumer Sets

"""

import json
from carrot.models import MessageLog
import traceback
import threading
import logging
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
import importlib
from carrot.objects import DefaultMessageSerializer
from django.db.utils import OperationalError
import pika
import time
from django.conf import settings


LOGGING_FORMAT = '%(threadName)-10s %(asctime)-10s %(levelname)s:: %(message)s'


class Consumer(threading.Thread):
    """
    An individual Consumer object. This class is run on a detached thread and watches a specific RabbitMQ queue for
    messages, and consumes them when they appear. Multiple Consumers can be linked to the same queue using a
    :class:`.ConsumerSet` object.
    """

    serializer = DefaultMessageSerializer()
    reconnect_timeout = 5
    task_log = []
    queue_arguments = {}
    exchange_arguments = {}
    active_message_log = None
    remaining_save_attempts = 10
    get_message_attempts = 50

    def __init__(self, host, queue, logger, name, durable=True, queue_arguments=None, exchange_arguments=None):
        """
        :param host: the host the queue to consume from is attached to
        :type host: :class:`carrot.objects.VirtualHost`
        :param str queue: the queue to consume from
        :param logger: the logging object
        :param name: the name of the consumer

        """
        super(Consumer, self).__init__()

        if queue_arguments is None:
            queue_arguments = {}

        if not exchange_arguments:
            exchange_arguments = {}

        self.failure_callbacks = []
        self.name = name
        self.logger = logger
        self.queue = queue
        self.exchange = queue

        self.connection = None
        self.channel = None
        self.shutdown_requested = False
        self._consumer_tag = None
        self._url = str(host)

        self.queue_arguments = queue_arguments
        self.exchange_arguments = exchange_arguments
        self.durable = durable

    def add_failure_callback(self, cb):
        self.failure_callbacks.append(cb)

    def fail(self, log, err):
        """
        This function is called if there is any kind of error with the `.consume()` function

        :param MessageLog log: the associated MessageLog object
        :param str err: the exception

        The exception message is logged, and the MessageLog is updated with the result

        """
        self.logger.error('Task %s failed due to the following exception: %s' % (log.task, err))

        for cb in self.failure_callbacks:
            try:
                cb(log, err)
                self.task_log.append('Failure callback %s succeeded' % str(cb))
            except Exception as err:
                self.task_log.append('Failure callback %s failed due to an error: %s' % (str(cb), err))

        if log.pk:
            if self.task_log:
                log.log = '\n'.join(self.task_log)

            log.status = 'FAILED'
            log.failure_time = timezone.now()
            log.exception = err
            log.traceback = traceback.format_exc()
            log.save()

    def get_task_type(self, properties, body):
        """
        Identifies the task type, by looking up the attribute **self.task_type** in the message properties

        :param properties: the message properties
        :param body: the message body. Not used by default, but provided so that the method can be extended if necessary

        :return: The task type as a string, e.g. *myapp.mymodule.mytask*

        """
        return properties[self.serializer.type_header]

    def __get_message_log(self, properties, body):
        for i in range(0, self.get_message_attempts):
            log = self.get_message_log(properties, body)

            if log:
                return log
            time.sleep(0.1)

    def get_message_log(self, properties, body):
        """
        Finds and returns the :class:`carrot.models.MessageLog` object associated with a RabbitMQ message

        By default, carrot finds this retrieving the MessageLog UUID from the RabbitMQ message properties.message_id
        attribute.

        This method can be extended by custom consumers. For example, if you are attempting to consume from a RabbitMQ
        queue containing messages that do not come from your Carrot instance, you may want to extend this method to
        create, instead of get, a MessageLog object

        :param properties: the message properties
        :param body: the message body. This is not used by default, but is included so that the function can be
                     extended in custom consumers.

        :rtype: class:`carrot.models.MessageLog` or None

        In order to avoid different consumers picking up the same message, MessageLogs are only
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
            return

        if log.status == 'PUBLISHED':
            return log

    def connect(self):
        """
        Connects to the broker

        :rtype: pika.SelectConnection

        """
        self.logger.info('Connecting to %s', self._url)
        return pika.SelectConnection(pika.URLParameters(self._url), self.on_connection_open, stop_ioloop_on_close=False)

    def on_connection_open(self, connection):
        """
        Callback that gets called when the connection is opened. Adds callback in case of a closed connection, and
        establishes the connection channel

        :param connection: Sent by default by pika but not used by carrot
        :type connection: pika.SelectConnection

        """
        self.logger.info('Connection opened')
        self.connection.add_on_close_callback(self.on_connection_closed)
        self.connection.channel(on_open_callback=self.on_channel_open)

    def on_connection_closed(self, *args):
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

    def reconnect(self):
        """
        Reconnect to the broker in case of accidental disconnection
        """
        self.connection.ioloop.stop()

        if not self.shutdown_requested:
            self.connection = self.connect()
            self.connection.ioloop.start()

    def on_channel_open(self, channel):
        """
        This function is invoked when the channel is established. It adds a callback in case of channel closure, and
        establishes the exchange

        :param pika.channel.Channel channel: The channel object

        """
        self.logger.info('Channel opened')
        self.channel = channel
        self.channel.add_on_close_callback(self.on_channel_closed)
        self.channel.exchange_declare(self.on_exchange_declare, self.exchange, **self.exchange_arguments)

    def on_channel_closed(self, channel, reply_code, reply_text):
        """
        Called when the channel is closed. Raises a warning and closes the connection

        Parameters are provided by Pika but not required by Carrot
        """
        if not self.shutdown_requested:
            self.logger.warning('Consumer %s not running: %s' % (self.name, reply_text))
            if self.active_message_log:
                self.active_message_log.requeue()
        else:
            self.logger.warning('Channel closed by client. Closing the connection')

        self.connection.close()

    def on_exchange_declare(self, *args):
        """
        Invoked when the exchange has been successfully established

        Parameters are provided by Pika but not required by Carrot
        """
        self.logger.info('Exchange declared')
        self.channel.queue_declare(self.on_queue_declare, self.queue, durable=self.durable,
                                   arguments=self.queue_arguments)

    def on_queue_declare(self, *args):
        """
        Invoked when the queue has been successfully declared

        Parameters are provided by Pika but not required by Carrot
        """
        self.channel.queue_bind(self.on_bind, self.queue, self.exchange)

    def on_bind(self, *args):
        """
        Invoked when the queue has been successfully bound to the exchange

        Parameters are provided by Pika but not required by Carrot
        """
        self.logger.info('Queue bound')
        self.start_consuming()

    def start_consuming(self):
        """
        The main consumer process. Attaches a callback to be invoked whenever there is a new message added to the queue
        """
        self.logger.info('Starting consumer %s' % self.name)
        self.channel.add_on_cancel_callback(self.on_consumer_cancelled)
        self._consumer_tag = self.channel.basic_consume(self.on_message, self.queue)

    def on_consumer_cancelled(self, method_frame):
        """
        Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer receiving messages.

        :param pika.frame.Method method_frame: The Basic.Cancel frame

        """
        self.logger.warning('Consumer was cancelled remotely, shutting down: %r', method_frame)
        if self.channel:
            self.channel.close()

    def on_message(self, channel, method_frame, properties, body):
        """
        The process that takes a single message from RabbitMQ, converts it into a python executable and runs it,
        logging the output back to the assoicated :class:`carrot.models.MessageLog`

        :param channel: not used
        :type channel: pika.channel.Channel
        :param method_frame: contains the delivery tag
        :type method_frame: pika.Spec.Basic.Deliver
        :param properties: the message properties
        :type properties: pika.Spec.BasicProperties
        :param bytes body: The message body
        """
        log = self.__get_message_log(properties, body)
        if log:
            self.active_message_log = log
            self.channel.basic_ack(method_frame.delivery_tag)
            log.status = 'IN_PROGRESS'
            log.save()
        else:
            self.logger.error('Unable to find a MessageLog matching the uuid %s. Ignoring this task' %
                              properties.message_id)
            self.channel.basic_nack(method_frame.delivery_tag, requeue=False)
            return

        try:
            task_type = self.get_task_type(properties.headers, body)
        except KeyError as err:
            self.fail(log, 'Unable to identify the task type because a key was not found in the message header: %s' %
                      err)
            return

        self.logger.info('Consuming task %s, ID=%s' % (task_type, properties.message_id))

        try:
            func = self.serializer.get_task(properties, body)
        except (ValueError, ImportError, AttributeError) as err:
            self.fail(log, err)
            return

        try:
            args, kwargs = self.serializer.serialize_arguments(body.decode())

        except Exception as err:
            self.fail(log, 'Unable to process the message due to an error collecting the task arguments: %s' % err)
            return

        start_msg = '{} {} INFO:: Starting task {}.{}'.format(self.name,
                                                              timezone.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3],
                                                              func.__module__, func.__name__)
        self.logger.info(start_msg)
        self.task_log = [
            start_msg
        ]
        task = LoggingTask(func, self.logger, self.name, *args, **kwargs)

        try:
            output = task.run()

            self.task_log.append(task.get_logs())
            self.logger.info(task.get_logs())

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
            self.task_log.append(task.get_logs())
            self.fail(log, str(err))

    def stop_consuming(self):
        """
        Stops the consumer and cancels the channel
        """
        if self.channel:
            self.shutdown_requested = True
            self.logger.warning('Shutdown received. Cancelling the channel')
            self.channel.basic_cancel(self.on_cancel, self._consumer_tag)

    def on_cancel(self, *args):
        """
        Invoked when the channel cancel is completed.

        Parameters provided by Pika but not required by Carrot

        """
        self.logger.info('Closing the channel')
        self.channel.close()

    def run(self):
        """
        Process starts here
        """
        self.connection = self.connect()
        self.connection.ioloop.start()

    def stop(self):
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

    def close_connection(self):
        """This method closes the connection to RabbitMQ."""
        self.logger.info('Closing connection')
        self.connection.close()


class ListHandler(logging.Handler):
    """
    A :class:`logging.Handler` that records each log entry to a python list object, provided that the entry is coming
    from the correct thread.

    Allows for task-specific logging

    """
    def __init__(self, thread_name, level):
        self.output = []
        self.thread_name = thread_name
        super(ListHandler, self).__init__(level)

    def emit(self, record):
        msg = self.format(record)
        if msg.startswith(self.thread_name):
            self.output.append(msg)

    def parse_output(self):
        return '\n'.join([str(line) for line in self.output])


class LoggingTask(object):
    """
    Turns a function into a class with :meth:`.run()` method, and attaches a :class:`ListHandler` logging handler
    """
    def __init__(self, task, logger, thread_name, *args, **kwargs):
        self.task = task
        self.args = args
        self.kwargs = kwargs

        self.logger = logger
        self.thread_name = thread_name
        self.out = []
        self.stream_handler = ListHandler(thread_name, self.logger.getEffectiveLevel())
        self.stream_handler.setLevel(self.logger.getEffectiveLevel())
        formatter = logging.Formatter(LOGGING_FORMAT)
        self.stream_handler.setFormatter(formatter)

        self.logger.addHandler(self.stream_handler)

        self._keep_alive = None

    def run(self):
        output = self.task(*self.args, **self.kwargs)
        return output

    def get_logs(self):
        try:
            self.logger.removeHandler(self.stream_handler)
            return self.stream_handler.parse_output()
        except:
            return


class ConsumerSet(object):
    """
    Creates and starts a number of :class:`.Consumer` objects. All consumers must belong to the same queue

    :param host: The virtual host where the queue belongs
    :param queue: The queue name
    :param concurrency: the number of consumers to create. Defaults to 1
    :param name: the name to assign to the individual consumers. Will be rendered as *Consumer-1, Consumer-2,* etc.
    :param logfile: the path to the log file. Defaults to carrot.log
    :param loglevel: the logging level. Defaults to logging.DEBUG

    """
    durable = True
    queue_arguments = {'x-max-priority': 255}
    exchange_arguments = {}

    @staticmethod
    def get_consumer_class(consumer_class):
        module = '.'.join(consumer_class.split('.')[:-1])
        _cls = consumer_class.split('.')[-1]
        mod = importlib.import_module(module)
        return getattr(mod, _cls)

    def __init__(self, host, queue, logger, concurrency=1, name='consumer', consumer_class='carrot.consumer.Consumer'):
        self.logger = logger
        self.host = host
        self.connection = host.blocking_connection
        self.channel = self.connection.channel()
        self.queue = queue

        self.concurrency = concurrency
        self.name = '%s-%s' % (self.queue, name)
        self.consumer_class = self.get_consumer_class(consumer_class)
        self.threads = []

        try:
            queue_settings = [q for q in settings.CARROT.get('queues', []) if q.get('name', None) == self.queue]
        except AttributeError:
            queue_settings = {}

        if queue_settings:
            q_settings = queue_settings[0]
            if q_settings.get('durable', None):
                self.durable = q_settings['durable']

            if q_settings.get('queue_arguments', None):
                self.queue_arguments = q_settings['queue_arguments']

            if q_settings.get('exchange_arguments', None):
                self.exchange_arguments = q_settings['exchange_arguments']

    def stop_consuming(self):
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

    def start_consuming(self):
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


