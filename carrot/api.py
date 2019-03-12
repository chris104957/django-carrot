import json
import ast
import importlib
from inspect import getmembers, isfunction
from django.conf import settings
from rest_framework import viewsets, serializers, pagination, response
from rest_framework.request import Request
from carrot.models import MessageLog, ScheduledTask
from carrot.utilities import purge_queue, requeue_all
from django.contrib.postgres.search import SearchVector
from django.db.models import QuerySet


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

    def get_queryset(self) -> QuerySet:
        """
        Returns a queryset of `carrot.models.MessageLog` objects. If a `search_term` is provided in the request query
        params, then the result is filtered based on this. If using postgres, this is done using SearchVectors for
        improved performance
        """
        search_term = self.request.query_params.get('search', None)
        qs = self.queryset.all()
        if search_term:
            if settings.DATABASES.get('default', {}).get('ENGINE') == 'django.db.backends.postgresql_psycopg2':
                qs = qs.annotate(search=SearchVector('task', 'content', 'task_args')).filter(search=search_term)
            else:
                qs = (
                    qs.filter(task__icontains=search_term) |
                    qs.filter(content__icontains=search_term) |
                    qs.filter(task_args__icontains=search_term)
                ).distinct()

        return qs


class PublishedMessageLogViewSet(MessageLogViewset):
    """
    Returns a list of Published `MessageLog` objects
    """

    queryset = MessageLog.objects.filter(status__in=['PUBLISHED', 'IN_PROGRESS'], id__isnull=False)

    def purge(self, request: Request, *args, **kwargs) -> MessageLogViewset.list:
        """
        Deletes all items in the pending queue
        """
        purge_queue()
        return super(PublishedMessageLogViewSet, self).list(request, *args, **kwargs)

    def requeue(self, request: Request, *args, **kwargs) -> MessageLogViewset.list:
        """
        Requeues all pending MessageLogs. Useful when stuff gets stuck due to system update
        """
        requeue_all()
        return super(PublishedMessageLogViewSet, self).list(request, *args, **kwargs)


published_message_log_viewset = PublishedMessageLogViewSet.as_view({'get': 'list'})
purge_messages = PublishedMessageLogViewSet.as_view({'get': 'purge'})
requeue_pending = PublishedMessageLogViewSet.as_view({'get': 'requeue'})


class FailedMessageLogViewSet(MessageLogViewset):
    """
    Returns a list of failed `MessageLog` objects
    """

    queryset = MessageLog.objects.filter(status='FAILED', id__isnull=False)

    def destroy(self, request: Request, *args, **kwargs) -> response.Response:
        """
        Deletes all `MessageLog` objects in the queryset
        """
        self.queryset.delete()
        return response.Response(status=204)

    def retry(self, request: Request, *args, **kwargs) -> MessageLogViewset.list:
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

    def destroy(self, request: Request, *args, **kwargs) -> MessageLogViewset.destroy:
        """
        Deletes the given `MessageLog` object
        """
        return super(MessageLogDetailViewset, self).destroy(request, *args, **kwargs)

    def retry(self, request: Request, *args, **kwargs) -> MessageLogViewset.retrieve:
        """
        Requeue a single task
        """
        _object = self.get_object()
        new_object = _object.requeue()
        self.kwargs = {'pk': new_object.pk}
        return self.retrieve(request, *args, **kwargs)


detail_message_log_viewset = MessageLogDetailViewset.as_view({'get': 'retrieve', 'delete': 'destroy', 'put': 'retry'})


class ScheduledTaskSerializer(serializers.ModelSerializer):
    def validate_task(self, value: str) -> str:
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
            if task_choices and not value in task_choices:
                raise serializers.ValidationError('This is not a valid selection')

        return value

    def validate_task_args(self, value: str) -> str:
        """
        Takes an input string and verifies that it can be interpreted as valid positional arguments, e.g.

        Valid: "1, True, None"
        Invalid: "foo, bar"
        """
        if value:
            for arg in value.split(','):
                try:
                    ast.literal_eval(arg.strip())
                except Exception as err:
                    raise serializers.ValidationError('Error parsing argument %s: %s' % (arg.strip(), err))

        return value

    def validate_content(self, value: str) -> str:
        """
        Validates that the given input string is valid JSON
        """
        if value:
            try:
                json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError('This field must be json serializable')

        return value

    def validate_queue(self, value: str) -> str:
        """
        Validates that a queue name has been given and is not blank
        """
        if value == '' or not value:
            raise serializers.ValidationError('This field is required')

        return value

    class Meta:
        model = ScheduledTask
        fields = (
            'task', 'interval_display', 'active', 'id', 'queue', 'exchange', 'routing_key', 'interval_type',
            'interval_count', 'content', 'task_args', 'task_name'
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

    def validate_args(self, request: Request, *args, **kwargs) -> response.Response:
        """
        Validates that the input is a valid Python tuple that can be used as a function's positional arguments
        """
        value = request.data.get('args')
        errors = []
        if value:
            for arg in value.split(','):
                try:
                    ast.literal_eval(arg.strip())
                except Exception as err:
                    print('Error parsing argument %s: %s' % (arg.strip(), err))
                    errors.append('Error parsing argument %s: %s' % (arg.strip(), err))

        return response.Response({'errors': errors})

    def get_task_choices(self, request: Request, *args, **kwargs) -> response.Response:
        """
        Gets a list of python functions from the task_modules settings in the config
        """
        modules = settings.CARROT.get('task_modules', None)
        task_choices = []
        if modules:
            for module in modules:
                try:
                    mod = importlib.import_module(module)
                    functions = [o[0] for o in getmembers(mod) if isfunction(o[1]) and not o[0] == 'task']

                    for function in functions:
                        f = '%s.%s' % (module, function)
                        task_choices.append(f)
                except (ImportError, AttributeError):
                    pass

        return response.Response(data=task_choices)

    def create(self, request: Request, *args, **kwargs) -> viewsets.ModelViewSet.create:
        """
        Create a new `ScheduledTask` object
        """
        return super(ScheduledTaskViewset, self).create(request, *args, **kwargs)

    def update(self, request: Request, *args, **kwargs) -> viewsets.ModelViewSet.update:
        """
        Update an existing `ScheduledTask` object
        """
        return super(ScheduledTaskViewset, self).update(request, *args, **kwargs)

    def run(self, request: Request, *args, **kwargs) -> viewsets.ModelViewSet.retrieve:
        """
        Triggers a given scheduled task now
        """
        _object = self.get_object()
        _object.publish()
        return self.retrieve(request, *args, **kwargs)

    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer
    pagination_class = SmallPagination


scheduled_task_viewset = ScheduledTaskViewset.as_view({'get': 'list', 'post': 'create'})
scheduled_task_detail = ScheduledTaskViewset.as_view({'get': 'retrieve', 'patch': 'update', 'delete': 'destroy'})
task_list = ScheduledTaskViewset.as_view({'get': 'get_task_choices'})
validate_args = ScheduledTaskViewset.as_view({'post': 'validate_args'})
run_scheduled_task = ScheduledTaskViewset.as_view({'get': 'run'})



