import requests

class Gemini:
    def __init__(self, fiat, crypto):
        self.url = 'https://api.gemini.com/v1/'
        self.fiat = fiat
        self.crypto = crypto
        self.rate = crypto.lower() + fiat.lower()
        self.deposit = 0.00  # EUR
        self.fiat_withdrawal = 0.09  # EUR
        self.withdrawal_map = {'BTC': 0.001,
                               'ETH': 0.005,
                               'XRP': 0.02,
                               'XLM': 0.00002,
                               'LTC': 0.02}

    def get_market_rate(self):
        market_rate = requests.get(self.url + "pubticker/" + self.rate ).json()
        self.normalised_rates = {self.crypto: {'ask':{}, 'bid':{}}}
        self.normalised_rates[self.crypto]['ask'] = float(market_rate['ask'])
        self.normalised_rates[self.crypto]['bid'] = float(market_rate['bid'])

        return self.normalised_rates

    def get_fees(self):
        """

        :return: 
        """
        return {'deposit': self.deposit, 'fiat_withdrawal': self.fiat_withdrawal, 'crypto_withdrawal': self.withdrawal_map[self.crypto]}

if __name__ == '__main__':
    print(Gemini('GBP', 'ETH').get_fees())