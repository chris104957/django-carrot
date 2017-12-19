import mock
import logging

from django.test import TestCase
from carrot.consumer import Consumer
from carrot.objects import VirtualHost
from carrot.utilities import (
    create_message
)
from carrot.models import MessageLog
from carrot import DEFAULT_BROKER


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


class CarrotTestCase(TestCase):
    @mock.patch('pika.SelectConnection')
    def test_consumer(self, *args):
        consumer = Consumer(VirtualHost('amqp://guest:guest@localhost:5672/test'), 'test', logging, 'test')
        consumer.task_log = ['blah']
        log = MessageLog(task='carrot.tests.test_task')
        consumer.fail(log, 'test error')
