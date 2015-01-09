# -*-coding:utf-8 -*-
"""
Created on 2013-11-21

@author: Danny
DannyWork Project
"""

from django.contrib import admin, messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404

from ..models import Account


class OwnerBasedModelAdmin(admin.ModelAdmin):
    account = None

    def save_model(self, request, obj, form, change):
        if not change:
            obj.owner = self.account(request, get_object=True)
        return super(OwnerBasedModelAdmin, self).save_model(request, obj, form, change)

    def get_list_display(self, request):
        list_display = list(super(OwnerBasedModelAdmin, self).get_list_display(request))
        if request.user.is_superuser:
            list_display.append('owner')
        return list_display

    def init_account(self, request):
        try:
            account = Account.objects.get(username=request.user.username)
        except Account.DoesNotExist:
            account = None
            if request.user.is_superuser:
                messages.info(request, u'您当前没有账户，无权添加但可编辑。')
            else:
                messages.error(request, u'您当前没有权限在此进行任何操作。')
        request.session['account'] = account.id if account else account

    def account(self, request, get_object=False):
        aid = request.session.get('account', None)
        if get_object:
            try:
                return Account.objects.get(id=aid)
            except Account.DoesNotExist:
                raise Http404
        return aid

    def get_queryset(self, request):
        qs = super(OwnerBasedModelAdmin, self).get_queryset(request)
        return qs if request.user.is_superuser else qs.filter(owner=self.account(request))

    def add_view(self, request, form_url='', extra_context=None):
        self.init_account(request)
        if not self.account(request):
            info = self.model._meta.app_label, self.model._meta.module_name
            return HttpResponseRedirect(redirect_to=reverse('admin:{0}_{1}_changelist'.format(*info)))
        return super(OwnerBasedModelAdmin, self).add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        self.init_account(request)
        if not self.account(request) and not request.user.is_superuser:
            info = self.model._meta.app_label, self.model._meta.module_name
            return HttpResponseRedirect(redirect_to=reverse('admin:{0}_{1}_changelist'.format(*info)))
        return super(OwnerBasedModelAdmin, self).change_view(request, object_id, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        self.init_account(request)
        return super(OwnerBasedModelAdmin, self).changelist_view(request, extra_context)
