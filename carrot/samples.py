from carrot.utilities import publish_message

def my_task(**kwargs):
    return 'hello world'

publish_message(my_task, hello=True)


from carrot.utilities import create_scheduled_task

create_scheduled_task(my_task, {'seconds': 5}, hello=True)


from carrot.models import MessageLog
from django.utils import timezone
from datetime import timedelta


def delete_expired(expiry=None):
    """
    Finds all completed :class:`carrot.models.MessageLog` objects that were completed more than 3 days ago, and deletes
    them
    """
    if expiry is None:
        expiry = {'days': 3}

    completed_tasks = MessageLog.objects.filter(status='COMPLETED',
                                                completion_time__lte=timezone.now() - timedelta(**expiry))
    count = completed_tasks.count()
    completed_tasks.delete()

    return 'Deleted %i entries' % count
