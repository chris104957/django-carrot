import threading
from carrot.models import ScheduledTask
import time
from django.core.exceptions import ObjectDoesNotExist


class ScheduledTaskThread(threading.Thread):
    """
    A thread that handles a single :class:`carrot.models.ScheduledTask` object. When started, it waits for the interval
    to pass before publishing the task to the required queue

    While waiting for the task to be due for publication, the process continuously monitors the object in the Django
    project's database for changes to the interval, task, or arguments, or in case it gets deleted/marked as inactive
    and response accordingly

    :param carrot.models.ScheduledTask scheduled_task: the scheduled task to be published periodically
    :param bool run_now: whether or not to run the task before waiting for the first interval
    :param dict filters: for limiting the queryset of ScheduledTasks for montoring (defaults to `active=True`)

    """
    def __init__(self, scheduled_task, run_now=False, **filters):
        threading.Thread.__init__(self)
        self.id = scheduled_task.id
        self.queue = scheduled_task.routing_key
        self.scheduled_task = scheduled_task
        self.run_now = run_now
        self.active = True
        self.filters = filters
        self.inactive_reason = ''

    def run(self):
        interval = self.scheduled_task.multiplier * self.scheduled_task.interval_count

        count = 0
        if self.run_now:
            self.scheduled_task.publish()

        while True:
            while count < interval:
                if not self.active:
                    if self.inactive_reason:
                        print('Thread stop has been requested because of the following reason: %s.\n Stopping the '
                              'thread' % self.inactive_reason)

                    return

                try:
                    self.scheduled_task = ScheduledTask.objects.get(pk=self.scheduled_task.pk, **self.filters)
                    interval = self.scheduled_task.multiplier * self.scheduled_task.interval_count

                except ObjectDoesNotExist:
                    print('Current task has been removed from the queryset. Stopping the thread')
                    return

                time.sleep(1)
                count += 1

            print('Publishing message %s' % self.scheduled_task.task)
            self.scheduled_task.publish()
            count = 0


class ScheduledTaskManager(object):
    """
    The main scheduled task manager project. For every active :class:`carrot.models.ScheduledTask`, a
    :class:`ScheduledTaskThread` is created and started

    This object exists for the purposes of starting these threads on startup, or when a new ScheduledTask object
    gets created, and implements a .stop() method to stop all threads

    """
    def __init__(self, **options):
        self.threads = []
        self.filters = options.pop('filters', {'active': True})
        self.run_now = options.pop('run_now', False)
        self.tasks = ScheduledTask.objects.filter(**self.filters)

    def start(self):
        print('found %i scheduled tasks to run' % self.tasks.count())
        for t in self.tasks:
            print('starting thread for task %s' % t.task)
            thread = ScheduledTaskThread(t, self.run_now, **self.filters)
            thread.start()
            self.threads.append(thread)

    def add_task(self, task):
        thread = ScheduledTaskThread(task, self.run_now, **self.filters)
        thread.start()
        self.threads.append(thread)

    def stop(self):
        print('Attempting to stop %i running threads' % len(self.threads))

        for t in self.threads:
            print('Stopping thread %s' % t)
            t.active = False
            t.inactive_reason = 'A termination of service was requested'
            t.join()
            print('thread %s stopped' % t)
