from django.views.generic import TemplateView


class MessageList(TemplateView):
    template_name = 'carrot/index.vue'

