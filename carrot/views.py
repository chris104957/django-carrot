from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from carrot.models import MessageLog, ScheduledTask
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.urls import reverse_lazy
from django import forms
from django.conf import settings
import json
import ast
import importlib
from inspect import getmembers, isfunction


class TaskForm(forms.ModelForm):
    def __init__(self, **kwargs):
        super(TaskForm, self).__init__(**kwargs)
        modules = settings.CARROT.get('task_modules', None)
        if modules:
            task_choices = []
            for module in modules:
                try:
                    mod = importlib.import_module(module)
                    functions = [o[0] for o in getmembers(mod) if isfunction(o[1]) and not o[0] == 'task']

                    for function in functions:
                        f = '%s.%s' % (module, function)
                        task_choices.append((f, f))
                except (ImportError, AttributeError):
                    pass

            self.fields['task'] = forms.ChoiceField(choices=task_choices)

    def clean(self):
        cleaned_data = super(TaskForm, self).clean()

        if not self.cleaned_data['queue']:
            raise forms.ValidationError({'queue': 'This field is required'})
        try:
            json.loads(self.cleaned_data['content'] or '{}')
        except json.JSONDecodeError:
            raise forms.ValidationError({'content': 'this field must be json serializable'})

        if self.cleaned_data.get('task_args', None):
            for arg in self.cleaned_data['task_args'].split(','):
                try:
                    ast.literal_eval(arg.strip())
                except Exception as err:
                    raise forms.ValidationError({'task_args': 'This string cannot be parsed. Reason: %s' % err})

        return cleaned_data

    class Meta:
        model = ScheduledTask
        fields = (
            'task', 'task_args', 'queue', 'content', 'exchange', 'routing_key', 'interval_type', 'interval_count',
            'active'
        )


class MessageList(ListView):
    queryset = MessageLog.objects.filter(status='PUBLISHED')

    def get_context_data(self, **kwargs):
        context = super(MessageList, self).get_context_data(**kwargs)
        context['failed_tasks'] = MessageLog.objects.filter(status='FAILED')
        context['completed_tasks'] = MessageLog.objects.filter(status='COMPLETED')
        context['scheduled_tasks'] = ScheduledTask.objects.all()
        return context


def requeue(request, pk):
    msg = MessageLog.objects.get(pk=pk)
    msg.requeue()
    return redirect(reverse('carrot-monitor'))


def requeue_all(request):
    for msg in MessageLog.objects.filter(status='FAILED'):
        msg.requeue()
    return redirect(reverse('carrot-monitor'))


def delete_all(request):
    for msg in MessageLog.objects.filter(status='FAILED'):
        msg.delete()
    return redirect(reverse('carrot-monitor'))


class DeleteFailedTaskView(DeleteView):
    model = MessageLog
    pk_url_kwarg = 'pk'
    success_url = reverse_lazy('carrot-monitor')


class MessageView(DetailView):
    model = MessageLog
    pk_url_kwarg = 'pk'

    def get_context_data(self, **kwargs):
        context = super(MessageView, self).get_context_data(**kwargs)
        context['loglevel'] = self.kwargs.get('level', "INFO")
        return context


class CreateScheduledTaskView(CreateView):
    model = ScheduledTask
    form_class = TaskForm


class UpdateScheduledTaskView(UpdateView):
    model = ScheduledTask
    pk_url_kwarg = 'pk'
    form_class = TaskForm


class DeleteScheduledTaskView(DeleteView):
    model = ScheduledTask
    pk_url_kwarg = 'pk'
    success_url = reverse_lazy('carrot-monitor')





