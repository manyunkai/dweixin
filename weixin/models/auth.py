# -*-coding:utf-8 -*-
"""
Created on 2013-11-20

@author: Danny
DannyWork Project
"""

import uuid

from django.db import models
from django.db.models.signals import pre_save


class Account(models.Model):
    username = models.CharField(u'账户名', max_length=32)
    uuid = models.CharField(u'账户标识', max_length=64)
    created = models.DateTimeField(u'创建时间', auto_now_add=True)
    is_valid = models.BooleanField(u'有效状态', default=True)

    def __unicode__(self):
        return self.username

    class Meta:
        app_label = 'weixin'
        verbose_name = u'账户'
        verbose_name_plural = u'账户'


class Config(models.Model):
    owner = models.ForeignKey(Account, verbose_name=u'账户')
    token = models.CharField(u'Token', max_length=32,
                             help_text=u'填写微信公众号接口配置里的Token，3-32个字符。')
    app_id = models.CharField(u'AppId', max_length=32, default='', blank=True,
                              help_text=u'开发者账号唯一凭证')
    secret = models.CharField(u'AppSecret', max_length=32, default='', blank=True,
                              help_text=u'开发者账号唯一凭证密钥')
    encoding_aes_key = models.CharField(u'EncodingAESKey', max_length=43, default='', blank=True,
                                        help_text=u'消息加密密钥')

    class Meta:
        app_label = 'weixin'
        verbose_name = u'公众号配置'
        verbose_name_plural = u'公众号配置'


def account_pre_save(sender=None, **kwargs):
    instance = kwargs.get('instance')
    if not instance.uuid:
        instance.uuid = ''.join(str(uuid.uuid4()).split('-'))

pre_save.connect(account_pre_save, sender=Account)
