import requests
import logging

class Bitstamp:
    def __init__(self, fiat, crypto):
        self.url = 'https://www.bitstamp.net/api/v2/ticker/'
        self.fiat = fiat
        self.crypto = crypto
        self.rate = crypto.lower() + fiat.lower()
        self.deposit = 0.00  # EUR
        self.fiat_withdrawal = 0.09  # EUR
        self.withdrawal_map = {'BTC': 0.0,
                               'ETH': 0.0,
                               'XRP': 0.0,
                               'XLM': 0.0,
                               'LTC': 0.0}

    def get_market_rate(self):
        market_rate = requests.get(self.url + self.rate + '/').json()
        self.normalised_rates = {self.crypto: {'ask':{}, 'bid':{}}}
        self.normalised_rates[self.crypto]['ask'] = float(market_rate['ask'])
        self.normalised_rates[self.crypto]['bid'] = float(market_rate['bid'])

        return self.normalised_rates

    def get_fees(self):
        """
        
        :return: 
        """
        fees = {'deposit':  self.deposit, 'fiat_withdrawal': self.fiat_withdrawal, 'crypto_withdrawal' : self.withdrawal_map[self.crypto] }
        logging.debug('Bitstamp {} Fees: {}'.format(self.crypto, fees))
        return fees