import json
import ast
import importlib
from inspect import getmembers, isfunction
from django.conf import settings
from rest_framework import viewsets, serializers, fields, pagination, response
from carrot.models import MessageLog, ScheduledTask


class MessageLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageLog
        fields = 'status', 'exchange', 'queue', 'routing_key', 'uuid', 'priority', 'task', 'task_args', \
                 'content', 'exception', 'traceback', 'output', 'publish_time', 'failure_time', 'completion_time', \
                 'log', 'id', 'virtual_host'


class SmallPagination(pagination.PageNumberPagination):
    page_size = 50


class MessageLogViewset(viewsets.ModelViewSet):
    serializer_class = MessageLogSerializer
    pagination_class = SmallPagination

    def get_queryset(self):
        search_terms = self.request.query_params.getlist('search', None)
        qs = self.queryset.all()
        if search_terms:
            include_pks = []
            for log in qs:
                for search_term in search_terms:
                    if (search_term.lower() in log.task.lower()) or (search_term.lower() in log.content.lower()) or \
                            (search_term.lower() in log.task_args.lower()):
                        include_pks.append(log.pk)
                        break

            qs = self.queryset.filter(pk__in=include_pks)

        return qs


class PublishedMessageLogViewSet(MessageLogViewset):
    """
    Returns a list of Published `MessageLog` objects
    """

    queryset = MessageLog.objects.filter(status__in=['PUBLISHED', 'IN_PROGRESS'], id__isnull=False)


published_message_log_viewset = PublishedMessageLogViewSet.as_view({'get': 'list'})


class FailedMessageLogViewSet(MessageLogViewset):
    """
    Returns a list of failed `MessageLog` objects
    """

    queryset = MessageLog.objects.filter(status='FAILED', id__isnull=False)

    def destroy(self, request, *args, **kwargs):
        """
        Deletes all `MessageLog` objects in the queryset
        """
        self.queryset.delete()
        return response.Response(status=204)

    def retry(self, request, *args, **kwargs):
        """
        Retries all `MessageLog` objects in the queryset
        """

        queryset = self.get_queryset()
        for task in queryset:
            task.requeue()

        return self.list(request, *args, **kwargs)


failed_message_log_viewset = FailedMessageLogViewSet.as_view({'get': 'list', 'delete': 'destroy', 'put': 'retry'})


class CompletedMessageLogViewSet(MessageLogViewset):
    """
    Returns a list of Completed `MessageLog` objects
    """
    queryset = MessageLog.objects.filter(status='COMPLETED', id__isnull=False)


completed_message_log_viewset = CompletedMessageLogViewSet.as_view({'get': 'list'})


class MessageLogDetailViewset(MessageLogViewset):
    """
    Shows the detail of a single `MessageLog` object
    """
    queryset = MessageLog.objects.all()
    kwargs = {}

    def destroy(self, request, *args, **kwargs):
        """
        Deletes the given `MessageLog` object
        """
        return super(MessageLogDetailViewset, self).destroy(request, *args, **kwargs)

    def retry(self, request, *args, **kwargs):
        """
        Requeue a failed task then calls the `retrieve()` method of the newly created `MessageLog` object
        """
        _object = self.get_object()
        new_object = _object.requeue()
        self.kwargs = {'pk': new_object.pk}
        return self.retrieve(request, *args, **kwargs)


detail_message_log_viewset = MessageLogDetailViewset.as_view({'get': 'retrieve', 'delete':'destroy', 'put': 'retry'})


class ScheduledTaskSerializer(serializers.ModelSerializer):
    def validate_task(self, value):
        modules = settings.CARROT.get('task_modules', None)
        if modules:
            task_choices = []
            for module in modules:
                try:
                    mod = importlib.import_module(module)
                    functions = [o[0] for o in getmembers(mod) if isfunction(o[1]) and not o[0] == 'task']

                    for function in functions:
                        f = '%s.%s' % (module, function)
                        task_choices.append(f)
                except (ImportError, AttributeError):
                    pass
            print(task_choices, value)
            if task_choices and not value in task_choices:
                raise serializers.ValidationError('This is not a valid selection')

        return value

    def validate_task_args(self, value):
        if value:
            for arg in value.split(','):
                try:
                    ast.literal_eval(arg.strip())
                except Exception as err:
                    raise serializers.ValidationError('Error parsing argument %s: %s' % (arg.strip(), err))

        return value

    def validate_content(self, value):
        if value:
            try:
                json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError('This field must be json serializable')

        return value

    def validate_queue(self, value):
        if value == '' or not value:
            raise serializers.ValidationError('This field is required')

        return value

    class Meta:
        model = ScheduledTask
        fields = (
            'task', 'interval_display', 'active', 'id', 'queue', 'exchange', 'routing_key', 'interval_type',
            'interval_count', 'content', 'task_args',
        )
        extra_kwargs = {
            'queue': {
                'required': True
            },
            'interval_type': {
                'required': True
            },
            'interval_count': {
                'required': True
            },
        }


class ScheduledTaskViewset(viewsets.ModelViewSet):
    """
    Returns a list of `ScheduledTask` objects
    """

    def create(self, request, *args, **kwargs):
        """
        Create a new `ScheduledTask` object
        """
        return super(ScheduledTaskViewset, self).create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """
        Update an existing `ScheduledTask` object
        """
        return super(ScheduledTaskViewset, self).update(request, *args, **kwargs)

    def run(self, request, *args, **kwargs):
        _object = self.get_object()
        _object.publish()
        return self.retrieve(request, *args, **kwargs)

    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer
    pagination_class = SmallPagination


scheduled_task_viewset = ScheduledTaskViewset.as_view({'get': 'list', 'post': 'create'})
scheduled_task_detail = ScheduledTaskViewset.as_view({'get': 'retrieve', 'patch': 'update', 'delete': 'destroy'})
run_scheduled_task = ScheduledTaskViewset.as_view({'get': 'run'})


