# -*-coding:utf-8 -*-
"""
Created on 2013-11-18

@author: Danny
DannyWork Project
"""

import re
import time
import uuid
import hashlib
import base64
from bs4 import BeautifulSoup

from django.conf import settings
from django.views.generic.base import View
from django.http.response import HttpResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.template.loader import render_to_string

from .models import EventReplyRule, Keyword, Config, Account, User, LocTrack
from .mixins import JsonResponseMixin
from .signals import event_adder
from .handlers import pull_response
from .utils.cryptor import WXBizMsgCrypt, Prpcrypt
from .utils.ip import get_client_ip


class Weixin(View):
    account = None
    config = None
    user = None

    @method_decorator(csrf_exempt)
    def dispatch(self, request, uuid, *args, **kwargs):
        try:
            self.account = Account.objects.filter(uuid=uuid, is_valid=True)[0]
            self.config = Config.objects.filter(owner=self.account)[0]
        except IndexError:
            raise PermissionDenied

        return super(Weixin, self).dispatch(request, *args, **kwargs)

    @property
    def token(self):
        return self.config.token

    @property
    def encoding_aes_key(self):
        return self.config.encoding_aes_key

    @property
    def app_id(self):
        return self.config.app_id

    @property
    def account_type(self):
        return self.config.type

    def validate(self, request):
        signature = request.REQUEST.get('signature' if self.account_type == 'M' else 'msg_signature', '')
        timestamp = request.REQUEST.get('timestamp', '')
        nonce = request.REQUEST.get('nonce',  '')
        echo_str = request.REQUEST.get('echostr', '')

        l = [self.token, timestamp, nonce]
        if self.account_type == 'Q':
            if echo_str:
                l.append(echo_str)
            else:
                soup = BeautifulSoup(request.body, features='xml')
                if not soup or not soup.Encrypt:
                    return False
                l.append(soup.Encrypt.text)
        l.sort()

        tmp_str = hashlib.sha1(''.join(l)).hexdigest()
        if tmp_str == signature:
            return True

        return False

    def _get_reply(self, txt, agent_id):
        txt, obj = txt.lower(), None
        for k in Keyword.get_exact_keywords(str(self.account.id), agent_id):
            k = unicode(k, encoding='utf8')
            if k.startswith('(') and k.endswith(')') and re.match(u'^' + k[1:-1] + u'$', txt) or k == txt:
                # 如果关键字以“(”开头且已“)”结尾，则作正则表达式处理
                qs = Keyword.objects.filter(owner=self.account, name=k, exact_match=True)
                qs = qs.filter(rule__agent__agent_id=agent_id) if agent_id else qs.filter(rule__agent_id=None)
                obj = qs[0] if qs else None
        if not obj:
            for k in Keyword.get_iexact_keywords(str(self.account.id), agent_id):
                k = unicode(k, encoding='utf8')
                if k.startswith('(') and k.endswith(')') and re.search(k[1:-1], txt) or k in txt:
                    qs = Keyword.objects.filter(owner=self.account, name=k, exact_match=False)
                    qs = qs.filter(rule__agent__agent_id=agent_id) if agent_id else qs.filter(rule__agent_id=None)
                    obj = qs[0] if qs else None
        return obj.rule if obj and obj.rule.is_valid else None

    def confirm_reply(self, soup, rule, user_message=''):
        if rule:
            if rule.res_msg_type in ['oahdl', 'oshdl']:
                # 外部同步和异步处理
                event_ctx = {
                    'type': 'OSP' if rule.res_msg_type == 'oshdl' else 'OAP',
                    'pool': rule.pool,
                    'belonging': self.account,
                    'from_user': self.user,
                    'user_message': user_message
                }
                if rule.res_msg_type == 'oshdl':
                    # 如果是同步处理类型，则在此等待返回或超时默认返回
                    # 获取当前线程的标识符用于缓存key
                    import threading
                    t = threading.currentThread()
                    ident = '-'.join([str(t.ident), str(uuid.uuid1())])

                    event_ctx.update({
                        'ident': ident
                    })
                    event_adder.send(sender=self, **event_ctx)

                    res = pull_response('thread', ident)
                    if res.get('status', False):
                        ctx = {
                            'to_user': soup.FromUserName.text,
                            'from_user': soup.ToUserName.text,
                            'create_time': int(time.time()),
                            'msg_type': res['reply'].get('msgtype'),
                            'reply': res['reply'].get(res['reply'].get('msgtype'))
                        }
                        reply = render_to_string('xml/message_for_json.xml', ctx)
                    else:
                        reply = ''
                else:
                    # 如果是异步处理类型，则直接向用户返回空内容，并将事件交由外部处理。
                    event_adder.send(sender=self, **event_ctx)
                    reply = ''
            else:
                # 内部处理
                render_ctx = {
                    'to_user': soup.FromUserName.text,
                    'from_user': soup.ToUserName.text,
                    'create_time': int(time.time()),
                    'reply': rule,
                    'msg_type': {
                        'textmsg': 'text',
                        'newsmsg': 'news'
                    }.get(rule.msg_object._meta.model_name, 'text'),
                    'extra_params': ''
                }
                reply = render_to_string('xml/message.xml', render_ctx)

                event_ctx = {
                    'type': 'ISP',
                    'belonging': self.account,
                    'from_user': self.user,
                    'processed_status': 'S',
                    'processed_message': u'响应成功',
                    'reply': reply,
                    'user_message': user_message
                }
                event_adder.send(sender=self, **event_ctx)
        else:
            reply = ''
            event_ctx = {
                'type': 'ISP',
                'belonging': self.account,
                'from_user': self.user,
                'processed_status': 'S',
                'processed_message': u'响应成功，但响应实体为空',
                'reply': reply,
                'user_message': user_message
            }
            event_adder.send(sender=self, **event_ctx)

        return reply

    def handle_msg(self, soup):
        msg_type = soup.MsgType.text
        user_message = {
            'event': 'message',
            'msg_type': msg_type,
        }

        # agent_id 在企业号中代表企业应用 ID，当为公众号或 AgentID 无效的时候都置为 0
        # 在数据查询时，只要 agent_id 为 0 则当 None 处理
        try:
            agent_id = int(soup.AgentID.text) if soup.AgentID else 0
        except (TypeError, ValueError):
            agent_id = 0

        if msg_type == 'text':
            content = (soup.Content.text or '').lower()
            user_message['content'] = content
            rule = self._get_reply(content, agent_id)
        elif msg_type == 'location':
            user_message.update({key.lower(): getattr(soup, key).text for key in ['Location_X', 'Location_Y', 'Scale', 'Label']})
            rule = None
        elif msg_type == 'image':
            user_message.update({
                'pic_url': soup.PicUrl.text
            })
            rule = None
        else:
            user_message = ''
            rule = None

        return self.confirm_reply(soup, rule, user_message)

    def handle_event(self, soup):
        event_type = soup.Event.text

        # agent_id 在企业号中代表企业应用 ID，当为公众号或 AgentID 无效的时候都置为 0
        # 在数据查询时，只要 agent_id 为 0 则当 None 处理
        try:
            agent_id = int(soup.AgentID.text) if soup.AgentID else 0
        except (TypeError, ValueError):
            agent_id = 0

        query = {
            'owner': self.account,
            'is_valid': True,
            'event_type': event_type,
            'event_key': soup.EventKey.text if soup.EventKey and not soup.Event.text in ['subscribe', 'unsubscribe'] else '',
            'agent__agent_id': agent_id if agent_id else None
        }
        rule = EventReplyRule.objects.filter(**query)
        rule = rule[0] if rule else None

        user_message = {
            'event': 'event',
            'event_type': event_type
        }
        if event_type == 'location_select':
            base = soup.SendLocationInfo
            user_message.update({key.lower(): getattr(base, key).text for key in ['Location_X', 'Location_Y', 'Scale', 'Label', 'Poiname']})
        elif event_type in ['scancode_waitmsg', 'scancode_push']:
            user_message.update({
                'scan_type': soup.ScanCodeInfo.ScanType.text,
                'scan_result': soup.ScanResult.text
            })
        elif event_type in ['VIEW']:
            user_message.update({
                'url': soup.EventKey.text,
            })
        elif event_type in ['CLICK']:
            user_message.update({
                'key': soup.EventKey.text,
            })
        else:
            user_message = ''

        return self.confirm_reply(soup, rule, user_message)

    def get_soup(self, encrypt_type, msg_signature, timestamp, nonce, body, callback_if_failed=True):
        if encrypt_type == 'aes':
            decrypt = WXBizMsgCrypt(self.token, self.encoding_aes_key, self.app_id)
            ret, content = decrypt.decrypt_msg(body, msg_signature, timestamp, nonce)
            if ret and callback_if_failed:
                ctx = {
                    'type': 'ISP',
                    'belonging': self.account,
                    'processed_status': 'F',
                    'processed_message': 'Error in decryption: {0}'.format(ret)
                }
                event_adder.send(sender=self, **ctx)
        else:
            content = body

        return BeautifulSoup(content or '', features='xml')

    def init_user(self, from_username):
        try:
            user = User.objects.filter(belonging=self.account, openid=from_username, is_deleted=False)[0]
        except IndexError:
            user = User()
            user.belonging = self.account
            user.openid = from_username

        user.is_valid = True
        user.save()

        self.user = user
        return True

    def delete_user(self):
        self.user.is_deleted = True
        self.user.save()

    def get(self, request):
        if self.validate(request):
            echo_str = request.REQUEST.get('echostr', '')
            if self.account_type == 'Q':
                # 企业号需解密 echostr
                key = base64.b64decode(self.encoding_aes_key + '=')
                if not len(key) == 32:
                    # 无效的 encoding_aes_key
                    raise PermissionDenied

                pc = Prpcrypt(key)
                ret, echo_str = pc.decrypt(echo_str, self.app_id)
                if ret:
                    # 解密错误
                    raise PermissionDenied
            return HttpResponse(echo_str)

        raise PermissionDenied

    def post(self, request):
        if not self.validate(request):
            raise PermissionDenied

        encrypt_type = request.GET.get('encrypt_type', 'raw') if self.account_type == 'M' else 'aes'

        # 企业号始终为 AES 加密模式
        # 公众号根据 encrypt_type 参数判断
        soup = self.get_soup(encrypt_type,
                             request.GET.get('msg_signature', ''),
                             request.GET.get('timestamp', ''),
                             request.GET.get('nonce', ''),
                             request.body)
        content = ''

        if soup.MsgType and self.init_user(soup.FromUserName.text):
            if self.user.is_valid:
                if soup.MsgType.text in ['text', 'image', 'voice', 'video', 'location', 'link']:
                    content = self.handle_msg(soup)
                elif soup.MsgType.text == 'event':
                    event_type = soup.Event.text
                    if event_type == 'LOCATION':
                        # 用户地理位置上报，在此记录位置信息
                        try:
                            lng = float(soup.Longitude.text)
                            lat = float(soup.Latitude.text)
                            precision = float(soup.Precision.text)
                        except (TypeError, ValueError):
                            pass
                        else:
                            LocTrack.objects.create(belonging=self.account,
                                                    user=self.user,
                                                    lng=lng,
                                                    lat=lat,
                                                    precision=precision)
                    elif event_type == 'unsubscribe':
                        # 用户取消订阅事件，在此删除用户
                        self.delete_user()
                    else:
                        content = self.handle_event(soup)
            else:
                # 目前针对未授权情况置空处理
                pass

        if content and encrypt_type == 'aes':
            encrypt = WXBizMsgCrypt(self.token, self.encoding_aes_key, self.app_id)
            ret, content = encrypt.encrypt_msg(content, request.GET.get('nonce', ''), request.GET.get('timestamp', ''))

        return HttpResponse(content)


class UserLocationFetching(JsonResponseMixin, View):
    """
    用户位置信息获取
    """

    param_list = ['openid']

    def dispatch(self, request, *args, **kwargs):
        if not get_client_ip(request) in settings.USER_LOCATION_FETCHING_ALLOWED_IPS:
            raise PermissionDenied

        return super(UserLocationFetching, self).dispatch(request, *args, **kwargs)

    def get(self, request):
        # 参数校验
        for key in self.param_list:
            if not request.GET.get(key, None):
                return self.render_json_to_response('1003')

        loc = LocTrack.objects.filter(user__openid=request.GET.get('openid')).order_by('-created')[:1]
        if loc:
            loc = loc[0]
            ctx = {
                'point': [loc.lng, loc.lat],
                'precision': loc.precision,
                'updated': loc.created.strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            ctx = {}

        return self.render_json_to_response(data=ctx)
