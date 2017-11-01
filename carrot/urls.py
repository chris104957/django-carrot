from django.conf.urls import url, include
from carrot.views import (
    MessageList, MessageView, requeue, CreateScheduledTaskView, UpdateScheduledTaskView, DeleteScheduledTaskView,
    DeleteFailedTaskView, requeue_all, delete_all
)
from carrot.utilities import decorate_class_view, decorate_function_view
from django.conf import settings
# from rest_framework_swagger.views import get_swagger_view
from carrot.api import (
    published_message_log_viewset, failed_message_log_viewset, completed_message_log_viewset, scheduled_task_viewset,
    detail_message_log_viewset, scheduled_task_detail
)
# schema_view = get_swagger_view('Carrot API')

decorators = settings.CARROT.get('monitor_authentication', [])


def _(v, **kwargs):
    return decorate_class_view(v, decorators).as_view(**kwargs)


def _f(v):
    return decorate_function_view(v, decorators)


urlpatterns = [
    url(r'^$', _(MessageList), name='carrot-monitor'),
    url(r'^(?P<pk>[0-9]+)/view/level=(?P<level>[a-zA-Z0-9-]+)$', _(MessageView), name='task-info'),
    url(r'^(?P<pk>[0-9]+)/requeue/$', _f(requeue), name='requeue-task'),
    url(r'requeue-all/$', _f(requeue_all), name='requeue-all'),
    url(r'delete-all/$', _f(delete_all), name='delete-all'),
    url(r'^(?P<pk>[0-9]+)/delete/$', _(DeleteFailedTaskView), name='delete-task'),
    url(r'^scheduled/(?P<pk>[0-9]+)/$', _(UpdateScheduledTaskView), name='edit-scheduled-task'),
    url(r'^scheduled/(?P<pk>[0-9]+)/delete/$', _(DeleteScheduledTaskView), name='delete-scheduled-task'),
    url(r'scheduled/create/$', _(CreateScheduledTaskView), name='create-scheduled-task'),
    # url(r'^api/docs/$', schema_view),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api/message-logs/published/$', published_message_log_viewset),
    url(r'^api/message-logs/failed/$', failed_message_log_viewset),
    url(r'^api/message-logs/completed/$', completed_message_log_viewset),
    url(r'^api/message-logs/(?P<pk>[0-9]+)/$', detail_message_log_viewset),
    url(r'^api/scheduled-tasks/$', scheduled_task_viewset),
    url(r'^api/scheduled-tasks/(?P<pk>[0-9]+)/$', scheduled_task_detail),
]