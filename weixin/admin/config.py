# -*-coding:utf-8 -*-
"""
Created on 2013-11-21

@author: Danny
DannyWork Project
"""

from django.contrib import admin
from django.http.response import HttpResponseRedirect
from django.core.urlresolvers import reverse

from ..models import Config, QyAgent
from .base import OwnerBasedModelAdmin


class QyAgentInline(admin.TabularInline):
    """
    企业号应用配置 Inline
    """

    model = QyAgent

    fields = ['name', 'agent_id']

    def get_queryset(self, request):
        qs = super(QyAgentInline, self).get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(config__owner__username=request.user.username)
        return qs


class ConfigAdmin(OwnerBasedModelAdmin):
    actions = None
    fields = ['type', 'token', 'app_id', 'secret', 'encoding_aes_key']
    list_display = ['type', 'token', 'app_id', 'secret', 'encoding_aes_key']
    change_list_template = 'core/admin/change_list.html'
    inlines = [QyAgentInline]

    def __init__(self, *args, **kwargs):
        super(ConfigAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None, )

    def get_config(self, request):
        try:
            return Config.objects.filter(owner=self.account(request))[0]
        except IndexError:
            pass

    def get_inline_instances(self, request, obj=None):
        config = self.get_config(request)
        self.inlines = [QyAgentInline] if config and config.type == 'Q' else []

        return super(ConfigAdmin, self).get_inline_instances(request, obj)

    def add_view(self, request, form_url='', extra_context=None):
        c = Config.objects.filter(owner__id=self.account(request))
        if c.exists():
            url_name = 'admin:{0}_{1}_change'.format(self.model._meta.app_label,
                                                     self.model._meta.module_name)
            return HttpResponseRedirect(reverse(url_name, args=[c[0].id]))
        return super(ConfigAdmin, self).add_view(request, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['config'] = self.get_config(request)
        return super(ConfigAdmin, self).changelist_view(request, extra_context)


admin.site.register(Config, ConfigAdmin)
