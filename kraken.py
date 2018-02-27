import requests
import krakenex
import logging

from utils import load_config, retry_if_exception


class Kraken:
    def __init__(self, fiat, crypto):
        self.url = 'https://api.kraken.com/0/public/Ticker'
        self.fiat = fiat
        self.crypto = crypto
        self.deposit = 0.00  # EUR
        self.fiat_withdrawal = 0.09  # EUR
        self.withdrawal_map = {'BTC': 0.001,
                               'ETH': 0.005,
                               'XRP': 0.02,
                               'XLM': 0.00002,
                               'LTC': 0.00 #1
                               }
        self.kraken_rate_map = {"DASH": "DASH",
                                "EOS": "EOS",
                                "GNO": "GNO",
                                "FEE": "KFEE",
                                "USDT": "USDT",
                                "DAO": "XDAO",
                                "ETC": "XETC",
                                "ETH": "XETH",
                                "ICN": "XICN",
                                "LTC": "XLTC",
                                "MLN": "XMLN",
                                "NMC": "XNMC",
                                "REP": "XREP",
                                "BTC": "XXBT",
                                "XDG": "XXDG",
                                "XLM": "XXLM",
                                "XMR": "XXMR",
                                "XRP": "XXRP",
                                "XVN": "XXVN",
                                "ZEC": "XZEC",
                                "CAD": "ZCAD",
                                "EUR": "ZEUR",
                                "GBP": "ZGBP",
                                "JPY": "ZJPY",
                                "KRW": "ZKRW",
                                "USD": "ZUSD"}
        self.rate = self.kraken_rate_map[crypto] + self.kraken_rate_map[fiat]
        self.api_key = load_config('config.yml')['kraken']['api_key']
        self.secret_key = load_config('config.yml')['kraken']['api_secret']

    @retry_if_exception(ex=requests.HTTPError)
    def get_market_rate(self):
        market_rate = requests.get(self.url, params={'pair': [self.rate]}).json()
        logging.debug(market_rate)
        self.normalised_rates = {self.crypto: {'ask': {}, 'bid': {}}}
        self.normalised_rates[self.crypto]['ask'] = float(market_rate['result'][self.rate]['a'][0])
        self.normalised_rates[self.crypto]['bid'] = float(market_rate['result'][self.rate]['b'][0])

        return self.normalised_rates

    @retry_if_exception(ex=requests.HTTPError)
    def buy_limit_order(self, price, volume):
        """
         Minimum order size
        Augur (REP): 0.3
        Bitcoin (XBT): 0.002
        Bitcoin Cash (BCH): 0.002
        Dash (DASH): 0.03
        Dogecoin (DOGE): 3000
        EOS (EOS): 3
        Ethereum (ETH): 0.02
        Ethereum Classic (ETC): 0.3
        Gnosis (GNO): 0.03
        Iconomi (ICN): 2
        Litecoin (LTC): 0.1
        Melon (MLN): 0.1
        Monero (XMR): 0.1
        Ripple (XRP): 30
        Stellar Lumens (XLM): 300
        Zcash (ZEC): 0.03
        
        
        {'error': [], 'result': {'descr': {'order': 'buy 0.10000000 LTCEUR @ limit 206.02'}, 'txid': ['ORFFCD-2N3KA-UC2GTP']}}
        
        :param price: 
        :param volume: volume in lots
        :return: 
        """
        k = krakenex.API(key=self.api_key, secret=self.secret_key)
        response = k.query_private('AddOrder',
                                   {'pair': self.rate,
                                    'type': 'buy',
                                    'ordertype': 'limit',
                                    'price': price,
                                    'volume': volume,  # order volume in lots
                                    'expiretm': '+600'
                                    })

        if response['error'] == []:
            response['txid'] = response['result']['txid'][0]

        logging.debug(response)

        return response

    @retry_if_exception(ex=requests.HTTPError)
    def sell_limit_order(self, price, volume):

        k = krakenex.API(key=self.api_key, secret=self.secret_key)
        response = k.query_private('AddOrder',
                                   {'pair': self.rate,
                                    'type': 'sell',
                                    'ordertype': 'limit',
                                    'price': price,
                                    'volume': volume,  # order volume in lots
                                    'expiretm': '+600'
                                    })

        if response['error'] == []:
            response['txid'] = response['result']['txid'][0]

        logging.debug(response)

        return response

    @retry_if_exception(ex=requests.HTTPError)
    def trade_status(self, txid):
        k = krakenex.API(key=self.api_key, secret=self.secret_key)
        response = k.query_private('QueryOrders',
                                   {'txid': txid})

        if 'closetm' in response['result'][txid]:
            response['filled'] = 'success'
            response['amount'] = response['result'][txid]['vol_exec']

        else:  # todo stop it
            response['filled'] = response['error']

        logging.debug(response)
        return response

    @retry_if_exception(ex=requests.HTTPError)
    def withdrawal(self, wallet_currency, amount, key):
        """
        'error': [], 'result': {'refid': 'AMBPWGV-EBQELQ-HTQJ37'}}

        :param wallet_currency: 
        :param amount: 
        :param key: 
        :return: 
        """
        k = krakenex.API(key=self.api_key, secret=self.secret_key)
        response = k.query_private('Withdraw',
                                   {'asset': wallet_currency,
                                    'key': key,
                                    'amount': amount})

        logging.debug(response)
        if response['error'] == []:
            response['refid'] = response['result']['refid']
            return response
        else:
            raise requests.HTTPError

    @retry_if_exception(ex=requests.HTTPError)
    def withdrawal_status(self, wallet_currency, ref_id):
        """
         k.query_private('WithdrawStatus',{'asset': wallet_currency})
        {'error': [],
         'result': [{'aclass': 'currency',
           'amount': '0.09900000',
           'asset': 'XLTC',
           'fee': '0.00100000',
           'info': 'LTC9zP25wtBEuaQV5VHqpeEDjJG6Uqf117',
           'method': 'Litecoin',
           'refid': 'AMBPWGV-EBQELQ-HTQJ37',
           'status': 'Success',
           'time': 1514593511,
           'txid': '647451bbe96309103d0f505bd1963a484e2618a3c18a3f3ab7ca396c981e6abd'}]}
        """

        k = krakenex.API(key=self.api_key, secret=self.secret_key)
        response = k.query_private('WithdrawStatus', {'asset': wallet_currency})
        for withdrawal in response['result']:
            if withdrawal['refid'] == ref_id:
                logging.debug(withdrawal)
                return withdrawal

    def get_fees(self):
        """

        :return: 
        """
        fees = {'deposit': self.deposit, 'fiat_withdrawal': self.fiat_withdrawal, 'crypto_withdrawal': self.withdrawal_map[self.crypto]}
        logging.debug('Kraken {} Fees: {}'.format(self.crypto, fees))
        return fees

    @retry_if_exception(ex=requests.HTTPError)
    def check_balance(self, account):
        k = krakenex.API(key=self.api_key, secret=self.secret_key)
        balance = k.query_private('Balance')['result']
        newbalance = dict()
        for currency in balance:
            # remove first symbol ('Z' or 'X'), but not for GNO or DASH
            newname = currency[1:] if len(currency) == 4 and currency != "DASH" else currency
            newbalance[newname] = (balance[currency])  # type(balance[currency]) == str
        balance = newbalance
        logging.debug('kraken {} balance: {}, payload: {}'.format(account, balance[account], balance))
        return float(balance[account])

    @retry_if_exception(ex=requests.HTTPError)
    def print_balances(self):
        k = krakenex.API(key=self.api_key, secret=self.secret_key)

        from decimal import Decimal as D

        balance = k.query_private('Balance')
        orders = k.query_private('OpenOrders')

        balance = balance['result']
        orders = orders['result']

        newbalance = dict()
        for currency in balance:
            # remove first symbol ('Z' or 'X'), but not for GNO or DASH
            newname = currency[1:] if len(currency) == 4 and currency != "DASH" else currency
            newbalance[newname] = D(balance[currency])  # type(balance[currency]) == str
        balance = newbalance

        for _, o in orders['open'].items():
            # remaining volume in base currency
            volume = D(o['vol']) - D(o['vol_exec'])

            # extract for less typing
            descr = o['descr']

            # order price
            price = D(descr['price'])

            pair = descr['pair']
            base = pair[:3] if pair != "DASHEUR" else "DASH"
            quote = pair[3:] if pair != "DASHEUR" else "EUR"

            type_ = descr['type']
            if type_ == 'buy':
                # buying for quote - reduce quote balance
                balance[quote] -= volume * price
            elif type_ == 'sell':
                # selling base - reduce base balance
                balance[base] -= volume

        for k, v in balance.items():
            # convert to string for printing
            if v == D('0'):
                s = '0'
            else:
                s = str(v)
            # remove trailing zeros (remnant of being decimal)
            s = s.rstrip('0').rstrip('.') if '.' in s else s
            #
            print(k, s)


if __name__ == "__main__":
    # Kraken(fiat = 'EUR', crypto = 'LTC').buy_limit_order(price='206.02', volume='0.1')
    # Kraken(fiat = 'EUR', crypto = 'ETH').trade_status(txid='ORFFCD-2N3KA-UC2GTP')
    # Kraken(fiat = 'EUR', crypto = 'ETH'). withdrawal(wallet_currency='LTC', amount='0.1', key=load_config('config.yml')['gdax']['LTC'])
    Kraken(fiat='EUR', crypto='ETH').check_balance('ETH')
