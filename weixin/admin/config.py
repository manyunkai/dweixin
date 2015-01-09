# -*-coding:utf-8 -*-
"""
Created on 2013-11-21

@author: Danny
DannyWork Project
"""

from django.contrib import admin
from django.http.response import HttpResponseRedirect
from django.core.urlresolvers import reverse

from ..models import Config
from .base import OwnerBasedModelAdmin


class ConfigAdmin(OwnerBasedModelAdmin):
    actions = None
    fields = ['token', 'app_id', 'secret', 'encoding_aes_key']
    list_display = ['token', 'app_id', 'secret', 'encoding_aes_key']
    change_list_template = 'core/admin/change_list.html'

    def __init__(self, *args, **kwargs):
        super(ConfigAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None, )

    def add_view(self, request, form_url='', extra_context=None):
        c = Config.objects.filter(owner__id=self.account(request))
        if c.exists():
            url_name = 'admin:{0}_{1}_change'.format(self.model._meta.app_label,
                                                     self.model._meta.module_name)
            return HttpResponseRedirect(reverse(url_name, args=[c[0].id]))
        return super(ConfigAdmin, self).add_view(request, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        c = Config.objects.filter(owner__id=self.account(request))
        if c.exists():
            extra_context['config'] = c[0]
        return super(ConfigAdmin, self).changelist_view(request, extra_context)


admin.site.register(Config, ConfigAdmin)
