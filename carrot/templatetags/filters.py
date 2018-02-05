from django import template
from django.utils.html import mark_safe
from django.conf import settings
import importlib
from inspect import getmembers, isfunction
from carrot.models import ScheduledTask
from django.template.response import SimpleTemplateResponse


register = template.Library()


def get_content(template, context=None):
    if context is None:
        context = {}
    task_temp = SimpleTemplateResponse('carrot/%s.html' % template, context=context)
    content = task_temp.rendered_content.replace('\n', '')
    return mark_safe(content)


@register.inclusion_tag('carrot/carrot.js')
def vue():
    task_content = get_content('task_detail')
    field_errors_content = get_content('field-errors')
    scheduled_content = get_content('scheduled_task_detail')
    paginator_content = get_content('paginator')
    search_bar_content = get_content('search_bar')
    try:
        modules = settings.CARROT.get('task_modules', [])
    except AttributeError:
        modules = []
    task_choices = []
    interval_choices = [c[0] for c in ScheduledTask.INTERVAL_CHOICES]
    for module in modules:
        try:
            mod = importlib.import_module(module)
            functions = [o[0] for o in getmembers(mod) if isfunction(o[1]) and not o[0] == 'task']

            for function in functions:
                f = '%s.%s' % (module, function)
                task_choices.append(f)
        except (ImportError, AttributeError):
            pass

    return {
        'task_detail_template': task_content,
        'scheduled_task_template': scheduled_content,
        'task_options': mark_safe(task_choices),
        'interval_options': mark_safe(interval_choices),
        'field_errors': field_errors_content,
        'paginator_template': paginator_content,
        'search_bar_template': search_bar_content,
    }

