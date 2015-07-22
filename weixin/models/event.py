# -*-coding:utf-8 -*-
"""
Created on 2015-01-06

@author: Danny
DannyWork Project
"""

import json
import time

from django.db import models
from django.db.models.signals import pre_save
from django.utils import timezone

from .auth import Account
from .user import User
from .track import LocTrack
from ..signals import event_adder
from ..utils.cache import connection


class Event(models.Model):
    """
    记录所有微信用户触发的事件及响应状态
    其中事件类型包括以下几种：
        内部处理： 表示该事件由本应用自身进行处理，目前该类型对应均为同步事件处理；
        外部同步处理：表示该事件由外部应用进行处理，本应用本身仅路由和转发，同步处理代表本应用始终阻塞并等待外部应用的处理响应；
        外部异步处理：表示该事件由外部应用进行处理，本应用本身仅路由和转发，异步处理代表本应用直接向公众号回送空返回，
                    在外部应用处理完后利用“客服”接口再次向用户回送消息。该模式需要公众号具有“客服”接口权限，且要求本应用配置了缓存。
    """

    EVENT_TYPE = (
        ('ISP', u'内部处理'),
        ('OSP', u'外部同步处理'),
        ('OAP', u'外部异步处理')
    )
    PROCESSED_STATUS_CHOICES = (
        ('W', u'等待处理'),
        ('S', u'处理成功'),
        ('F', u'处理失败')
    )

    type = models.CharField(u'类型', max_length=3, choices=EVENT_TYPE)
    pool = models.CharField(u'队列池编号', max_length=4, null=True, blank=True)
    ident = models.CharField(u'线程编号', max_length=128, null=True, blank=True)

    belonging = models.ForeignKey(Account, verbose_name=u'账户')
    from_user = models.ForeignKey(User, verbose_name=u'微信用户', blank=True, null=True)
    user_message = models.CharField(u'用户消息', max_length=1000, default='', blank=True)

    created = models.DateTimeField(u'发起时间', auto_now_add=True)

    processed_status = models.CharField(u'处理状态', max_length=1, choices=PROCESSED_STATUS_CHOICES, default='W')
    processed_message = models.CharField(u'状态消息', max_length=64, null=True, blank=True)
    processed_at = models.DateTimeField(u'处理时间', null=True, blank=True)

    reply = models.CharField(u'返回内容', max_length=10000, null=True, blank=True)

    class Meta:
        app_label = 'weixin'
        verbose_name = u'事件记录'
        verbose_name_plural = u'事件记录'


PROCESSED_POOL_PREFIX = 'event:pool:processed:{0}'
PENDING_POOL_PREFIX = 'event:pool:pending:{0}'
THREADING_POOL_PREFIX = 'event:pool:thread:{0}'


def event_pre_save(sender=None, **kwargs):
    instance = kwargs.get('instance')
    if not instance.processed_status == 'W':
        instance.processed_at = timezone.now()


def add_event(sender=None, **kwargs):
    kwargs.pop('signal')
    user_message = kwargs.get('user_message', '')
    if not isinstance(user_message, str):
        kwargs['user_message'] = json.dumps(user_message)
    event = Event.objects.create(**kwargs)

    data = {
        'id': event.id,
        'pool': event.pool,
        'ident': event.ident,
        'belonging': event.belonging.id,
        'from_user': event.from_user.openid,
        'user_message': user_message,
        'created': time.mktime(event.created.timetuple())
    }

    if not event.type == 'ISP':
        loc = LocTrack.objects.filter(user=event.from_user).order_by('-created')[:1]
        if loc:
            loc = loc[0]
            data['location'] = [loc.lng, loc.lat]
        connection.lpush(PENDING_POOL_PREFIX.format(event.pool), json.dumps(data))


pre_save.connect(event_pre_save, sender=Event)
event_adder.connect(add_event)
