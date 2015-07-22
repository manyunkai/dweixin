# -*-coding:utf-8 -*-
"""
Created on 2013-11-18

@author: Danny
DannyWork Project
"""

import urllib
import httplib
import json
import time

from django.http import HttpResponse
from django.core.cache import cache

from .codes import CODES

class ConnectionFailed(BaseException):
    pass


class GetAccessTokenFailed(BaseException):
    pass


class JsonResponseMixin(object):

    content_type = 'application/json'

    def render_json_to_response(self, status='0', data=None):
        res = {
            'status': status,
            'message': CODES.get(status, '')
        }
        if data:
            res['data'] = data

        return HttpResponse(json.dumps(res), content_type=self.content_type)


class ConnectMixin(object):
    host = 'api.weixin.qq.com'
    qy_host = 'qyapi.weixin.qq.com'
    port = '443'

    # configs for requesting access_token
    get_access_token_path = '/cgi-bin/token'
    get_access_token_path_qy = '/cgi-bin/gettoken'
    req_access_token_method = 'GET'

    # configs for the specified request
    method = 'GET'
    path = ''
    params = {}
    data = {}

    num_retry = 3

    def __init__(self, config):
        self.config = config

    @property
    def app_id(self):
        return self.config.app_id

    @property
    def app_secret(self):
        return self.config.secret

    def flush_access_token(self):
        if self.config.type == 'M':
            params = {
                'grant_type': 'client_credential',
                'appid': self.app_id,
                'secret': self.app_secret
            }
        else:
            params = {
                'corpid': self.app_id,
                'corpsecret': self.app_secret
            }

        start_time = time.time()
        account_type = self.config.type
        try:
            res = self._send_request(self.host if account_type == 'M' else self.qy_host,
                                     self.get_access_token_path if account_type == 'M' else self.get_access_token_path_qy,
                                     self.req_access_token_method,
                                     params=params)
        except ConnectionFailed:
            raise GetAccessTokenFailed('Connection failed.')
        else:
            if not res[0]:
                raise GetAccessTokenFailed(res[1])
            if res[1].get('errcode'):
                raise GetAccessTokenFailed(res[1].get('errmsg'))

            cache.set('access_token:belonging:{0}'.format(self.config.id),
                      res[1]['access_token'],
                      res[1]['expires_in'] - (time.time() - start_time))
            return res[1]['access_token']

    def get_access_token(self):
        if not self.app_id or not self.app_secret:
            raise GetAccessTokenFailed('Configuration Error.')

        token = cache.get('access_token:belonging:{0}'.format(self.config.id))
        if not token:
            token = self.flush_access_token()
        return token

    def _send_request(self, host, path, method, port=443, params=None, data=None):

        client = httplib.HTTPSConnection(host, port)

        path = '?'.join([path, urllib.urlencode(params or {})])
        data = json.dumps(data or {}, ensure_ascii=False)
        client.request(method, path, data.encode('utf8'))

        res = client.getresponse()
        if not res.status == 200:
            return False, res.status

        return True, json.loads(res.read())

    def go_request(self, data=None, port=None, with_access_token=True):
        data = data or {}
        params = self.params.copy()
        if with_access_token:
            params['access_token'] = self.get_access_token()

        for i in range(self.num_retry):
            status, data = self._send_request(self.host if self.config.type == 'M' else self.qy_host,
                                              self.path,
                                              self.method,
                                              port=port or self.port,
                                              params=params,
                                              data=data)
            if not status:
                raise ConnectionFailed(data)

            if data.get('errcode') == '40014':
                if i == (self.num_retry - 1):
                    raise GetAccessTokenFailed('Flush access_token failed after retried 3 times.')

                # access_token 无效或过期，在此刷新后重试
                self.flush_access_token()
                continue

            break

        return data


class PushMenu(ConnectMixin):
    """
    将自定义菜单推送至微信服务器。
    其中执行函数push如果成功，函数无返回。否则返回相应的错误信息。
    """

    method = 'POST'
    path = '/cgi-bin/menu/create'

    def __init__(self, config, menu, params=None):
        super(PushMenu, self).__init__(config)
        self.menu = menu
        self.params = params or {}

    def push(self):
        try:
            result = self.go_request(self.menu)
        except Exception, e:
            return str(e)
        if result.get('errcode'):
            return result.get('errmsg')


class PullMenu(ConnectMixin):
    """
    从微信服务器获取自定义菜单，该操作会覆盖本地数据库。
    其中执行函数pull总是返回一个元素，其第一个元素是状态值（True或False），
    第二个元素为错误消息或返回的menu数据（已解析为字典）。
    """

    method = 'GET'
    path = '/cgi-bin/menu/get'

    def pull(self):
        try:
            result = self.go_request()
        except Exception, e:
            return False, str(e)

        if result.get('errcode'):
            return False, result.get('errmsg')
        return True, result.get('menu', {})


class BaseCustomerServicePusher(ConnectMixin):
    """
    基本的客服消息推送。
    """

    method = 'POST'
    path = '/cgi-bin/message/custom/send'

    def push(self, content):
        try:
            result = self.go_request(content)
        except Exception, e:
            return False, str(e)

        if result.get('errcode'):
            return False, result.get('errmsg')
        return True, 'succeed.'
