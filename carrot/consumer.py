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


LOGGING_FORMAT = '%(threadName)-10s %(asctime)-10s %(levelname)s:: %(message)s'


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


class KeepAlive(threading.Thread):
    """
    This thread is started every time carrot executes a function, and sends a heartbeat to RabbitMQ so as to avoid
    dropping the connection (which can happen with long-running functions)
    """
    def __init__(self, connection):
        threading.Thread.__init__(self)
        self.connection = connection
        self.keep_alive = True

    def run(self):
        if self.keep_alive:
            self.connection.sleep(0.1)


class LoggingTask(object):
    """
    Turns a function into a class with :meth:`.run()` method, and attaches a :class:`KeepAlive` object and a
    :class:`ListHandler` logging handler
    """
    def __init__(self, task, logger, thread_name, connection, *args, **kwargs):
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

        self._keep_alive = None
        self.connection = connection

    def keep_alive(self):
        self._ka = KeepAlive(self.connection)
        self._ka.start()

    def stop_keep_live(self):
        self._ka.keep_alive = False
        self._ka.join(1)

    def run(self):
        self.keep_alive()
        output = self.task(*self.args, **self.kwargs)
        self.stop_keep_live()
        return output

    def get_logs(self):
        try:
            self.logger.removeHandler(self.stream_handler)
            return self.stream_handler.parse_output()
        except:
            return


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
                log.status = 'IN_PROGRESS'
                log.save()
                self.channel.basic_ack(method_frame.delivery_tag)
            except ObjectDoesNotExist:
                self.logger.error('Unable to find a MessageLog matching the uuid %s. Ignoring this task' %
                                  properties.message_id)
                self.channel.basic_nack(method_frame.delivery_tag, requeue=False)
                return

            try:
                task_type = self.get_task_type(properties.headers, body)
            except KeyError as err:
                self.fail(log, 'Unable to identify the task type because a key was not found in the message header: %s'
                          % err)
                return

            self.logger.info('Consuming task %s, ID=%s' % (task_type, properties.message_id))

            try:
                func = self.serializer.get_task(properties, body)
            except (ValueError, ModuleNotFoundError, AttributeError) as err:
                self.fail(log, err)
                return

            try:
                args, kwargs = self.serializer.serialize_arguments(body.decode())

            except Exception as err:
                self.fail(log,
                          'Unable to process the message due to an error collecting the task arguments: %s' % err)
                return

            start_msg = '{} {} INFO:: Starting task {}.{}'.format(self.name,
                                                             timezone.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3],
                                                             func.__module__, func.__name__)
            self.logger.info(start_msg)
            self.task_log = [
                start_msg
            ]
            task = LoggingTask(func, self.logger, self.name, self.connection, *args, **kwargs)

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

    def fail(self, log, err):
        """
        This function is called if there is any kind of error with the `.consume()` function

        :param MessageLog log: the associated MessageLog object
        :param str err: the exception

        The exception message is logged, and the MessageLog is updated with the result

        """
        self.logger.error('Task %s failed due to the following exception: %s' % (log.task, err))

        if self.task_log:
            log.log = '\n'.join(self.task_log)

        log.status = 'FAILED'
        log.failure_time = timezone.now()
        log.exception = err
        log.traceback = traceback.format_exc()
        log.save()

    def run(self):
        """
        The consume process. Waits for a message then calls :meth:`.consume' when it finds one.

        When :prop:`.signal` is set to False (which can be done by the parent :class:`.ConsumerSet` objects
        :meth:`.ConsumerSet.stop` method), this is a break point that stops the consumer from running and terminates
        the connection
        """
        self.logger.info('Started consumer %s' % self.name)
        for message in self.channel.consume(self.queue or 'default', inactivity_timeout=1):
            if not self.signal:
                self.channel.cancel()
                return self.connection.close()

            self.connection.sleep(0.1)

            if message:
                method_frame, header_frame, body = message
                self.consume(method_frame, header_frame, body)


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

    def stop_consuming(self):
        """
        Stops all running threads. Loops through the threads twice - firstly, to set the signal to **False** on all
        threads, secondly to wait for them all to finish

        If a single loop was used here, the latter threads could still consume new tasks while the parent process waited
        for the earlier threads to finish. The second loop allows for quicker consumer stoppage and stops all consumers
        from consuming new tasks from the moment the signal is received
        """
        print('%i thread(s) to close' % len(self.threads))
        for t in self.threads:
            t.signal = False

        for t in self.threads:
            print('Closing thread %s' % t)
            t.join()
            print('Closed thread %s' % t)

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


