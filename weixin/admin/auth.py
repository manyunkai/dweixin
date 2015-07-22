# -*-coding:utf-8 -*-
"""
Created on 2015-01-07

@author: Danny
DannyWork Project
"""

from django.contrib import admin, messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.conf import settings

from ..models import Account


class AccountAdmin(admin.ModelAdmin):
    list_display = ['username', 'url', 'created', 'is_valid', 'uuid']
    fields = ['username', 'is_valid']
    actions = None

    def get_list_display(self, request):
        if request.user.is_superuser:
            return self.list_display
        return ['username', 'url']

    def url(self, obj):
        return settings.HOST + reverse('weixin_entry', args=[obj.uuid])
    url.short_description = u'微信接入链接'

    def get_queryset(self, request):
        qs = super(AccountAdmin, self).get_queryset(request)
        return qs if request.user.is_superuser else qs.filter(username=request.user.username)

    def add_view(self, request, form_url='', extra_context=None):
        if not request.user.is_superuser:
            info = self.model._meta.app_label, self.model._meta.module_name
            return HttpResponseRedirect(redirect_to=reverse('admin:{0}_{1}_changelist'.format(*info)))
        return super(AccountAdmin, self).add_view(request, form_url, extra_context)

    def delete_view(self, request, object_id, extra_context=None):
        if not request.user.is_superuser:
            info = self.model._meta.app_label, self.model._meta.module_name
            return HttpResponseRedirect(redirect_to=reverse('admin:{0}_{1}_changelist'.format(*info)))
        return super(AccountAdmin, self).add_view(request, object_id, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if not request.user.is_superuser:
            info = self.model._meta.app_label, self.model._meta.module_name
            return HttpResponseRedirect(redirect_to=reverse('admin:{0}_{1}_changelist'.format(*info)))
        return super(AccountAdmin, self).change_view(request, object_id, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        messages.info(request, u'请将“微信接入链接”配置到微信后台，其余配置在“公众号配置”中修改。')
        return super(AccountAdmin, self).changelist_view(request, extra_context)

admin.site.register(Account, AccountAdmin)
