# -*-coding:utf-8 -*-
"""
Created on 2015-01-05

@author: Danny
DannyWork Project
"""

import json

from .mixins import BaseCustomerServicePusher
from .utils.cache import connection
from .models import Config, Event

PROCESSED_POOL_PREFIX = 'event:pool:processed:{0}'
PENDING_POOL_PREFIX = 'event:pool:pending:{0}'
THREADING_POOL_PREFIX = 'event:pool:thread:{0}'


def pull_response(ptype, ident, timeout=3):
    cache_key = 'event:pool:{0}:{1}'.format(ptype, ident)
    res = connection.brpop(cache_key, timeout)
    event = None
    reply = ''
    if res:
        try:
            res = json.loads(res[1])
        except:
            status = False
            message = 'Parse Error in response.'
        else:
            try:
                event = Event.objects.get(id=res.get('event'))
            except Event.DoesNotExist:
                status = False
                message = 'Event not found.'
            else:
                if res.get('status', 0):
                    reply = res.get('reply', {})
                    status = True
                    message = 'Success.'
                else:
                    reply = ''
                    status = False
                    message = res.get('message')
                event.processed_status = 'S' if status else 'F'
                event.processed_message = message
                event.reply = reply
                event.save()
    else:
        status = False
        message = 'Time out.'

    return {'status': status, 'message': message, 'reply': reply, 'event': event}


def handle_customer_service_msg(pool, timeout=10):
    res = pull_response('processed', pool, timeout)
    if res.get('status'):
        event = res.get('event')
        try:
            config = Config.objects.filter(owner=event.belonging)[0]
        except IndexError:
            return False, 'Config error for account {0}'.format(res.get('account').username)

        content = res.get('reply')
        content['touser'] = event.from_user.openid

        return BaseCustomerServicePusher(config).push(content)
    return False, res.get('message')
