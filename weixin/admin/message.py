# -*-coding:utf-8 -*-
"""
Created on 2013-11-20

@author: Danny
DannyWork Project
"""

from django.contrib import admin
from django.core.urlresolvers import reverse

from ..models import TextMsg, NewsMsg, NewsMsgItem,\
    NewsMsgItemMapping, Keyword, EventReplyRule, MsgReplyRule, MediaMsg,\
    MediaItem
from ..forms import NewsMsgItemForm, TextMsgForm, MediaItemForm
from ..forms.message import EventReplyRuleForm
from .base import OwnerBasedModelAdmin


class KeywordInline(admin.TabularInline):
    model = Keyword
    fields = ['name', 'exact_match']


class MsgReplyRuleAdmin(OwnerBasedModelAdmin):
    fields = ['name', 'res_msg_type', 'pool', 'msg_object_content_type',
              'msg_object_object_id', 'is_valid']
    list_display = ['name', 'related_object', 'is_valid']
    related_lookup_fields = {
        'generic': [['msg_object_content_type', 'msg_object_object_id']],
    }
    list_editable = ['is_valid']
    inlines = [KeywordInline]

    def related_object(self, obj):
        if obj.msg_object:
            info = obj.msg_object._meta.app_label, obj.msg_object._meta.module_name
            url = reverse('admin:{0}_{1}_change'.format(*info), args=[obj.msg_object.id])
            return u'<a href="{0}">{1}</a>'.format(url, obj.msg_object.name)
        return ''
    related_object.short_description = u'关联消息'
    related_object.allow_tags = True


class KeywordAdmin(OwnerBasedModelAdmin):
    fields = ['name', 'exact_match']
    list_display = ['name', 'exact_match', 'related_object']

    def related_object(self, obj):
        return u'<a href="{0}">{1}</a>'.format(reverse('admin:weixin_msgreplyrule_change', args=[obj.rule.id]), obj.rule.name)
    related_object.short_description = u'关联规则'
    related_object.allow_tags = True


class TextMsgAdmin(OwnerBasedModelAdmin):
    fields = ['name', 'content']
    list_display = ['name', 'content']
    form = TextMsgForm

    def to_field_allowed(self, request, to_field):
        return True


class MsgItemsInline(admin.TabularInline):
    model = NewsMsgItemMapping
    max_num = 10

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'newsmsgitem':
            kwargs['queryset'] = NewsMsgItem.objects.filter(owner__username=request.user.username)
        return super(MsgItemsInline, self).formfield_for_foreignkey(db_field, request, **kwargs)


class NewsMsgAdmin(OwnerBasedModelAdmin):
    fields = ['name']
    list_display = ['name', 'news']
    inlines = [MsgItemsInline]

    def news(self, obj):
        return u', '.join([item.title for item in obj.items.all()])
    news.short_description = u'关联的消息实体'

    def to_field_allowed(self, request, to_field):
        return True


class NewsMsgItemAdmin(OwnerBasedModelAdmin):
    fields = ['title', 'pic_large', 'pic_small', 'url', 'description']
    form = NewsMsgItemForm
    list_display = ['title', 'description']

    def save_model(self, request, obj, form, change):
        obj.name = obj.title
        super(NewsMsgItemAdmin, self).save_model(request, obj, form, change)


class EventReplyAdmin(OwnerBasedModelAdmin):
    fields = ['name', 'event_type', 'event_key', 'res_msg_type', 'pool',
              'msg_object_content_type', 'msg_object_object_id']
    list_display = ['name', 'event_type', 'event_key',
                    'msg_object_content_type', 'related_object']
    related_lookup_fields = {
        'generic': [['msg_object_content_type', 'msg_object_object_id']],
    }
    form = EventReplyRuleForm

    def related_object(self, obj):
        if obj.msg_object:
            info = obj.msg_object._meta.app_label, obj.msg_object._meta.module_name
            url = reverse('admin:{0}_{1}_change'.format(*info), args=[obj.msg_object.id])
            return u'<a href="{0}">{1}</a>'.format(url, obj.msg_object.name)
        return ''
    related_object.short_description = u'关联消息'
    related_object.allow_tags = True


class MediaItemAdmin(OwnerBasedModelAdmin):
    fields = ['title', 'file', 'description']
    form = MediaItemForm

    def save_model(self, request, obj, form, change):
        obj.name = obj.title
        super(MediaItemAdmin, self).save_model(request, obj, form, change)


class MediaMsgAdmin(OwnerBasedModelAdmin):
    fields = ['name', 'item']
    list_display = ['name', 'related_object']

    def related_object(self, obj):
        info = obj.item._meta.app_label, obj.item._meta.module_name
        url = reverse('admin:{0}_{1}_change'.format(*info), args=[obj.item_id])
        return u'<a href="{0}">{1}</a>'.format(url, obj.item.name)
    related_object.short_description = u'关联的媒体'
    related_object.allow_tags = True

    def to_field_allowed(self, request, to_field):
        return True


admin.site.register(Keyword, KeywordAdmin)
admin.site.register(TextMsg, TextMsgAdmin)
admin.site.register(NewsMsg, NewsMsgAdmin)
admin.site.register(MediaMsg, MediaMsgAdmin)
admin.site.register(MediaItem, MediaItemAdmin)
admin.site.register(NewsMsgItem, NewsMsgItemAdmin)
admin.site.register(EventReplyRule, EventReplyAdmin)
admin.site.register(MsgReplyRule, MsgReplyRuleAdmin)
