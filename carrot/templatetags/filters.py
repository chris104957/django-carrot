from django import template
from django.utils.html import format_html, mark_safe, format_html_join
from django.forms.utils import flatatt
import json
from carrot.utilities import JsonConverter
from django.core.urlresolvers import reverse


register = template.Library()


@register.simple_tag
def el(tag, content=None, **opts):
    if content:
        return format_html('<{} {}>{}</{}>', tag, flatatt(opts), content, tag)
    else:
        return format_html('<{} {} />', tag, flatatt(opts))


@register.simple_tag
def ot(tag, **opts):
    return format_html('<{} {}>', tag, flatatt(opts))


@register.simple_tag
def ct(tag):
    return format_html('</{}>', tag)


@register.inclusion_tag('carrot/table.html')
def task_queue(object_list):
    return {
        'table_class': 'task-queue',
        'headers': ['Priority', 'Task', 'Arguments', 'Keyword arguments', 'Queue', 'Exchange', 'Routing key'],
        'attributes': ['priority', 'href', 'task_args', 'content', 'queue', 'exchange', 'routing_key'],
        'object_list': object_list[:30]
    }


@register.inclusion_tag('carrot/strapline.html')
def strapline_with_url(null):
    return {
        'pre_msg': 'Click',
        'url': reverse('create-scheduled-task', args=[]),
        'msg': 'here',
        'post_msg': 'to create a new scheduled task'
    }


@register.inclusion_tag('carrot/task_form.html')
def task_form(form):
    return {'form': form}


@register.filter
def jsonblock(object):
    content = object.keywords
    if not content or str(content) == '"{}"':
        return format_html('<ul {}>{}</ul>',
                           flatatt({'class': 'traceback green'}),
                           'No information provided'
                           )

    converter = JsonConverter()
    if object.positionals:
        first_row = format_html('<tr><th>{}</th><th>{}</th></tr><tr><td>Positional arguments</td><td>{}</td></tr',
                                'Field', 'Value', object.positionals)
    else:
        first_row = format_html('<tr><th>{}</th><th>{}</th></tr', 'Field', 'Value')

    return mark_safe(converter.convert(
        json=object.keywords,
        first_row=first_row,
        table_attributes=flatatt({'class': 'task-queue'}),
    ))


@register.filter
def outputblock(content):
    try:
        if not content or str(content) == '"{}"':
            return format_html('<ul {}>{}</ul>',
                               flatatt({'class': 'traceback green'}),
                               'No information provided'
                               )
        converter = JsonConverter()
        first_row = format_html('<tr><th>{}</th><th>{}</th></tr', 'Field', 'Value')

        return mark_safe(converter.convert(
            json=json.loads(content or '{}'),
            first_row=first_row,
            table_attributes=flatatt({'class': 'task-queue'}),
        ))

    except json.JSONDecodeError:
        return format_html('<ul {}>{}</ul>',
                           flatatt({'class': 'traceback green'}),
                           format_html_join('\n', '<li class="tb">{}</li>', ((line,) for line in content.split('\n'))))


@register.inclusion_tag('carrot/info_table.html')
def info_table(object):
    attributes = [
        ('Virtual host', object.virtual_host,),
        ('Queue', object.queue,),
        ('Exchange', object.exchange,),
        ('Routing key', object.routing_key),
        ('Status', object.status),
        ('Priority', object.priority),
        ('Publish time', object.display_publish_time),
        ('Completion time', object.display_completion_time),
        ('Failure time', object.display_failure_time),
    ]
    return {
        'table_class': 'task-queue',
        'headers': ['Field', 'Value'],
        'attributes': attributes,
    }


@register.inclusion_tag('carrot/table.html')
def failed_task_queue(object_list):
    object_list = object_list.order_by('-failure_time')
    return {
        'table_class': 'task-queue failed',
        'headers': ['Failure Time', 'Task', 'Arguments', 'Keyword arguments', 'Exchange', 'Routing key', 'Exception'],
        'attributes': ['display_failure_time', 'href', 'task_args', 'content', 'exchange', 'routing_key', 'exception'],
        'object_list': object_list[:30]
    }


@register.inclusion_tag('carrot/table.html')
def completed_task_queue(object_list):
    object_list = object_list.order_by('-completion_time')
    return {
        'table_class': 'task-queue completed',
        'headers': ['Completion Time', 'Task', 'Arguments', 'Keyword arguments', 'Exchange', 'Routing key',],
        'attributes': ['display_completion_time', 'href', 'task_args', 'content', 'exchange', 'routing_key',],
        'object_list': object_list[:30]
    }


@register.inclusion_tag('carrot/table.html')
def scheduled_task_queue(object_list):
    return {
        'table_class': 'task-queue',
        'headers': ['Task', 'Interval', 'Exchange', 'Routing key', 'Active?'],
        'attributes': ['href', 'interval_display', 'exchange', 'routing_key', 'active'],
        'object_list': object_list[:30]
    }



@register.simple_tag
def get_attr(instance, field, default=None):
    return getattr(instance, field, default)


@register.filter
def table_strapline(object_list):
    if object_list.count() > 30:
        msg = 'Showing the next 30 tasks to be processed (out of a total of %i)' % object_list.count()
    elif object_list.count() == 0:
        msg = 'No items currently in the queue'

    else:
        msg = 'Showing all %i tasks currently in the queue' % object_list.count()

    return format_html('<p {}>{}<p>', flatatt({'class':'strapline'}), msg)


@register.filter
def table_strapline_failed(object_list):
    requeue_delete = 'Click <a {}>here</a> to requeue all tasks, or <a {}>here</a> to delete all tasks'

    requeue_delete_args = flatatt({'href': reverse('requeue-all')}), flatatt({'href': reverse('delete-all')})

    if object_list.count() > 30:
        msg = 'Showing the 30 most recent failed tasks (out of a total of %i).' % object_list.count(),

    elif object_list.count() == 0:
        requeue_delete_args = ()
        requeue_delete = ''
        msg = 'No failed tasks'

    else:
        msg = 'Showing all %i failed tasks.' % object_list.count()

    return format_html('<p {}>{} %s<p>' % requeue_delete, flatatt({'class':'strapline'}), msg, *requeue_delete_args)


@register.filter
def table_strapline_completed(object_list):
    if object_list.count() > 30:
        msg = 'Showing the 30 most recent completed tasks (out of a total of %i)' % object_list.count()

    elif object_list.count() == 0:
        msg = 'No recent completed tasks'

    else:
        msg = 'Showing all %i completed tasks' % object_list.count()

    return format_html('<p {}>{}<p>', flatatt({'class':'strapline'}), msg)


@register.filter
def formatted_traceback(traceback, loglevel='WARNING'):
    levels = {
        'DEBUG': 0,
        'INFO': 1,
        'WARNING': 2,
        'ERROR': 3,
        'CRITICAL': 4,
    }

    items = []
    traceback = traceback.split('\n')
    for line in traceback:
        def get_indent(l):
            return int((len(l) - len(l.lstrip())) / 2)
        try:
            data, msg = line.strip().split('::')[0:2]
            consumer, date, time, level = data.split()
            msg = '%s %s: %s' % (date, time, msg)
            if levels[level] >= levels[loglevel]:
                items.append((get_indent(line), level, msg))
        except ValueError:
            items.append((get_indent(line), 'ERROR', line.strip()))

    list_items = format_html_join('\n', '<li class="tb indent_level_{} {}">{}</li>', ((item) for item in items))

    return format_html('<ul class="traceback yellow">{}</ul>', list_items)
