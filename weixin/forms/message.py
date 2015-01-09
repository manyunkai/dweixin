# -*-coding:utf-8 -*-
"""
Created on 2015-01-07

@author: Danny
DannyWork Project
"""

import os

from django import forms
from django.core.exceptions import ObjectDoesNotExist

from ..models import EventReplyRule, MediaItem, TextMsg, NewsMsgItem


class NewsMsgItemForm(forms.ModelForm):

    class Meta:
        model = NewsMsgItem
        widgets = {
            'description': forms.Textarea
        }


class TextMsgForm(forms.ModelForm):

    class Meta:
        model = TextMsg
        widgets = {
            'content': forms.Textarea
        }


MEDIA_MAX_SIZE = 100
MEDIA_ALLOW_TYPES = {
    'mp3': 'audio file'
}


class MediaItemForm(forms.ModelForm):
    def clean_file(self):
        value = self.cleaned_data.get('file')
        if value:
            if value.size > MEDIA_MAX_SIZE * 1024 * 1024:
                raise forms.ValidationError(u'上传的文件不能大于{0}M'.format(MEDIA_MAX_SIZE))

            #m = magic.Magic(magic_file='D:\\Program Files (x86)\\GnuWin32\\share\\misc\\magic')
            #format = m.from_buffer(value.read(1024))

            ext = os.path.splitext(value.name)[1].lstrip('.')

            if not ext in MEDIA_ALLOW_TYPES.keys():# or not MEDIA_ALLOW_TYPES[ext] in format.lower():
                raise forms.ValidationError(u'该文件格式不支持'.format(MEDIA_MAX_SIZE))
        return value

    class Meta:
        model = MediaItem


class EventReplyRuleForm(forms.ModelForm):

    def clean(self):
        if not self.cleaned_data.get('res_msg_type') in ['oahdl', 'oshdl'] and not self.cleaned_data.get('msg_object_object_id'):
            self._errors['msg_object_object_id'] = self.error_class([u'非外部处理事件必须提供应用内的消息响应。'])
        if self.cleaned_data.get('res_msg_type') in ['oahdl', 'oshdl'] and not self.cleaned_data.get('pool'):
            self._errors['pool'] = self.error_class([u'外部处理事件必须提供队列池编号。'])
        ct = self.cleaned_data.get('msg_object_content_type')
        if ct:
            try:
                rel_obj = ct.get_object_for_this_type(pk=self.cleaned_data.get('msg_object_object_id'))
            except ObjectDoesNotExist:
                pass

        return super(EventReplyRuleForm, self).clean()

    class Meta:
        model = EventReplyRule
