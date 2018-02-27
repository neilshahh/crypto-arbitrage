from abc import ABCMeta, abstractmethod


class ExchangeBase:
    __metaclass__ = ABCMeta

    def get_market_rate(self):
        """
        Each function should take the rate and return in the form 
        
        {crypto: {'ask': {}, 'bid': {} } }
        :return: 
        """


    def buy_limit_order(self, price, volume):
        """
        Each function should return API response and add a 'txid' key 
         
        :param price: in Fiat currency
        :param volume: in Crypto lot size
        :return: 
        """


    def sell_limit_order(self, price, volume):
        """
        Each function should return API response and add a 'txid' key 
         
        :param price: in Fiat currency
        :param volume: in Crypto lot size
        :return: 
        """


    def trade_status(self, txid):
        """
        Each function should return API response and add a  'filled' key with value being 
        'success' if successful

        :param txid: takes it from response from 
        :return: 
        """


    def withdrawal(self, wallet_currency, amount, key):
        """
        Each function should return API response and add a 'refid' key showing the id of the withdrawal
        
        :param wallet_currency: 
        :param amount: 
        :param key: The key of the exchange you want to transfer to, found in config
        :return: 
        """


    def withdrawal_status(self, wallet_currency, ref_id):
        """
        Some exchanges do not support this and add a key 'status' with 'Success' if successful
        
        :param wallet_currency: 
        :param ref_id: 
        :return: 
        """


    def get_fees(self):
        """
        
        :return: 
        """

    def check_balance(self, account: str) -> float:
        """
        
        :param account: 
        :return: 
        """



if __name__ == "__main__":
    pass