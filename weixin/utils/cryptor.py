#-*- encoding:utf-8 -*-

import base64
import string
import random
import hashlib
import time
import struct
import socket
import xml.etree.cElementTree as ET

from Crypto.Cipher import AES

import errors


class FormatException(Exception):
    pass


def throw_exception(message, exception_class=FormatException):
    """
    Exception raising function.
    """

    raise exception_class(message)


class SHA1(object):
    """
    计算公众平台的消息签名接口
    """

    def get_sha1(self, token, timestamp, nonce, encrypt):
        """
        用SHA1算法生成安全签名
        @param token:  票据
        @param timestamp: 时间戳
        @param encrypt: 密文
        @param nonce: 随机字符串
        @return: 安全签名
        """

        try:
            sortlist = [token, timestamp, nonce, encrypt]
            sortlist.sort()
            sha = hashlib.sha1()
            sha.update(''.join(sortlist))
            return errors.WXBizMsgCrypt_OK, sha.hexdigest()
        except Exception,e:
            return errors.WXBizMsgCrypt_ComputeSignature_Error, None


class XMLParse(object):
    """
    提供提取消息格式中的密文及生成回复消息格式的接口
    """

    # xml 消息模板
    AES_TEXT_RESPONSE_TEMPLATE = """
<xml>
<Encrypt><![CDATA[%(msg_encrypt)s]]></Encrypt>
<MsgSignature><![CDATA[%(msg_signature)s]]></MsgSignature>
<TimeStamp>%(timestamp)s</TimeStamp>
<Nonce><![CDATA[%(nonce)s]]></Nonce>
</xml>
"""

    def extract(self, xmltext):
        """
        提取出xml数据包中的加密消息
        @param xmltext: 待提取的xml字符串
        @return: 提取出的加密消息字符串
        """

        try:
            xml_tree = ET.fromstring(xmltext)
            encrypt = xml_tree.find('Encrypt')
            touser_name = xml_tree.find('ToUserName')
            return errors.WXBizMsgCrypt_OK, encrypt.text, touser_name.text
        except Exception, e:
            return errors.WXBizMsgCrypt_ParseXml_Error, None, None

    def generate(self, encrypt, signature, timestamp, nonce):
        """
        生成xml消息
        @param encrypt: 加密后的消息密文
        @param signature: 安全签名
        @param timestamp: 时间戳
        @param nonce: 随机字符串
        @return: 生成的xml字符串
        """

        resp_dict = {
            'msg_encrypt': encrypt,
            'msg_signature': signature,
            'timestamp': timestamp,
            'nonce': nonce
        }
        resp_xml = self.AES_TEXT_RESPONSE_TEMPLATE % resp_dict
        return resp_xml


class PKCS7Encoder(object):
    """
    提供基于PKCS7算法的加解密接口
    """

    block_size = 32

    def encode(self, text):
        """
        对需要加密的明文进行填充补位
        @param text: 需要进行填充补位操作的明文
        @return: 补齐明文字符串
        """

        text_length = len(text)

        # 计算需要填充的位数
        amount_to_pad = self.block_size - (text_length % self.block_size)
        amount_to_pad = self.block_size if amount_to_pad == 0 else amount_to_pad

        # 获得补位所用的字符
        pad = chr(amount_to_pad)

        return text + pad * amount_to_pad

    def decode(self, decrypted):
        """
        删除解密后明文的补位字符
        @param decrypted: 解密后的明文
        @return: 删除补位字符后的明文
        """

        pad = ord(decrypted[-1])
        pad = 0 if pad < 1 or pad > 32 else pad

        return decrypted[:-pad]


class Prpcrypt(object):
    """
    提供接收和推送给公众平台消息的加解密接口
    """

    RANDOM_STR_RULE = string.letters + string.digits

    def __init__(self, key):
        self.key = key

        # 设置加解密模式为 AES 的 CBC 模式
        self.mode = AES.MODE_CBC

    def get_random_str(self):
        """
        随机生成16位字符串
        @return: 16位字符串
        """

        return ''.join(random.sample(self.RANDOM_STR_RULE, 16))

    def encrypt(self, text, appid):
        """
        对明文进行加密
        @param text: 需要加密的明文
        @return: 加密得到的字符串
        """

        # 16位随机字符串添加到明文开头
        text = text.encode('utf-8')
        appid = appid.encode('utf-8')
        text = ''.join([self.get_random_str(), struct.pack('I', socket.htonl(len(text))), text, appid])

        # 使用自定义的填充方式对明文进行补位填充
        text = PKCS7Encoder().encode(text)

        # 加密
        cryptor = AES.new(self.key, self.mode, self.key[:16])
        try:
            ciphertext = cryptor.encrypt(text)
            # 使用 BASE64 对加密后的字符串进行编码
            return errors.WXBizMsgCrypt_OK, base64.b64encode(ciphertext)
        except Exception, e:
            return errors.WXBizMsgCrypt_EncryptAES_Error, None

    def decrypt(self,text,appid):
        """对解密后的明文进行补位删除
        @param text: 密文
        @return: 删除填充补位后的明文
        """
        try:
            cryptor = AES.new(self.key, self.mode, self.key[:16])
            # 使用 BASE64 对密文进行解码，然后 AES-CBC 解密
            plain_text = cryptor.decrypt(base64.b64decode(text))
        except Exception, e:
            return errors.WXBizMsgCrypt_DecryptAES_Error, None

        try:
            pad = ord(plain_text[-1])
            # 去掉补位字符串
            #pkcs7 = PKCS7Encoder()
            #plain_text = pkcs7.encode(plain_text)
            # 去除16位随机字符串
            content = plain_text[16:-pad]
            xml_len = socket.ntohl(struct.unpack('I', content[:4])[0])
            xml_content = content[4:xml_len + 4]
            from_appid = content[xml_len + 4:]
        except Exception, e:
            return errors.WXBizMsgCrypt_IllegalBuffer, None

        if not from_appid == appid:
            return errors.WXBizMsgCrypt_ValidateAppid_Error, None
        return 0, xml_content


class WXBizMsgCrypt(object):

    def __init__(self, token, encoding_aes_key, appid):
        """
        :param token: 公众平台上，开发者设置的Token
        :param encoding_aes_key: 公众平台上，开发者设置的EncodingAESKey
        :param appid: 企业号的AppId
        """

        try:
            self.key = base64.b64decode(encoding_aes_key + '=')
            assert len(self.key) == 32
        except:
            throw_exception('EncodingAESKey invalid.', FormatException)

        self.token = token
        self.appid = appid

    def encrypt_msg(self, reply_message, nonce, timestamp=None):
        """
        将公众号回复用户的消息加密打包
        :param reply_message: 企业号待回复用户的消息，xml 格式的字符串
        :param nonce: 随机串，可以自己生成，也可以用 URL 参数的 nonce
        :param timestamp: 时间戳，可以自己生成，也可以用 URL 参数的 timestamp, 如为 None 则自动用当前时间
        :return: 成功返回0和加密后的消息，失败返回对应的错误码及None
        """

        pc = Prpcrypt(self.key)
        ret, encrypt = pc.encrypt(reply_message, self.appid)
        if ret:
            return ret, None

        timestamp = timestamp or str(int(time.time()))

        # 生成安全签名
        ret, signature = SHA1().get_sha1(self.token, timestamp, nonce, encrypt)
        if ret:
            return ret, None

        encrypted = XMLParse().generate(encrypt, signature, timestamp, nonce)
        return 0, encrypted

    def decrypt_msg(self, post_data, signature, timestamp, nonce):
        """
        检验消息的真实性，并且获取解密后的明文
        :param post_data: 密文，对应 POS T请求的数据
        :param signature: 签名串，对应 URL 参数的 msg_signature
        :param timestamp: 时间戳，对应 URL 参数的 timestamp
        :param nonce: 随机串，对应 URL 参数的 nonce
        :return: 成功返回0和对应的明文，失败则返回错误码和 None
        """

        # 验证安全签名
        ret, encrypt, touser_name = XMLParse().extract(post_data)
        if ret:
            return ret, None

        ret, sig_from_pdata = SHA1().get_sha1(self.token, timestamp, nonce, encrypt)
        if ret:
            return ret, None
        if not sig_from_pdata == signature:
            return errors.WXBizMsgCrypt_ValidateSignature_Error, None

        return Prpcrypt(self.key).decrypt(encrypt, self.appid)
