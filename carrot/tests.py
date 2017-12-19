import mock
import logging

from django.test import TestCase
from carrot.consumer import Consumer
from carrot.objects import VirtualHost, DefaultMessageSerializer
from carrot.utilities import (
    create_message
)
from carrot.models import MessageLog
from carrot import DEFAULT_BROKER
from django.test.utils import override_settings


ALT_CARROT = {
    'default_broker': DEFAULT_BROKER,
    'queues': [
        {
            'name': 'test',
            'host': DEFAULT_BROKER,
            'consumer_class': 'carrot.consumer.Consumer',
        },
        {
            'name': 'default',
            'host': DEFAULT_BROKER,
            'consumer_class': 'carrot.consumer.Consumer',
        }
    ],
    'task_modules': ['carrot.tests', 'carrot.invalid']
}


def test_task(*args, **kwargs):
    return


def dict_task(*args, **kwargs):
    return {'blah': True}


def failing_task(*args, **kwargs):
    raise Exception('test')


def mock_messagelog(*args, **kwargs):
    class MockMessageLog(object):
        def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
            from django.db.utils import OperationalError
            raise OperationalError('test')

    return MockMessageLog

class Properties(object):
    message_id = 1234
    delivery_tag = 1
    headers = {}


class FailingSerializer(DefaultMessageSerializer):
    failing_method = 'serialize_arguments'

    def serialize_arguments(self, body):
        if self.failing_method == 'serialize_arguments':
            raise AttributeError('test error message')
        super(FailingSerializer, self).serialize_arguments(body)

    def get_task(self, properties, body):
        if self.failing_method == 'get_task':
            raise AttributeError('test error message')
        super(FailingSerializer, self).get_task(properties, body)


def mock_connection(*args, **kwargs):
    class MockLoop(object):
        def stop(self):
            pass

        def start(self):
            pass

    class MockChannel(object):
        def __init__(self, *args, **kwargs):
            pass

        def add_on_close_callback(self):
            return

        @staticmethod
        def close(*args, **kwargs):
            return

        def exchange_declare(self, callback, exchange=None, **kwargs):
            return

        def basic_publish(self, **kwargs):
            return

        def queue_declare(self, *args, **kwargs):
            return

        def queue_bind(self, *args, **kwargs):
            return

        def add_on_cancel_callback(self, *args, **kwargs):
            return

        def basic_consume(self, *args, **kwargs):
            return

        def basic_nack(self, *args, **kwargs):
            return

        def basic_ack(self, *args, **kwargs):
            return

    class MockConnection(object):
        def __init__(self, *args, **kwargs):
            self.channel = MockChannel
            self.ioloop = MockLoop()

        def connect(self):
            return self

        def add_on_close_callback(self, callback):
            return
        
        @property
        def on_channel_open(self):
            return

        def add_timeout(self, reconnect_timeout, timeout):
            return

        def close(self):
            return

    return MockConnection


logger = logging.getLogger('carrot')


class CarrotTestCase(TestCase):
    @mock.patch('pika.SelectConnection', new_callable=mock_connection)
    @mock.patch('pika.BlockingConnection', new_callable=mock_connection)
    def test_consumer(self, *args):
        consumer = Consumer(VirtualHost('amqp://guest:guest@localhost:5672/test'), 'test', logger, 'test')
        consumer.task_log = ['blah']
        log = MessageLog.objects.create(task='carrot.tests.test_task', uuid=1234, status='PUBLISHED', task_args='()')

        consumer.get_task_type({'type': 'carrot.tests.test_task'}, None)
        p = Properties()
        self.assertEqual(consumer.get_message_log(p, None), log)

        p.message_id = 4321
        consumer.get_message_log(p, None)

        consumer.fail(log, 'test error')

        consumer.connection = consumer.connect()
        consumer.run()
        consumer.reconnect()

        consumer.on_connection_open(consumer.connection)

        consumer.channel = consumer.connection.channel
        consumer.on_channel_open(consumer.channel)

        consumer.on_exchange_declare()
        consumer.on_queue_declare()
        consumer.on_bind()

        p.message_id = 1234

        consumer.on_message(consumer.channel, p, p, b'{}')

        log.status = 'PUBLISHED'
        log.save()

        consumer.on_message(consumer.channel, p, p, b'{}')

        p.headers = {'type':'carrot.tests.test_task'}
        log.delete()
        log = MessageLog.objects.create(task='carrot.tests.test_task', uuid=1234, status='PUBLISHED', task_args='()')
        consumer.on_message(consumer.channel, p, p, b'{}')

        log.delete()
        log = MessageLog.objects.create(task='carrot.tests.test_task', uuid=1234, status='PUBLISHED', task_args='()')

        with mock.patch('carrot.models.MessageLog', new_callable=mock_messagelog) as null:
            consumer.on_message(consumer.channel, p, p, b'{}')

        log.delete()
        p.headers = {'type':'carrot.tests.dict_task'}
        log = MessageLog.objects.create(task='carrot.tests.dict_task', uuid=1234, status='PUBLISHED', task_args='()')
        consumer.on_message(consumer.channel, p, p, b'{}')

        log.delete()
        p.headers = {'type':'carrot.tests.failing_task'}
        log = MessageLog.objects.create(task='carrot.tests.failing_task', uuid=1234, status='PUBLISHED', task_args='()')
        consumer.on_message(consumer.channel, p, p, b'{}')

        log.delete()
        log = MessageLog.objects.create(task='carrot.tests.test_task', uuid=1234, status='PUBLISHED', task_args='()')

        consumer.serializer = FailingSerializer()
        consumer.on_message(consumer.channel, p, p, b'{}')

        log.delete()
        log = MessageLog.objects.create(task='carrot.tests.test_task', uuid=1234, status='PUBLISHED', task_args='()')
        consumer.serializer.failing_method = 'get_task'
        consumer.on_message(consumer.channel, p, p, b'{}')

        consumer.active_message_log = log

        consumer.on_consumer_cancelled(1)
        consumer.on_channel_closed(consumer.channel, 1, 'blah')
        consumer.on_connection_closed(consumer.connection)

        consumer.shutdown_requested = True

        consumer.on_channel_closed(consumer.channel, 1, 'blah')
        consumer.on_connection_closed(consumer.connection)

