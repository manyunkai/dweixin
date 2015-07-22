# -*-coding:utf-8 -*-
"""
Created on 2015-01-07

@author: Danny
DannyWork Project
"""

from django.contrib import admin
from django.core.exceptions import PermissionDenied

from ..models import Event, Config


class EventAdmin(admin.ModelAdmin):
    change_list_template = 'event/admin/change_list.html'
    list_display = ['id', 'type', 'pool', 'ident', 'belonging', 'from_user', 'user_message',
                    'processed_status', 'processed_message', 'processed_at', 'reply', 'created']
    actions = None

    def __init__(self, *args, **kwargs):
        super(EventAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = (None, )

    def get_queryset(self, request):
        qs = super(EventAdmin, self).get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(belonging__username=request.user.username)
        return qs

    def change_view(self, request, object_id, form_url='', extra_context=None):
        raise PermissionDenied

    def add_view(self, request, form_url='', extra_context=None):
        raise PermissionDenied

    def delete_view(self, request, object_id, extra_context=None):
        raise PermissionDenied

admin.site.register(Event, EventAdmin)
