# -*-coding:utf-8 -*-
"""
Created on 2013-11-18

@author: Danny
DannyWork Project
"""

import hashlib
import time
from bs4 import BeautifulSoup

from django.views.generic.base import View
from django.http.response import HttpResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.template.loader import render_to_string

from .models import EventReplyRule, Keyword, Config, Account, User
from signals import event_adder
from .handlers import pull_response
from utils.cryptor import WXBizMsgCrypt


class Weixin(View):
    account = None
    config = None
    user = None

    @method_decorator(csrf_exempt)
    def dispatch(self, request, uuid, *args, **kwargs):
        try:
            self.account = Account.objects.get(uuid=uuid, is_valid=True)
            self.config = Config.objects.get(owner=self.account)
        except (Account.DoesNotExist, Config.DoesNotExist):
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

    def validate(self, request):
        signature = request.REQUEST.get('signature', '')
        timestamp = request.REQUEST.get('timestamp', '')
        nonce = request.REQUEST.get('nonce',  '')

        tmp_str = hashlib.sha1(''.join(sorted([self.token, timestamp, nonce]))).hexdigest()
        if tmp_str == signature:
            return True

        return False

    def _get_reply(self, txt):
        txt, obj = txt.lower(), None
        for k in Keyword.get_exact_keywords(str(self.account.id)):
            k = unicode(k, encoding='utf8')
            if k == txt:
                obj = Keyword.objects.filter(owner=self.account, name=k)
                obj = obj[0] if obj else None
        if not obj:
            for k in Keyword.get_iexact_keywords(str(self.account.id)):
                k = unicode(k, encoding='utf8')
                if k in txt:
                    obj = Keyword.objects.filter(owner=self.account, name=k)
                    obj = obj[0] if obj else None
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
                    ident = str(t.ident)

                    event_ctx.update({
                        'ident': ident
                    })
                    event_adder.send(sender=self, **event_ctx)

                    res = pull_response('thread', ident)
                    print res
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
                    }.get(rule.msg_object._meta.model_name, 'text')
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

        print '***'
        print reply
        print '***'
        return reply

    def handle_msg(self, soup):
        msg_type = soup.MsgType.text
        if msg_type == 'text':
            user_message = soup.Content.text or ''
            rule = self._get_reply(user_message.lower())
        elif msg_type == 'location':
            user_message = {key.lower(): getattr(soup, key).text for key in ['Location_X', 'Location_Y', 'Scale', 'Label']}
            rule = None
        elif msg_type == 'image':
            user_message = {
                'pic_url': soup.PicUrl.text
            }
            rule = None
        else:
            user_message = ''
            rule = None

        return self.confirm_reply(soup, rule, user_message)

    def handle_event(self, soup):
        event_type = soup.Event.text
        all = EventReplyRule.objects.filter(owner=self.account, is_valid=True)
        rule = all.filter(event_type=event_type,
                          event_key=soup.EventKey.text if soup.EventKey and not soup.Event.text in ['subscribe', 'unsubscribe'] else '')
        rule = rule[0] if rule else None

        if event_type == 'location_select':
            base = soup.SendLocationInfo
            user_message = {key.lower(): getattr(base, key).text for key in ['Location_X', 'Location_Y', 'Scale', 'Label', 'Poiname']}
        elif event_type in ['scancode_waitmsg', 'scancode_push']:
            user_message = {
                'scan_type': soup.ScanCodeInfo.ScanType.text,
                'scan_result': soup.ScanResult.text
            }
        elif event_type in ['VIEW']:
            user_message = {
                'url': soup.EventKey.text,
            }
        elif event_type in ['CLICK']:
            user_message = {
                'key': soup.EventKey.text,
            }
        else:
            user_message = ''

        return self.confirm_reply(soup, rule, user_message)

    def get_soup(self, encrypt_type, msg_signature, timestamp, nonce, body):
        if encrypt_type == 'aes':
            decrypt = WXBizMsgCrypt(self.token, self.encoding_aes_key, self.app_id)
            ret, content = decrypt.decrypt_msg(body, msg_signature, timestamp, nonce)
            if ret:
                ctx = {
                    'type': 'ISP',
                    'belonging': self.account,
                    'processed_status': 'F',
                    'processed_message': 'Error in decryption: {0}'.format(ret)
                }
                event_adder.send(sender=self, **ctx)
        else:
            content = body

        return BeautifulSoup(content, features='xml')

    def init_user(self, from_username):
        self.user = User.objects.get_or_create(belonging=self.account, openid=from_username)[0]

    def get(self, request):
        if self.validate(request):
            return HttpResponse(request.REQUEST.get('echostr', ''))

        raise PermissionDenied

    def post(self, request):
        if not self.validate(request):
            raise PermissionDenied

        print '---'
        print request.body
        print '---'

        soup = self.get_soup(request.GET.get('encrypt_type', 'raw'),
                             request.GET.get('msg_signature', ''),
                             request.GET.get('timestamp', ''),
                             request.GET.get('nonce', ''),
                             request.body)

        if soup.MsgType:
            self.init_user(soup.FromUserName.text)

            if soup.MsgType.text in ['text', 'image', 'voice', 'video', 'location', 'link']:
                content = self.handle_msg(soup)
            elif soup.MsgType.text == 'event':
                content = self.handle_event(soup)

            if request.GET.get('encrypt_type', 'raw') == 'aes':
                encrypt = WXBizMsgCrypt(self.token, self.encoding_aes_key, self.app_id)
                ret, content = encrypt.encrypt_msg(content, request.GET.get('nonce', ''), request.GET.get('timestamp', ''))
        else:
            content = ''

        return HttpResponse(content)
