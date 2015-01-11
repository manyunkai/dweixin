# -*-coding:utf-8 -*-
"""
Created on 2013-11-20

@author: Danny
DannyWork Project
"""

from django.contrib import admin, messages
from django.http.response import HttpResponseRedirect
from django.core.urlresolvers import reverse

from ..models import Button, Config
from ..mixins import PullMenu, PushMenu
from .base import OwnerBasedModelAdmin


class ButtonAdmin(OwnerBasedModelAdmin):
    change_list_template = 'menu/admin/change_list.html'
    list_display = ['name', 'type', 'parent', 'key', 'url', 'position']
    fields = ['name', 'type', 'parent', 'key', 'url', 'position']
    raw_id_fields = ['parent']

    def get_urls(self):
        from django.conf.urls import patterns, url

        info = self.model._meta.app_label, self.model._meta.module_name
        return patterns('',
                        url(r'^pull_menu/$',
                            self.admin_site.admin_view(self.pull_menu),
                            name='%s_%s_pull_menu' % info),
                        url(r'^push_menu/$',
                            self.admin_site.admin_view(self.push_menu),
                            name='%s_%s_push_menu' % info),
        ) + super(ButtonAdmin, self).get_urls()

    def get_form(self, request, obj=None, **kwargs):
        form = super(ButtonAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields['parent'].queryset = form.base_fields['parent'].queryset.filter(parent=None)
        return form

    def get_config(self, request):
        try:
            return Config.objects.get(owner=self.account(request))
        except Config.DoesNotExist:
            return None

    def pull_menu(self, request, from_url=''):
        config = self.get_config(request)
        account = self.account(request, get_object=True)
        if config:
            handle = PullMenu(config)
            try:
                status, data = handle.pull()
            except BaseException, e:
                messages.error(request, u'拉取失败：{0}。'.format(str(e)))
            else:
                if status:
                    if data.get('button'):
                        Button.objects.filter(owner=account).delete()

                    top_i = 1
                    for top in data.get('button', []):
                        button = Button.objects.create(owner=account, name=top['name'], position=top_i)
                        if top.get('sub_button'):
                            sub_i = 1
                            for sub in top.get('sub_button'):
                                sub_button = Button()
                                sub_button.owner = account
                                sub_button.name = sub.get('name')
                                if not sub_button.name:
                                    messages.info(request, u'您的菜单因部分格式不正确，未能成功获取。')
                                    continue
                                sub_button.type = sub['type']
                                if sub_button.type == 'click':
                                    sub_button.key = sub.get('key', '')
                                else:
                                    sub_button.url = sub.get('url', '')
                                sub_button.parent = button
                                sub_button.position = sub_i
                                sub_button.save()
                                sub_i += 1
                        else:
                            button.type = top['type']
                            if button.type == 'view':
                                button.key = top.get('key', '')
                            else:
                                button.url = top.get('url', '')
                            button.save()
                        top_i += 1

                    messages.success(request, u'自定义菜单拉取成功。')
                else:
                    messages.error(request, u'操作失败：{0}。'.format(data))
        else:
            messages.error(request, u'您还没有填写微信配置，不能进行此操作')

        return HttpResponseRedirect(reverse('admin:weixin_button_changelist'))

    def push_menu(self, request, from_url=''):
        config = self.get_config(request)
        if config:
            buttons = []
            for top in Button.objects.filter(owner__id=self.account(request), parent=None).order_by('position'):
                top_dict = {
                    'name': top.name
                }
                if top.type:
                    top_dict['type'] = top.type
                    if top.type == 'view':
                        top_dict['url'] = top.url
                    else:
                        top_dict['key'] = top.key
                else:
                    subs = top.button_set.all().order_by('position')
                    if not subs:
                        messages.info(request, u'您的菜单<{0}>动作类型设定为父级菜单，但并不包含任何子菜单，本次上传将会忽略')

                    sub_buttons = []
                    for sub in subs:
                        sub_dict = {
                            'name': sub.name,
                            'type': sub.type,
                        }
                        if sub.type == 'view':
                            sub_dict['url'] = sub.url
                        else:
                            sub_dict['key'] = sub.key
                        sub_buttons.append(sub_dict)
                    top_dict['sub_button'] = sub_buttons
                buttons.append(top_dict)

            handler = PushMenu(config, {'button': buttons})
            try:
                result = handler.push()
            except BaseException, e:
                messages.error(request, u'推送失败：{0}。'.format(str(e)))
            else:
                if result:
                    messages.error(request, u'操作失败：{0}。'.format(result))
                else:
                    messages.success(request, u'自定义菜单已成功推至微信服务器。')
        else:
            messages.error(request, u'您还没有填写微信配置，不能进行此操作')

        return HttpResponseRedirect(reverse('admin:weixin_button_changelist'))


admin.site.register(Button, ButtonAdmin)
