import mock
import time
import logging

from django.test import TestCase
from django.core.management import call_command
from django.db.utils import OperationalError
from django.db.models import QuerySet
from django.test import RequestFactory
from django.contrib.auth.models import User

from carrot.models import ScheduledTask, MessageLog
from carrot.consumer import ConsumerSet, Consumer
from carrot.objects import VirtualHost, Message, DefaultMessageSerializer
from carrot.scheduler import ScheduledTaskManager, ScheduledTaskThread
from carrot.utilities import (
    get_host_from_name, publish_message, create_scheduled_task, decorate_class_view
)
from carrot.api import (
    failed_message_log_viewset, scheduled_task_viewset, detail_message_log_viewset, scheduled_task_detail,
)
from rest_framework.test import APIRequestFactory

from carrot.views import MessageList

from carrot import DEFAULT_BROKER


logger = logging.getLogger('carrot')


def test_task(*args, **kwargs):
    logger.error('blah')


def dict_task(*args, **kwargs):
    return {'blah': True}


def test_failure(*args, **kwargs):
    raise Exception('Exception from test_failure task')


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


def mocked_model(model, count=0):
    class MockQuerySet(QuerySet):
        def count(self):
            return count

    return MockQuerySet(model=model)


def mocked_object(*args, **kwargs):
    class MockMessageLog(object):
        task = 'blah2'

        def __init__(self, *args, **kwargs):
            print(args, kwargs)
            self.task = 'blah'

        def save(*args, **kwargs):
            raise OperationalError('OperationalError')

    return MockMessageLog


def mocked_connection(**kwargs):
    class MethodFrame:
        delivery_tag = 1

        def __iter__(self):
            for i in []:
                yield

    class Properties:
        def __init__(self, fail_properties, task):
            self.fail_properties = fail_properties
            self.task = task

        @property
        def headers(self):
            if self.fail_properties:
                raise KeyError('KeyError')

            return {'type': 'carrot.tests.%s' % self.task}

        message_id = 1

    class Channel:
        def __init__(self, task, fail_properties=False):
            self.fail_properties = fail_properties
            self.task = task

        def consume(self, *args, **kwargs):
            mframe = MethodFrame()
            properties = Properties(self.fail_properties, self.task)
            content = b'{}'
            return [mframe, properties, content], properties, content

        def basic_nack(self, *args, **kwargs):
            return

        def basic_ack(self, *args, **kwargs):
            return

    class Connection(object):
        def __init__(self, *args, **kwargs):
            self.fail_properties = kwargs.pop('fail_properties', False)
            self.task = kwargs.pop('task', 'test_task')

        def sleep(self, duration):
            return

        def channel(self):
            return Channel(self.task, self.fail_properties)

    def make_connection(**options):
        return Connection(**kwargs)

    return make_connection


def mock_task(*args, **kwargs):
    class MockTask(object):
        multiplier = 1
        interval_count = 1
        pk = 1
        task = 'carrot.tests.test_task'

        def __init__(self, *args, **kwargs):
            print(args, kwargs)

        @staticmethod
        def publish():
            return

    return MockTask()


@mock.patch('carrot.objects.VirtualHost')
def consume_one(signal, *args, **kwargs):
    @mock.patch('pika.BlockingConnection', mocked_connection(**kwargs))
    def wrap(*args):
        consumer = Consumer(1, 'test', VirtualHost(), 'null', logger, run_once=True)
        consumer.signal = signal
        consumer.start()
        consumer.join()

    return wrap()


class CarrotTestCase(TestCase):
    @mock.patch('pika.BlockingConnection')
    @mock.patch('carrot.consumer.ConsumerSet')
    @mock.patch('time.sleep')
    def test_commands(self, *args):
        kwargs = {'logfile': 'mycarrot.log', 'testmode': True}

        with self.settings(CARROT=ALT_CARROT):
            with mock.patch('time.sleep'):
                with mock.patch('carrot.models.ScheduledTask.objects', mocked_model(ScheduledTask, count=300)):
                    with self.assertRaises(SystemExit):
                        call_command('carrot', **kwargs)
                with mock.patch('carrot.models.ScheduledTask.objects', mocked_model(ScheduledTask, count=-1)):
                    with self.assertRaises(SystemExit):
                        call_command('carrot', **kwargs)

        with mock.patch('carrot.scheduler.ScheduledTaskManager.start',
                        side_effect=Exception('Generic Exception from test_commands')):
            call_command('carrot', **kwargs)

    @mock.patch('carrot.objects.VirtualHost')
    @mock.patch('carrot.consumer.Consumer')
    def test_consumer_set(self, *args):
        with mock.patch('pika.BlockingConnection', mocked_connection()):
            with mock.patch('carrot.models.MessageLog.objects.get', mocked_object):
                logger = logging.getLogger('carrot')
                c = ConsumerSet(VirtualHost(), 'null', logger=logger)
                c.start_consuming()
                time.sleep(0.01)
                c.stop_consuming()

    @mock.patch('time.sleep')
    @mock.patch('pika.BlockingConnection.sleep')
    def test_consumer(self, *args):
        consume_one()

        with mock.patch('carrot.models.MessageLog.objects.get'):
            consume_one(True, task='dict_task')
            consume_one(True)
            with mock.patch('carrot.consumer.ListHandler.parse_output', side_effect=Exception()):
                consume_one(True)

            consume_one(False)
            consume_one(True, task='invalid_task')
            consume_one(True, fail_properties=True)

            with mock.patch('carrot.objects.DefaultMessageSerializer.serialize_arguments', side_effect=Exception('test')):
                consume_one(task='dict_task')

        with mock.patch('carrot.models.MessageLog.objects.get', mocked_object):
            consume_one(True, task='test_task')

        from django.core.exceptions import ObjectDoesNotExist
        with mock.patch('carrot.models.MessageLog.objects.get', side_effect=ObjectDoesNotExist()):
            consume_one(True, task='test_task')

    @mock.patch('pika.BlockingConnection')
    def test_utilities(self, *args):
        host = get_host_from_name(None)
        self.assertTrue(isinstance(host, VirtualHost))

        with self.settings(CARROT=ALT_CARROT):
            host = get_host_from_name('test')
            self.assertTrue(isinstance(host, VirtualHost))

            with self.assertRaises(Exception):
                get_host_from_name('blah')

        publish_message('carrot.tests.test_task')
        publish_message(test_task)
        with self.assertRaises(ImportError):
            publish_message('invalid.path')

        with self.assertRaises(AttributeError):
            publish_message('carrot.tests.invalid_task')

        create_scheduled_task(test_task, {'seconds': 1}, 'test')

        with self.assertRaises(AttributeError):
            create_scheduled_task(test_task, {'seconds': 1, 'hours': 1}, 'test')

        decorate_class_view(MessageList, None)

        cls_view = decorate_class_view(MessageList, ['django.contrib.auth.decorators.login_required'])

        r = RequestFactory().get(cls_view())
        r.user = mock.MagicMock(spec=User)

        with self.assertRaises(AttributeError):
            print(cls_view().dispatch(r))

    @mock.patch('pika.BlockingConnection')
    def test_models(self, *args):
        from django.utils.safestring import SafeText
        msg = publish_message(test_task, 0, None)
        self.assertTrue(isinstance(msg.virtual_host, str))
        self.assertTrue(isinstance(msg.keywords, dict))

        task = create_scheduled_task(test_task, {'seconds': 5})

        self.assertEqual(task.interval_display, 'Every 5 seconds')

        self.assertEqual(task.multiplier, 1)
        task.interval_type = 'minutes'
        self.assertEqual(task.multiplier, 60)
        task.interval_type = 'hours'
        self.assertEqual(task.multiplier, 3600)
        task.interval_type = 'days'
        self.assertEqual(task.multiplier, 86400)
        self.assertEqual(task.positional_arguments, ())
        task.task_args = 'blah, blah2,'
        self.assertEqual(task.positional_arguments, ('blah','blah2'))

        self.assertTrue(isinstance(task.publish(), MessageLog))

    def test_objects(self):
        self.assertEqual('amqp://guest:guest@localhost:5672//', str(VirtualHost(url='amqp://localhost:5672')))
        with self.assertRaises(Exception):
            VirtualHost(url='blah')
        msg = Message('carrot.tests.test_task', VirtualHost(url=DEFAULT_BROKER), task_kwargs={'blah': True})

        serializer = DefaultMessageSerializer(msg)
        self.assertTrue(isinstance(serializer.body(), str))
        with self.settings(CARROT=ALT_CARROT):
            Message('carrot.tests.test_task', None)

    def test_scheduler(self):
        task = create_scheduled_task(test_task, {'seconds': 1}, blah=True)
        s = ScheduledTaskManager()
        s.start()
        s.stop()

        with mock.patch('carrot.utilities.publish_message'):
            with mock.patch('carrot.models.ScheduledTask.objects.get', mock_task):
                thread = ScheduledTaskThread(task, True)
                thread.active = False
                thread.inactive_reason = 'test'

                with mock.patch('time.sleep'):
                    thread.start()
                    thread.join()

                    thread = ScheduledTaskThread(task)
                    thread.start()

                thread.active = False
                thread.join()

    @mock.patch('carrot.utilities.create_message')
    def test_api(self, *args):
        MessageLog.objects.create(status='FAILED', task_args='()', task='mymodule.task')

        factory = APIRequestFactory()

        request = factory.put('/carrot/api/message-logs/')
        failed_message_log_viewset(request)

        msg = MessageLog.objects.create(status='FAILED', task_args='()', task='mymodule.task')
        request = factory.put('/carrot/api/message-logs/%s/' % msg.pk)
        detail_message_log_viewset(request, pk=msg.pk)

        request = factory.delete('/carrot/api/message-logs/%s/' % msg.pk)
        detail_message_log_viewset(request, pk=msg.pk)

        request = factory.delete('/carrot/api/message-logs/')
        failed_message_log_viewset(request)

        data = {
            'queue': 'blah',
            'task_args': '()',
            'content': '{}',
            'task': 'carrot.tests.test_task'
        }
        invalid_data = {
            'queue': '',
            'task_args': 'blah',
            'content': '}{',
            'task': None,
        }
        with self.settings(CARROT=ALT_CARROT):
            request = factory.post('/carrot/api/scheduled-tasks/', data)
            scheduled_task_viewset(request)

            request = factory.patch('/carrot/api/scheduled-tasks/', data)
            scheduled_task_detail(request, pk=msg.pk)

            request = factory.post('/carrot/api/scheduled-tasks/', invalid_data)
            scheduled_task_viewset(request)






