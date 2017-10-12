"""
This module provides a backend API for creating Consumers and Consumer Sets

"""

import json
from carrot.models import MessageLog
import traceback
import uuid
import threading
import logging
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
import importlib
import sys
from carrot.objects import DefaultMessageSerializer
from django.db.utils import OperationalError
import time


LOGGING_FORMAT = '%(threadName)-10s %(asctime)s:: %(message)s'


class ListHandler(logging.Handler):
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
    def __init__(self, task, logger, thread_name, *args, **kwargs):
        self.task = task
        self.args = args
        self.kwargs = kwargs

        self.logger = logger
        self.thread_name = thread_name
        self.out = []
        self.stream_handler = ListHandler(thread_name, logger.getEffectiveLevel())
        self.stream_handler.setLevel(logger.getEffectiveLevel())
        formatter = logging.Formatter(LOGGING_FORMAT)
        self.stream_handler.setFormatter(formatter)

        self.logger.addHandler(self.stream_handler)

        self._run = False

    def run(self):
        output = self.task(*self.args, **self.kwargs)
        self._run = True
        return output

    def get_logs(self):
        if self._run:
            self.logger.removeHandler(self.stream_handler)
            return self.stream_handler.parse_output()


class Consumer(threading.Thread):
    """
    An individual Consumer object. This class is run on a detached thread and watches a specific RabbitMQ queue for
    messages, and consumes them when they appear. Multiple Consumers can be linked to the same queue using a
    :class:`.ConsumerSet` object.

    This object takes the following parameters:

        :param thread_id: an identifier for the thread (a uuid)
        :param name: the name of the Consumer. Note that all Consumers in the same :class:`.ConsumerSet` are assigned
            the same name, e.g. Consumer-1, Consumer-2
        :param host: The virtual host :class:`carrot.objects.VirtualHost` object where the queue resides
        :param queue: The name of the linked queue
        :param logger: The log object from the parent process

    __init__ also specifies the following attributes:
        - **connection**: the blocking connection of the :class:`carrot.objects.VirtualHost`
        - **task_log**: a list of log entries specific to the task being executed. This list is cleared every time
          the consumer consumes a new message
        - **signal**: This is a flag that allows the consumer to run, and is initially set to **True**. When the parent
          process is killed, the parent process sets the signal to **False** which is intercepted by various break
          points in the consumer, causing the :meth:`.run` method to return

    """
    serializer = DefaultMessageSerializer()

    def __init__(self, thread_id, name, host, queue, logger, run_once=False):
        threading.Thread.__init__(self)
        self.logger = logger
        self.thread_id = thread_id
        self.name = name
        self.host = host
        self.connection = host.blocking_connection
        self.channel = self.connection.channel()

        self.queue = queue
        self.task_log = []
        self.signal = True
        self.run_once = run_once

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

        :return: a :class:`carrot.models.MessageLog` object

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
        return MessageLog.objects.get(uuid=properties.message_id)

    def get_task_type(self, properties, body):
        """
        Identifies the task type, by looking up the attribute **self.task_type** in the message properties

        :param properties: the message properties
        :param body: the message body. Not used by default, but provided so that the method can be extended if necessary

        :return: The task type as a string, e.g. *myapp.mymodule.mytask*

        """
        return properties[self.serializer.type_header]

    def consume(self, method_frame, properties, body):
        """
        On finding a message in the queue, this function is called, which executes the task. The following actions
        happen in this function:
            #. The value of *self.task_log* is cleared
            #. Carrot searches for a :class:`carrot.models.MessageLog` object with a guid matching the message ID. If
               none can be found, the message is rejected. Once the MessageLog has been found, any subsequent exceptions
               can be stored against it for debugging purposes
            #. The task type is identified
            #. The python function to be executed is identified
            #. The positional and keyword arguments are identified
            #. The function is wrapped as a :class:`.LoggingTask` object and executed
            #. If the function runs successfully, the message is acknowledged. Otherwise, the message is rejected
            #. The associated :class:`carrot.models.MessageLog` object is updated with the task log, output, exception
               traceback and status (as necessary).

        ..warning:
            Note that if you have a very high number of database connections (in other words, a very high number of
            consumers or a very high number of tasks scheduled to run at the same time), then carrot may encounter a
            Database exception on saving the output of a task to the associated :class:`carrot.models.MessageLog`.
            Carrot waits 10 seconds then retries a maximum of 10 times before raising the exception, as the database
            may become unblocked once other connections are cleared. If more than 10 retries are required, Carrot will
            be unable to save the output of the task to the :class:`carrot.models.MessageLog`. If this happens, you
            should either reduce the amount of tasks you are trying to process at the same time, or edit the maximum
            number of database connections supported by your Django project's database

        """
        if self.signal:
            try:
                log = self.get_message_log(properties, body)
            except ObjectDoesNotExist:
                self.logger.error('Unable to find a MessageLog matching the uuid %s. Ignoring this task' %
                                  properties.message_id)
                self.channel.basic_nack(method_frame.delivery_tag, requeue=False)
                return

            try:
                task_type = self.get_task_type(properties.headers, body)
            except KeyError as err:
                self.fail(log, 'Unable to identify the task type because a key was not found in the message header: %s'
                          % err, method_frame.delivery_tag)
                return

            self.logger.info('Consuming task %s, ID=%s' % (task_type, properties.message_id))

            try:
                func = self.serializer.get_task(properties, body)
            except (ValueError, ModuleNotFoundError, AttributeError) as err:
                self.fail(log, err, method_frame.delivery_tag)
                return

            try:
                args, kwargs = self.serializer.serialize_arguments(body.decode())

            except Exception as err:

                self.fail(log,
                          'Unable to process the message due to an error parsing the message body to JSON: %s' % err,
                          method_frame.delivery_tag)
                return

            try:
                start_msg = '{} {}:: Starting task {}.{}'.format(self.name,
                                                                 timezone.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3],
                                                                 func.__module__, func.__name__)
                self.logger.info(start_msg)
                self.task_log = [
                    start_msg
                ]
                task = LoggingTask(func, self.logger, self.name, *args, **kwargs)

                output = task.run()
                self.task_log.append(task.get_logs())
                self.logger.info(task.get_logs())

                success = '{} {}:: Task {} completed successfully with response {}'.format(self.name,
                                                                                           timezone.now().strftime(
                                                                                               "%Y-%m-%d %H:%M:%S,%f")[
                                                                                           :-3],
                                                                                           log.task, output)
                print(success)
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
                        break
                    except OperationalError:
                        if save_attempts > 10:
                            raise OperationalError('Unable to access the database. This is probably because the number '
                                                   'of carrot threads is too high. Either reduce the amount of '
                                                   'scheduled tasks consumers, or increase the max number of '
                                                   'connections supported by your database')
                        time.sleep(10)

                self.channel.basic_ack(method_frame.delivery_tag)

            except Exception as err:
                self.fail(log, 'An unknown error occurred: %s' % err, method_frame.delivery_tag)

    def fail(self, log, err, delivery_tag):
        """
        This function is called if there is any kind of error with the `.consume()` function

        :param log: the associated MessageLog object
        :param err: the exception
        :param delivery_tag: the message delivery tag

        The exception message is logged, and the message is rejected. The MessageLog is also updated with the result

        """
        self.logger.error('Task %s failed due to the following exception: %s' % (log.task, err))
        self.channel.basic_nack(delivery_tag, requeue=False)
        log.status = 'FAILED'
        log.failure_time = timezone.now()
        log.exception = err
        log.traceback = traceback.format_exc()
        log.save()

    def run(self):
        """
        The actual thread process. Waits for messages to be ready to consume
        """
        self.logger.info('Started consumer %s' % self.name)

        while True:
            if not self.signal:
                break
            method_frame, header_frame, body = self.channel.basic_get(self.queue or 'default')
            if method_frame:
                self.consume(method_frame, header_frame, body)
                if self.run_once:
                    break


class ConsumerSet(object):
    """
    Creates and starts a number of :class:`.Consumer` objects. All consumers must belong to the same queue

        :param host: The virtual host where the queue belongs
        :param queue: The queue name
        :param concurrency: the number of consumers to create. Defaults to 1
        :param name: the name to assign to the individual consumers. Will be rendered as *Consumer-1, Consumer-2,* etc.
        :param logfile: the path to the log file. Defaults to carrot.log
        :param loglevel: the logging level. Defaults to logging.INFO

    """

    @staticmethod
    def get_consumer_class(consumer_class):
        module = '.'.join(consumer_class.split('.')[:-1])
        _cls = consumer_class.split('.')[-1]
        mod = importlib.import_module(module)
        return getattr(mod, _cls)

    def __init__(self, host, queue, concurrency=1, name='consumer', logfile='/var/log/carrot.log',
                 consumer_class='carrot.consumer.Consumer', loglevel='DEBUG'):
        loglevel = getattr(logging, loglevel)

        self.logfile = logfile
        self.logger = logging.getLogger('carrot')
        self.logger.setLevel(loglevel)

        file_handler = logging.FileHandler(self.logfile)
        file_handler.setLevel(loglevel)

        streaming_handler = logging.StreamHandler(sys.stdout)
        streaming_handler.setLevel(loglevel)

        formatter = logging.Formatter(LOGGING_FORMAT)
        streaming_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(streaming_handler)
        self.host = host
        self.connection = host.blocking_connection
        self.channel = self.connection.channel()
        self.queue = queue
        self.concurrency = concurrency
        self.name = name
        self.consumer_class = self.get_consumer_class(consumer_class)
        self.threads = []

    def stop_consuming(self):
        print('%i thread(s) to close' % len(self.threads))
        for t in self.threads:
            print('Closing thread %s' % t)
            t.signal = False
            t.join()
            print('Closed thread %s' % t)

        sys.exit()

    def start_consuming(self):
        """
        Creates a thread for each concurrency level, e.g. if concurrency is set to 5, 5 threads are created.

        A :class:`.Consumer` is attached to each thread and is started
        """
        for i in range(0, self.concurrency):
            thread_id = str(uuid.uuid4())
            thread = self.consumer_class(thread_id, '%s-%i' % (self.name, i + 1), self.host, self.queue, self.logger)
            self.threads.append(thread)
            thread.start()


