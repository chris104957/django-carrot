from rest_framework import viewsets, serializers, authentication, permissions, fields, pagination

from carrot.models import MessageLog, ScheduledTask


class MessageLogSerializer(serializers.ModelSerializer):
    url = fields.CharField(source='get_url')

    class Meta:
        model = MessageLog
        fields = 'url', 'status', 'exchange', 'queue', 'routing_key', 'uuid', 'priority', 'task', 'task_args', \
                 'content', 'exception', 'traceback', 'output', 'publish_time', 'failure_time', 'completion_time', \
                 'log', 'pk', 'virtual_host'


class SmallPagination(pagination.PageNumberPagination):
    page_size = 10


class MessageLogViewset(viewsets.ModelViewSet):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    serializer_class = MessageLogSerializer
    pagination_class = SmallPagination


class PublishedMessageLogViewSet(MessageLogViewset):
    queryset = MessageLog.objects.filter(status='PUBLISHED')


published_message_log_viewset = PublishedMessageLogViewSet.as_view({'get': 'list'})


class FailedMessageLogViewSet(MessageLogViewset):
    queryset = MessageLog.objects.filter(status='FAILED')


failed_message_log_viewset = FailedMessageLogViewSet.as_view({'get': 'list'})


class CompletedMessageLogViewSet(MessageLogViewset):
    queryset = MessageLog.objects.filter(status='COMPLETED')


completed_message_log_viewset = CompletedMessageLogViewSet.as_view({'get': 'list'})


class ScheduledTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledTask
        fields = 'url', 'task', 'interval_display', 'active'


class ScheduledTaskViewset(viewsets.ModelViewSet):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer
    pagination_class = SmallPagination


scheduled_task_viewset = ScheduledTaskViewset.as_view({'get': 'list'})


class MessageLogDetailViewset(MessageLogViewset):
    queryset = MessageLog.objects.all()


detail_message_log_viewset = MessageLogDetailViewset.as_view({'get': 'retrieve'})