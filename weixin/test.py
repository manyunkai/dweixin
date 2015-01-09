# -*-coding:utf-8 -*-
"""
Created on 2015-01-07

@author: Danny
DannyWork Project
"""

import json
import random
import time

from .handlers import PENDING_POOL_PREFIX, THREADING_POOL_PREFIX, PROCESSED_POOL_PREFIX, connection, \
    handle_customer_service_msg


test_reply = [
    {
        'msgtype': 'text',
        'text': {
            'content': u'这是一个外部处理测试。'
        }
    },
    {
        'msgtype': 'news',
        'news': {
            'articles': [
                {
                    'title': 'Danny\'s Avatar',
                    'description': 'Danny\'s Avatar.',
                    'url': 'http://www.dannysite.com/',
                    'picurl': 'http://www.dannysite.com/static/site/v3/img/cover.jpg'
                },
                {
                    'title': 'Time of Life',
                    'description': 'Time of Life',
                    'url': 'http://www.dannysite.com/',
                    'picurl': 'http://www.dannysite.com/media/images/uploads/103e54d0-7ef0-11e4-96fa-00163e0309b4.jpg'
                }
            ]
        }
    }
]


def pull_request():
    while True:
        print 'Waiting for request.'

        req = connection.brpop(PENDING_POOL_PREFIX.format('1'))
        if req:
            try:
                req = json.loads(req[1])
            except:
                print 'Json Loaded Error.'
                continue

        print 'Loaded request'
        print req

        res = {
            'status': 1,
            'message': 'success',
            'event': req.get('id'),
            'reply': random.choice(test_reply)
        }

        print 'Response:'
        print res

        ident = req.get('ident')
        cache_key = THREADING_POOL_PREFIX.format(ident) if ident else PROCESSED_POOL_PREFIX.format('1')

        print 'Push to:', cache_key

        connection.lpush(cache_key, json.dumps(res))
        if ident:
            # 如果是基于线程的，则设置 key 的超时时间。
            # 因为其监听线程可能已经退出，在此情况下如果 key 不过期则会造成垃圾数据。
            connection.expire(cache_key, 5)

        print 'Push succeed.'


def cs_robot():
    while True:
        print 'Waiting for message.'

        time.sleep(10)

        print handle_customer_service_msg(1, 10)
