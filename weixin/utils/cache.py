# -*-coding:utf-8 -*-
"""
Created on 2015-01-05

@author: Danny
DannyWork Project
"""

import redis

from django.conf import settings


connection = redis.Redis(host=getattr(settings, 'WEIXIN_REDIS_HOST', 'localhost'),
                         port=getattr(settings, 'WEIXIN_REDIS_PORT', 6379),
                         db=getattr(settings, 'WEIXIN_REDIS_DB', 0),
                         password=getattr(settings, 'WEIXIN_REDIS_PASSWORD', None),
                         socket_timeout=getattr(settings, 'WEIXIN_REDIS_SOCKET_TIMEOUT', None),
                         connection_pool=getattr(settings, 'WEIXIN_REDIS_CONNECTION_POOL', None),
                         charset=getattr(settings, 'WEIXIN_REDIS_CHARSET', 'utf-8'))
