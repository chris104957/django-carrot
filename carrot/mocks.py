from carrot.objects import DefaultMessageSerializer


class MessageSerializer(DefaultMessageSerializer):
    failing_method = 'serialize_arguments'

    def serialize_arguments(self, body):
        if self.failing_method == 'serialize_arguments':
            raise AttributeError('test error message')
        super(MessageSerializer, self).serialize_arguments(body)

    def get_task(self, properties, body):
        if self.failing_method == 'get_task':
            raise AttributeError('test error message')
        super(MessageSerializer, self).get_task(properties, body)


class IoLoop(object):
    def stop(self):
        pass

    def start(self):
        pass


class Channel(object):
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

    def basic_cancel(self, *args, **kwargs):
        return

    def basic_nack(self, *args, **kwargs):
        return

    def basic_ack(self, *args, **kwargs):
        return


class Connection(object):
    def __init__(self, *args, **kwargs):
        self.channel = Channel
        self.ioloop = IoLoop()

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


class Properties(object):
    message_id = 1234
    delivery_tag = 1
    headers = {}


class Consumer(object):
    def join(self):
        return

    def stop(self):
        return

    def start(self):
        return

    def __init__(self, *args, **kwargs):
        pass