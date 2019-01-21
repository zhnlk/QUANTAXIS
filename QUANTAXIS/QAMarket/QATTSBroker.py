# coding:utf-8


import requests
import json
import urllib
import base64
import pandas as pd
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from QUANTAXIS.QAMarket.QABroker import QA_Broker
from QUANTAXIS.QAUtil.QAParameter import ORDER_DIRECTION, MARKET_TYPE, ORDER_MODEL, TRADE_STATUS


class QA_TTSBroker(QA_Broker):
    def __init__(self, endpoint="http://127.0.0.1:10092/api", encoding="utf-8", enc_key=None, enc_iv=None):

        self._endpoint = endpoint
        self._encoding = "utf-8"
        if enc_key == None or enc_iv == None:
            self._transport_enc = False
            self._transport_enc_key = None
            self._transport_enc_iv = None
            self._cipher = None
        else:
            self._transport_enc = True
            self._transport_enc_key = enc_key
            self._transport_enc_iv = enc_iv
            backend = default_backend()
            self._cipher = Cipher(algorithms.AES(
                enc_key), modes.CBC(enc_iv), backend=backend)

        self._session = requests.Session()
        self.client_id = 0
        self.gddm = 0

    def call(self, func, params=None):

        json_obj = {
            "func": func
        }

        if params is not None:
            json_obj["params"] = params

        if self._transport_enc:
            data_to_send = self.encrypt(json_obj)
            response = self._session.post(self._endpoint, data=data_to_send)
        else:
            response = self._session.post(self._endpoint, json=json_obj)
        response.encoding = self._encoding
        text = response.text

        if self._transport_enc:
            decoded_text = self.decrypt(text)
            print(decoded_text)
            return json.loads(decoded_text)
        else:
            return json.loads(text)

    def encrypt(self, source_obj):
        encrypter = self._cipher.encryptor()
        source = json.dumps(source_obj)
        source = source.encode(self._encoding)
        need_to_padding = 16 - (len(source) % 16)
        if need_to_padding > 0:
            source = source + b'\x00' * need_to_padding
        enc_data = encrypter.update(source) + encrypter.finalize()
        b64_enc_data = base64.encodebytes(enc_data)
        return urllib.parse.quote(b64_enc_data)

    def decrypt(self, source):
        decrypter = self._cipher.decryptor()
        source = urllib.parse.unquote(source)
        source = base64.decodebytes(source.encode("utf-8"))
        data_bytes = decrypter.update(source) + decrypter.finalize()
        return data_bytes.rstrip(b"\x00").decode(self._encoding)

    def data_to_df(self, result):
        if 'data' in result:
            data = result['data']
            return pd.DataFrame(data=data)

    #------ functions

    def ping(self):

        return self.call("ping", {})

    def logon(self, ip, port, version, yyb_id, account_id, trade_account, jy_passwrod, tx_password):
        data = self.call("logon", {
            "ip": ip,
            "port": port,
            "version": version,
            "yyb_id": yyb_id,
            "account_no": account_id,
            "trade_account": trade_account,
            "jy_password": jy_passwrod,
            "tx_password": tx_password
        })
        if data['success']:
            self.client_id = data["data"]["client_id"]
            self.gddm = api.query_data(5)['data'][0]['股东代码']
            print(self.gddm)
        return data

    def logoff(self):
        return self.call("logoff", {
            "client_id": self.client_id
        })

    def query_data(self,  category):
        return self.call("query_data", {
            "client_id": self.client_id,
            "category": category
        })

    def send_order(self,  code, price, amount, towards, order_model):
        """下单

        Arguments:
            code {[type]} -- [description]
            price {[type]} -- [description]
            amount {[type]} -- [description]
            towards {[type]} -- [description]
            order_model {[type]} -- [description]

        Returns:
            [type] -- [description]
        """

        towards = 0 if towards == ORDER_DIRECTION.BUY else 1
        if order_model == ORDER_MODEL.MARKET:
            order_model = 4
        elif order_model == ORDER_MODEL.LIMIT:
            order_model = 1

        return self.call("send_order", {
            'client_id': self.client_id,
            'category': towards,
            'price_type': order_model,
            'gddm': self.gddm,
            'zqdm': code,
            'price': price,
            'quantity': amount
        })

    def cancel_order(self, exchange_id, order_id):
        """

        Arguments:
            exchange_id {[type]} -- 交易所  0 深圳 1上海 (偶尔2是深圳)
            order_id {[type]} -- [description]

        Returns:
            [type] -- [description]
        """

        return self.call("cancel_order", {
            'client_id': self.client_id,
            'exchange_id': exchange_id,
            'hth': order_id
        })

    def get_quote(self, code):
        return self.call("get_quote", {
            'client_id': self.client_id,
            'code': code,
        })

    def repay(self,  amount):
        return self.call("repay", {
            'client_id': self.client_id,
            'amount': amount
        })

    def receive_order(self, event):

        return self.send_order(event.client_id, event.category, event.price_type, event.gddm, event.zqdm, event.price, event.quantity)
        #client_id, category, price_type, gddm, zqdm, price, quantity

    def run(self, event):
        pass


if __name__ == "__main__":
    import os
    import QUANTAXIS as QA
    print('在运行前 请先运行tdxtradeserver的 exe文件, 目录是你直接get_tts指定的 一般是 C:\tdxTradeServer')
    print('这是测试代码, 下面需要输入的 key/iv在ini中自己查找, account 和password是自己的账户密码 ')
    api = QA_TTSBroker(endpoint="http://127.0.0.1:19820/api",
                       enc_key=bytes('64de4fc61d8811e9', encoding='utf-8'), enc_iv=bytes('9a8c9cb6d020b9c2', encoding='utf-8'))

    print("---Ping---")
    result = api.ping()
    print(result)

    print("---登入---")
    acc = "35202548"  # 你的账号
    password = "161410"  # 你的密码
    result = api.logon("60.191.116.36", 7708,
                       "6.44", 1,
                       acc, acc, password, "")

    if result["success"]:
        for i in (0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 14, 15):
            print("---查询信息 cate=%d--" % i)
            print(api.data_to_df(api.query_data(i)))
        print(api.send_order(code='000001', price=10, amount=100,
                             towards=QA.ORDER_DIRECTION.BUY, order_model=QA.ORDER_DIRECTION.BUY))
        print("---登出---")
        print(api.logoff(client_id))