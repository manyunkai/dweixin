# -*-coding:utf-8 -*-
"""
Created on 2013-11-20

@author: Danny
DannyWork Project
"""

from django.db import models

from .auth import Account


class Button(models.Model):
    BUTTON_TYPE = (
        ('click', u'点击推事件'),
        ('view', u'跳转URL'),
        ('scancode_push', u'扫码推事件'),
        ('scancode_waitmsg', u'扫码推事件且弹出“消息接收中”提示框'),
        ('pic_sysphoto', u'弹出系统拍照发图'),
        ('pic_photo_or_album', u'弹出拍照或者相册发图'),
        ('pic_weixin', u'弹出微信相册发图器'),
        ('location_select', u'弹出地理位置选择器')
    )

    owner = models.ForeignKey(Account, verbose_name=u'账户')
    name = models.CharField(u'标题', max_length=40)
    type = models.CharField(u'响应动作类型', max_length=20, choices=BUTTON_TYPE, null=True, blank=True,
                            help_text=u'自定义菜单接口按钮类型，注意除click和view事件外，其余事件需要微信iPhone5.4.1以上版本支持。')
    parent = models.ForeignKey('self', verbose_name='父级菜单', null=True, blank=True)
    key = models.CharField(u'KEY值', max_length=128, blank=True)
    url = models.URLField(u'网页链接', blank=True)
    position = models.IntegerField(u'排序', default=0)

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'weixin'
        verbose_name = u'自定义菜单'
        verbose_name_plural = u'自定义菜单'
