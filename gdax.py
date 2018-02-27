import requests
import logging

import json, hmac, hashlib, time, requests, base64
from requests.auth import AuthBase
from utils import load_config
from datetime import datetime, timedelta


class Gdax:
    def __init__(self, fiat, crypto):
        self.url = 'https://api.gdax.com/'
        # self.url = 'https://api-public.sandbox.gdax.com'
        self.fiat = fiat
        self.crypto = crypto
        self.rate = crypto + '-' + fiat
        self.deposit = 0.00  # EUR
        self.fiat_withdrawal = 0.09  # EUR
        self.withdrawal_map = {'BTC': 0.0,
                               'ETH': 0.0,
                               'XRP': 0.0,
                               'XLM': 0.0,
                               'LTC': 0.0}
        self.api_key = load_config('config.yml')['gdax']['api_key']
        self.secret_key = load_config('config.yml')['gdax']['api_secret']
        self.passphrase = load_config('config.yml')['gdax']['passphrase']

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
            "type": "limit"
            # "time_in_force": 'GTC',
            # "cancel_after": (datetime.now() + timedelta(minutes=10)).strftime('%M,%H,%d')
        }

        buy = requests.post(self.url + 'orders',
                            data=json.dumps(data),
                            auth=auth).json()
        buy['txid'] = buy['id']

        logging.debug(buy)
        return buy

    def sell_limit_order(self, price=0, volume=0):
        """default is limit order"""
        auth = CoinbaseExchangeAuth(self.api_key, self.secret_key, self.passphrase)
        data = {
            "size": volume,
            "price": price,
            "side": "sell",
            "product_id": self.rate,
            "type": "limit"
        }

        sell = requests.post(self.url + 'orders',
                             data=json.dumps(data),
                             auth=auth).json()

        sell['txid'] = sell['id']

        logging.debug(sell)
        return sell

    def trade_status(self, txid):
        auth = CoinbaseExchangeAuth(self.api_key, self.secret_key, self.passphrase)
        trade = requests.get(self.url + 'orders/' + txid,
                              auth=auth).json()

        if trade['status'] == 'done':
            trade['filled'] = 'success'
            trade['amount'] = trade['filled_size']
        else:
            trade['filled'] = trade['status']

        logging.debug(trade)
        return trade

    def check_balance(self, account):
        """
        [{'available': '0.05713447',
          'balance': '0.0571344700000000',
          'currency': 'BTC',
          'hold': '0.0000000000000000',
          'id': '2d2de0f2-a011-4645-88fc-b0a877ab8e0a',
          'profile_id': '0f1d3ee0-9e61-481e-b044-b1c28a6441be'},
         {'available': '0',
          'balance': '0.0990000000000000',
          'currency': 'LTC',
          'hold': '0.0990000000000000',
          'id': 'd22945f8-a7f3-441f-81a9-cf756793e4ff',
          'profile_id': '0f1d3ee0-9e61-481e-b044-b1c28a6441be'},...]

        :param account: 
        :return: 
        """
        auth = CoinbaseExchangeAuth(self.api_key, self.secret_key, self.passphrase)
        request = requests.get(self.url + 'accounts', auth=auth).json()

        for balance in request:
            if balance['currency'] == account:
                logging.debug('gdax {} balance: {}, payload: {}'.format(account, balance['available'], balance))
                return float(balance['available'])

    def get_fees(self):
        """

        :return: 
        """
        fees = {'deposit': self.deposit, 'fiat_withdrawal': self.fiat_withdrawal, 'crypto_withdrawal': self.withdrawal_map[self.crypto]}
        logging.debug('Gdax {} Fees: {}'.format(self.crypto, fees))
        return fees

    def withdrawal(self, wallet_currency, amount, key):
        """
        
        :param wallet_currency: 
        :param amount: 
        :param key: 
        :return: 
        """
        auth = CoinbaseExchangeAuth(self.api_key, self.secret_key, self.passphrase)
        data = {"amount": float(amount),
                "currency": wallet_currency,
                "crypto_address": key
                }
        response = requests.post(self.url + 'withdrawals/crypto', auth=auth, data=json.dumps(data)).json()
        response['refid'] = response['id']
        logging.debug(response)
        return response

    def withdrawal_status(self, wallet_currency, ref_id):
        """
        unsupported
        
        :param wallet_currency: 
        :param ref_id: 
        :return: 
        """
        pass

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


if __name__ == "__main__":
    exchange = Gdax('EUR', 'LTC')
    sell = exchange.withdrawal_status(214.19, 0.099)
    # print(sell)

    # count = 0
    # while True:
    #     buy_status = exchange.trade_status(txid=sell['txid'])
    #     if buy_status['filled'] == 'success':
    #         # grab_token = self.arb["buy" if self.arb['buy'] == 'kraken' else "sell"] # The key loads the key to send to. However its different for kraken
    #         # withdraw = buy_exchange.withdraw(wallet_currency=self.arb["crypto"],
    #         #                                  amount=buy_status['amount'],
    #         #                                  key=load_config('config.yml')[grab_token][self.arb["crypto"]])
    #         print('success')
    #         break
    #     count += 1
    #     print(count)
    #     print(buy_status)
    #     time.sleep(20)
        # api_key = '143e07f64176094c5e1d358e2a7565dd',
        # secret_key = 'AJQJqHriLj5fthKSXh5fsQtFnBEcEb21gqYvvNCUpvNz5ylYLiERdhBOQXrON+F5nLP2noM7TVZ1IMWBpA1o2A==',
        # passphrase = 'bq5yle3zzxp'
