import requests
import coinbase

import json, hmac, hashlib, time, requests, base64
from requests.auth import AuthBase
from utils import load_config
from datetime import datetime, timedelta


class Coinbase:
    def __init__(self, fiat, crypto):
        self.fiat = fiat
        self.crypto = crypto
        self.rate = crypto + '-' + fiat
        self.deposit = 0.00  # EUR
        self.fiat_withdrawal = 0.09  # EUR
        self.withdrawal_map = {'BTC': 0.001,
                               'ETH': 0.005,
                               'XRP': 0.02,
                               'XLM': 0.00002,
                               'LTC': 0.02}
        self.api_key = load_config('config.yml')['coinbase']['api_key']
        self.secret_key = load_config('config.yml')['coinbase']['api_secret']
        self.passphrase = load_config('config.yml')['coinbase']['passphrase']

    def get_market_rate(self):
        market_rate = requests.get(self.url + 'products/' + self.rate + '/book', params={'level': '1'}).json()
        self.normalised_rates = {self.crypto: {'ask': {}, 'bid': {}}}
        self.normalised_rates[self.crypto]['ask'] = float(market_rate['asks'][0][0])
        self.normalised_rates[self.crypto]['bid'] = float(market_rate['bids'][0][0])

        return self.normalised_rates

    def buy_limit_order(self, price=0, volume=0):
        """default is limit order"""
        auth = CoinbaseExchangeAuth(self.api_key, self.secret_key, self.passphrase)
        data = {
            "size": volume,
            "price": price,
            "side": "buy",
            "product_id": self.rate,
            "type":"limit:",
            "time_in_force":'GTT',
            "cancel_after": (datetime.now() + timedelta(minutes=10)).strftime('%M, %H, %d')
        }

        buy = requests.post(self.url + 'orders',
                            data=data,
                            auth=auth)
        return buy.json()

    def sell_limit_order(self, price=0, volume=0):
        """default is limit order"""
        auth = CoinbaseExchangeAuth(self.api_key, self.secret_key, self.passphrase)
        data = {
            "size": volume,
            "price": price,
            "side": "sell",
            "product_id": self.rate,
            "type":"limit:"
        }

        buy = requests.post(self.url + 'orders',
                            data=data,
                            auth=auth)

        buy['id'] = buy['txid']

        return buy.json()

    def trade_status(self, txid):
        auth = CoinbaseExchangeAuth(self.api_key, self.secret_key, self.passphrase)
        response = requests.get(self.url + 'orders/' + txid,
                                auth=auth)
        return response


    def test(self):
        auth = CoinbaseExchangeAuth(self.api_key, self.secret_key, self.passphrase)
        hi = requests.get(self.url + 'accounts', auth=auth)
        print(hi.content)


class CoinbaseExchangeAuth(AuthBase):
    def __init__(self, api_key, secret_key, passphrase):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

    def __call__(self, request):
        timestamp = str(time.time())
        message = timestamp + request.method + request.path_url + (request.body or '')
        hmac_key = base64.b64decode(self.secret_key)
        signature = hmac.new(hmac_key, message.encode('ascii'), hashlib.sha256)
        signature_b64 = base64.b64encode(signature.digest())

        request.headers.update({
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        })
        return request

    def get_fees(self):
        """

        :return: 
        """
        return {'deposit': self.deposit, 'fiat_withdrawal': self.fiat_withdrawal, 'crypto_withdrawal': self.withdrawal_map[self.crypto]}


if __name__ == "__main__":
    Gdax('EUR', 'ETH',
         api_key='143e07f64176094c5e1d358e2a7565dd',
         secret_key='AJQJqHriLj5fthKSXh5fsQtFnBEcEb21gqYvvNCUpvNz5ylYLiERdhBOQXrON+F5nLP2noM7TVZ1IMWBpA1o2A==',
         passphrase='bq5yle3zzxp').test()
