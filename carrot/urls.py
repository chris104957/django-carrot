from django.conf.urls import url
from carrot.views import MessageList
from carrot.utilities import decorate_class_view, decorate_function_view
from django.conf import settings
from carrot.api import (
    published_message_log_viewset, failed_message_log_viewset, completed_message_log_viewset, scheduled_task_viewset,
    detail_message_log_viewset, scheduled_task_detail, run_scheduled_task, task_list, validate_args
)

try:
    decorators = settings.CARROT.get('monitor_authentication', [])
except AttributeError:
    decorators = []


def _(v, **kwargs):
    return decorate_class_view(v, decorators).as_view(**kwargs)


def _f(v):
    return decorate_function_view(v, decorators)

urlpatterns = [
    url(r'^$', _(MessageList), name='carrot-monitor'),
    url(r'^api/message-logs/published/$', _f(published_message_log_viewset), name='published-messagelog'),
    url(r'^api/message-logs/failed/$', _f(failed_message_log_viewset)),
    url(r'^api/message-logs/completed/$', _f(completed_message_log_viewset)),
    url(r'^api/message-logs/(?P<pk>[0-9]+)/$', _f(detail_message_log_viewset)),
    url(r'^api/scheduled-tasks/$', _f(scheduled_task_viewset)),
    url(r'^api/scheduled-tasks/task-choices/$', _f(task_list)),
    url(r'^api/scheduled-tasks/validate-args/$', _f(validate_args)),
    url(r'^api/scheduled-tasks/(?P<pk>[0-9]+)/$', _f(scheduled_task_detail)),
    url(r'^api/scheduled-tasks/(?P<pk>[0-9]+)/run/$', _f(run_scheduled_task)),
]