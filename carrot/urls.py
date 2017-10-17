from django.conf.urls import url
from carrot.views import (
    MessageList, MessageView, requeue, CreateScheduledTaskView, UpdateScheduledTaskView, DeleteScheduledTaskView,
    DeleteFailedTaskView, requeue_all, delete_all
)
from carrot.utilities import decorate_class_view, decorate_function_view
from django.conf import settings

decorators = settings.CARROT.get('monitor_authentication', [])


def _(v, **kwargs):
    return decorate_class_view(v, decorators).as_view(**kwargs)


def _f(v):
    return decorate_function_view(v, decorators)


urlpatterns = [
    url(r'^$', _(MessageList), name='carrot-monitor'),
    url(r'^(?P<pk>[0-9]+)/view/level=(?P<level>[a-zA-Z0-9-]+)$', _(MessageView), name='task-info'),
    # url(r'^(?P<pk>[0-9]+)/view?$', _(MessageView), name='task-info'),
    url(r'^(?P<pk>[0-9]+)/requeue/$', _f(requeue), name='requeue-task'),
    url(r'requeue-all/$', _f(requeue_all), name='requeue-all'),
    url(r'delete-all/$', _f(delete_all), name='delete-all'),
    url(r'^(?P<pk>[0-9]+)/delete/$', _(DeleteFailedTaskView), name='delete-task'),
    url(r'^scheduled/(?P<pk>[0-9]+)/$', _(UpdateScheduledTaskView), name='edit-scheduled-task'),
    url(r'^scheduled/(?P<pk>[0-9]+)/delete/$', _(DeleteScheduledTaskView), name='delete-scheduled-task'),
    url(r'scheduled/create/$', _(CreateScheduledTaskView), name='create-scheduled-task'),
]