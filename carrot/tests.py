import mock
import logging
from carrot.mocks import MessageSerializer, Connection, Properties
from django.test import TestCase, RequestFactory
from django.test.utils import override_settings

from carrot.consumer import Consumer, ConsumerSet
from carrot.objects import VirtualHost
from carrot.models import MessageLog, ScheduledTask
from carrot.api import (failed_message_log_viewset, detail_message_log_viewset, scheduled_task_detail,
                        scheduled_task_viewset, task_list, validate_args, run_scheduled_task)

from carrot.utilities import (get_host_from_name, validate_task, create_scheduled_task, decorate_class_view,
                              decorate_function_view, purge_queue)
from django.core.exceptions import ObjectDoesNotExist
from carrot.views import MessageList

logger = logging.getLogger('carrot')


def test_task(*args, **kwargs):
    logger.info('test')
    return


def dict_task(*args, **kwargs):
    return {'blah': True}


def failing_task(*args, **kwargs):
    raise Exception('test')


def mock_connection(*args, **kwargs):
    return Connection


def mock_consumer(*args, **kwargs):
    from carrot.mocks import Consumer as MockConsumer
    return MockConsumer


class CarrotTestCase(TestCase):
    @mock.patch('pika.SelectConnection', new_callable=mock_connection)
    @mock.patch('pika.BlockingConnection', new_callable=mock_connection)
    def test_consumer(self, *args):
        consumer = Consumer(VirtualHost('amqp://guest:guest@localhost:5672/test'), 'test', logger, 'test')
        consumer.task_log = ['blah']
        log = MessageLog.objects.create(task='carrot.tests.test_task', uuid=1234, status='PUBLISHED', task_args='()')

        # consumer.get_task_type({'type': 'carrot.tests.test_task'}, None)
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
        consumer.on_channel_closed(consumer.channel, 1, 'blah')

        p.headers = {'type':'carrot.tests.test_task'}
        log.delete()
        log = MessageLog.objects.create(task='carrot.tests.test_task', uuid=1234, status='PUBLISHED', task_args='()')
        self.assertEqual(str(log), 'carrot.tests.test_task')
        consumer.on_message(consumer.channel, p, p, b'{}')

        log.delete()

        p.headers = {'type': 'carrot.tests.dict_task'}
        log = MessageLog.objects.create(task='carrot.tests.dict_task', uuid=1234, status='PUBLISHED', task_args='()')
        consumer.on_message(consumer.channel, p, p, b'{}')

        log.delete()
        p.headers = {'type':'carrot.tests.failing_task'}
        log = MessageLog.objects.create(task='carrot.tests.failing_task', uuid=1234, status='PUBLISHED', task_args='()')
        consumer.on_message(consumer.channel, p, p, b'{}')

        log.delete()
        log = MessageLog.objects.create(task='carrot.tests.test_task', uuid=1234, status='PUBLISHED', task_args='()')
        consumer.serializer = MessageSerializer(log)
        consumer.on_message(consumer.channel, p, p, b'{}')

        log.delete()
        log = MessageLog.objects.create(task='carrot.tests.test_task', uuid=1234, status='PUBLISHED', task_args='()')
        consumer.serializer.failing_method = 'get_task'
        consumer.on_message(consumer.channel, p, p, b'{}')

        consumer.active_message_log = log
        consumer.on_consumer_cancelled(1)

        consumer.stop()
        consumer.on_cancel()
        consumer.channel = None

        consumer.stop()

        consumer.close_connection()
        consumer.on_channel_closed(consumer.channel, 1, 'blah')
        consumer.on_connection_closed(consumer.connection)

        consumer.shutdown_requested = True

        consumer.on_channel_closed(consumer.channel, 1, 'blah')
        consumer.on_connection_closed(consumer.connection)

    @mock.patch('carrot.consumer.Consumer', new_callable=mock_consumer)
    @mock.patch('pika.BlockingConnection', new_callable=mock_connection)
    def test_consumer_set(self, *args):
        alt_settings = {
            'queues': [{
                'name': 'test',
                'durable': True,
                'queue_arguments': {'blah': True},
                'exchange_arguments': {'blah': True},
            }]
        }
        with override_settings(CARROT=alt_settings):
            cs = ConsumerSet(VirtualHost('amqp://guest:guest@localhost:5672/test'), 'test', logger)

            cs.start_consuming()

            cs.stop_consuming()

    @mock.patch('pika.BlockingConnection', new_callable=mock_connection)
    def test_api(self, *args):
        MessageLog.objects.create(task='carrot.tests.test_task', uuid=1234, status='FAILED', task_args='()')

        f = RequestFactory()
        r = f.delete('/api/message-logs/failed')

        failed_message_log_viewset(r)
        self.assertEqual(MessageLog.objects.filter(status='FAILED').count(), 0)
        r = f.get('/api/message-logs/failed')
        response = failed_message_log_viewset(r)
        self.assertEqual(response.data.get('count'), 0)

        MessageLog.objects.create(task='carrot.tests.test_task', uuid=1234, status='FAILED', task_args='()')
        r = f.put('/api/message-logs/failed')
        failed_message_log_viewset(r)

        log = MessageLog.objects.create(task='carrot.tests.test_task', uuid=1234, status='COMPLETED', task_args='()')
        r = f.delete('/api/message-logs/%s/' % log.pk)
        detail_message_log_viewset(r, pk=log.pk)

        log = MessageLog.objects.create(task='carrot.tests.test_task', uuid=1234, status='FAILED', task_args='()')
        r = f.put('/api/message-logs/%s/' % log.pk)
        detail_message_log_viewset(r, pk=log.pk)

        data = {
            'task': 'carrot.tests.test_task',
            'interval_count': 1,
            'active': True,
            'queue': 'test',
            'interval_type': 'hours',
            'task_args': '(True,)',
            'content': '{"blah": true}'

        }
        alt_settings = {
            'task_modules': ['carrot.tests', 'invalid.module']
        }
        with override_settings(CARROT=alt_settings):

            r = f.post('/api/scheduled-tasks', data)
            response = scheduled_task_viewset(r, data)

            data['interval_count'] = 2
            data['task'] = 'carrot.tests.something_invalid'
            r = f.patch('/api/scheduled-tasks/%s' % response.data.get('pk'), data)
            scheduled_task_detail(r, pk=response.data.get('pk'))

            r = f.get('/api/scheduled-tasks/1/run/')
            run_scheduled_task(r, pk=1)

            r = f.get('/api/scheduled-tasks/task-choices/')
            task_list(r)

            data = {'args': '()'}
            r = f.post('/api/scheduled-tasks/validate-args/', data)
            validate_args(r, data)

            data = {'args': 'some utter bollocks'}
            r = f.post('/api/scheduled-tasks/validate-args/', data)
            response = validate_args(r, data)
            print(response.data)
            self.assertGreater(len(response.data['errors']), 0)

    def test_utilities(self):
        with self.assertRaises(Exception):
            get_host_from_name('test')

        alt_settings = {
            'queues': [
                {
                    'name': 'test',
                    'host': 'amqp://guest:guest@localhost:5672/'
                }
            ]
        }
        with override_settings(CARROT=alt_settings):
            get_host_from_name('test')

        with self.assertRaises(ImportError):
            validate_task('some.invalid.task')

        with self.assertRaises(AttributeError):
            validate_task('carrot.tests.invalid_function')

        validate_task(test_task)

        task = create_scheduled_task(task='carrot.tests.test_task', interval={'days':1})

        self.assertEqual(task.multiplier, 86400)
        task.interval_type = 'hours'
        self.assertEqual(task.multiplier, 3600)
        task.interval_type = 'minutes'
        self.assertEqual(task.multiplier, 60)
        task.interval_type = 'seconds'
        self.assertEqual(task.multiplier, 1)

        with mock.patch('carrot.utilities.publish_message'):
            task.publish()

        self.assertTrue(isinstance(task, ScheduledTask))

        with self.assertRaises(AttributeError):
            create_scheduled_task(task='carrot.tests.test_task', interval=None)

        decorate_class_view(MessageList, ['django.contrib.auth.decorators.login_required'])
        decorate_class_view(MessageList)

        decorate_function_view(failed_message_log_viewset, ['django.contrib.auth.decorators.login_required'])

    def test_purge(self):
        MessageLog.objects.create(
            status='IN_PROGRESS',
            uuid='2c2eef00-689f-4478-ba59-2d17d1fcb23f',
            task='some.invalid.task',
        )

        with mock.patch('pika.BlockingConnection', new_callable=mock_connection):
            purge_queue()

        with self.assertRaises(ObjectDoesNotExist):
            MessageLog.objects.get(uuid='2c2eef00-689f-4478-ba59-2d17d1fcb23f')

        self.assertEqual(MessageLog.objects.filter(status__in=['IN_PROGRESS', 'PUBLISHED']).count(), 0)

