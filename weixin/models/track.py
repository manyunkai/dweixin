# -*-coding:utf-8 -*-
# 
# Copyright (C) 2012-2015 Lianbi TECH Co., Ltd. All rights reserved.
# Created on 2015-06-24, by Danny
# 
#

__author__ = 'Danny'

from django.db import models

from .auth import Account
from .user import User


class LocTrack(models.Model):
    """
    地理位置上报记录
    """

    belonging = models.ForeignKey(Account, verbose_name=u'账户')

    user = models.ForeignKey(User, verbose_name=u'用户')

    lng = models.FloatField(u'经度')
    lat = models.FloatField(u'纬度')
    precision = models.FloatField(u'精度')

    created = models.DateTimeField(u'创建时间', auto_now_add=True)

    class Meta:
        app_label = 'weixin'
        verbose_name = u'地理位置上报记录'
        verbose_name_plural = u'地理位置上报记录'
