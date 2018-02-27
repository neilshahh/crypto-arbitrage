import time
import logging
from kraken import Kraken
from gdax import Gdax
from gemini import Gemini
from bitstamp import Bitstamp
from utils import load_config


class ArbScheme:
    def __init__(self, fiat, cryptos):
        self.cryptos = cryptos
        self.fiat = fiat
        self.arb = {"profit": 0}
        # self.arb = {'profit': 1.6151999999999804, 'buy': 'kraken', 'buy_price': 206.96, 'sell': 'gdax', 'sell_price': 209.7, 'crypto': 'LTC', 'fiat': 'EUR'}
        self.apis = {
            # 'bitstamp': Bitstamp,
            # 'gemini': Gemini,
            'kraken': Kraken,
            'gdax': Gdax}
        self.volume = {'BTC': 0.003,
                       'LTC': 0.3,
                       'ETH': 0.06}
        self.allowed_profit = 0.7

    def _calculate_profit(self, crypto, exchange_ask, ask_price, exchange_bid, bid_price):
        logging.debug('Calculating Profit...')
        info = {}
        fees_ask = self.apis[exchange_ask](self.fiat, crypto).get_fees() #buy exchange
        fees_bid = self.apis[exchange_bid](self.fiat, crypto).get_fees()
        buy_volume = self.volume[crypto]
        sell_volume = buy_volume - fees_ask['crypto_withdrawal']

        sell_value = bid_price * sell_volume
        buy_value  = ask_price * buy_volume
        fixed_fees = fees_ask['deposit'] - fees_bid['fiat_withdrawal']
        profit = ((sell_value - buy_value) + fixed_fees)
        percentage_profit =  profit * 100 / buy_value

        info['percentage_profit'] = percentage_profit
        info['deposit'] = fees_ask['deposit']
        info['crypto_withdrawal'] = fees_ask['crypto_withdrawal']
        info['fiat_withdrawal'] = fees_bid['fiat_withdrawal']

        logging.debug('POSITIVE PROFIT CALCULATED' if percentage_profit > 0 else 'NEGATIVE PROFIT CALCULATED')
        logging.debug('{}: [sell on] {:>8} - [buy on] {:>8} \t {:>8} - {:>8} \t *** PROFIT (after fees)  : {} ***'.format(crypto, exchange_bid, exchange_ask, bid_price, ask_price, percentage_profit))
        logging.debug('((((bids({}) * (volume({}) - crypto_withdrawal({}))) - (asks({}) * volume({}))) - deposit({}) - fiat_withdrawal({})) / (asks({}) * volume ({})) '
                      '* 100'.format(bid_price, buy_volume, fees_ask['crypto_withdrawal'], ask_price, buy_volume, fees_ask['deposit'],fees_bid['fiat_withdrawal'], ask_price, buy_volume))
        logging.debug('(((sell_value({}) - buy_value({})) - deposit({}) - fiat_withdrawal({})) / buy_value({})) * 100'.format(sell_value, buy_value,fees_ask['deposit'],fees_bid['fiat_withdrawal'],buy_value))

        return info

    def get_rates(self, crypto):
        """gets rates from exchanges and returns dictionary"""

        normalised_rates = {crypto: {'ask': {}, 'bid': {}}}

        for exchange, api in self.apis.items():
            rates = api(crypto=crypto, fiat=self.fiat).get_market_rate()
            normalised_rates[crypto]['ask'][exchange] = rates[crypto]['ask']
            normalised_rates[crypto]['bid'][exchange] = rates[crypto]['bid']

        logging.debug(normalised_rates)
        return normalised_rates

    def calculate_arb(self, crypto):
        rates = self.get_rates(crypto)
        for exa, asks in rates[crypto]['ask'].items():  # ask prices on different exchanges
            for exb, bids in rates[crypto]['bid'].items():  # bid prices on different exchanges
                logging.debug('Looping through - buy: ask {} {}, sell: bid {} {}'.format(exa, asks, exb, bids))
                profit_info = self._calculate_profit(crypto, exa, asks, exb, bids)
                if profit_info['percentage_profit'] > self.arb["profit"]:
                    self.arb["buy"] = exa
                    self.arb["buy_price"] = asks
                    self.arb["sell"] = exb
                    self.arb["sell_price"] = bids
                    self.arb["crypto"] = crypto
                    self.arb["fiat"] = self.fiat
                    self.arb["profit"] = profit_info['percentage_profit']  # 0.75% fees from topup, transfer and withdrawal
                    self.arb["deposit"] = profit_info['deposit']
                    self.arb["crypto_withdrawal"] = profit_info['crypto_withdrawal']
                    self.arb["fiat_withdrawal"] = profit_info['fiat_withdrawal']

        logging.debug(self.arb)

    def check_and_withdraw(self, buy, buy_exchange):
        """
        rule is if withdrawing on kraken then (sell exchange) -> kraken_LTC
        if not withdrawing on kraken then (sell exchange) -> crypto
        :param buy: 
        :param buy_exchange: 
        :return: 
        """
        # withdraw only once the buy is complete
        while True:
            buy_status = buy_exchange.trade_status(txid=buy['txid'])
            if buy_status['filled'] == 'success':
                key = self.arb["sell"]
                sub_key = 'kraken_' + self.arb["crypto"] if self.arb['buy'] == 'kraken' else self.arb["crypto"]  # The key loads the key to send to. However its different for kraken
                withdrawal = buy_exchange.withdrawal(wallet_currency=self.arb["crypto"],
                                                     amount=buy_status['amount'],
                                                     key=load_config('config.yml')[key][sub_key])
                return withdrawal
            time.sleep(20)

    def sell_and_check(self, sell_exchange, withdrawal_status):
        # no way to detect whether funds have reached exchange so just going to keep on checking for funds.
        # todo find a way round if exchange doesnt support withdrawal status
        count = 0
        while True:
            check_balance = sell_exchange.check_balance(account=self.arb["crypto"])
            if float(check_balance) >= float(withdrawal_status['amount']):
                logging.debug('balance: {}, withdrawal amount {}'.format(float(check_balance), float(withdrawal_status['amount'])))

                updated_rate = self.get_rates(self.arb["crypto"])[self.arb["crypto"]]["bid"][self.arb["sell"]]
                price_difference_from_time = abs((updated_rate - self.arb["sell_price"]) / self.arb["sell_price"])*100
                logging.debug('The price difference since arb calculation and now is: {}%'.format(price_difference_from_time))
                price_filter = True if price_difference_from_time < (self.arb["profit"] / 2) else False

                recalculate_profit = self._calculate_profit(crypto=self.arb["crypto"],
                                                            exchange_ask=self.arb["buy"],
                                                            exchange_bid=self.arb["sell"],
                                                            ask_price=self.arb['buy_price'],
                                                            bid_price=updated_rate)["percentage_profit"]

                logging.debug('recalculated profit: {}'.format(recalculate_profit))
                self.arb['new_profit'] = recalculate_profit

                if price_filter:
                    sell = sell_exchange.sell_limit_order(price=updated_rate, volume=withdrawal_status['amount'])
                    break
            count += 1
            logging.debug('count: {}'.format(count))
            time.sleep(60)

        while True:
            sell_status = sell_exchange.trade_status(txid=sell['txid'])
            if sell_status['filled'] == 'success':
                logging.debug('Complete')
                return "Complete"
            time.sleep(60)

    def execute_arb(self):
        # todo: python enviroment to test and for prod
        # todo: logging
        # todo: if the loop takes more than 10 mins cancel the order
        # todo: withdraw_status = buy_exchange.withdraw_status(txid=withdraw['txid'])
        # todo: pushnotify - pushover
        # todo: database to store transactions
        # todo: change api classes for __init__ to not take in crypto and fiat. doesnt make sense
        # todo: profit calculation to take into account taker fees or refactor to make traders makers
        # todo: split apis into authenticated and non authenticated
        # todo: if script fails it should be able to restart at its last point

        while True:
            for crypto in self.cryptos:
                self.calculate_arb(crypto)
            if self.arb['profit'] > self.allowed_profit:
                break
            else:
                self.arb["profit"] = 0
                logging.debug('No arb opportunity found. trying again... ')
                time.sleep(15)

        buy_exchange = self.apis[self.arb['buy']](crypto=self.arb['crypto'], fiat=self.arb['fiat'])
        sell_exchange = self.apis[self.arb['sell']](crypto=self.arb['crypto'], fiat=self.arb['fiat'])

        volume = self.volume[self.arb["crypto"]]

        balance_before_buy = buy_exchange.check_balance(account=self.arb["fiat"])

        buy = buy_exchange.buy_limit_order(volume=volume,
                                           price=self.arb["buy_price"])

        # withdraws only once the buy is complete
        withdrawal = self.check_and_withdraw(buy=buy,
                                             buy_exchange=buy_exchange)


        withdrawal_status = buy_exchange.withdrawal_status(wallet_currency=self.arb["crypto"],
                                                           ref_id=withdrawal['refid']) if self.arb['sell'] == 'gdax' else withdrawal

        balance_after_buy = buy_exchange.check_balance(account=self.arb["fiat"])
        balance_before_sell = sell_exchange.check_balance(account=self.arb["fiat"])

        # no way to detect whether funds have reached so just going to keep on checking for funds.
        sell = self.sell_and_check(sell_exchange=sell_exchange,
                                   withdrawal_status=withdrawal_status)

        balance_after_sell = sell_exchange.check_balance(account=self.arb["fiat"])

        amount_before = float(balance_before_buy) - float(balance_after_buy)
        amount_after = float(balance_after_sell) - float(balance_before_sell)

        logging.debug('Profit before withdrawing fiat: {} {}'.format(amount_after-amount_before, self.arb["fiat"]))
        logging.debug('Arb Complete')


if __name__ == "__main__":
    formatter = '[%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s'
    logging.basicConfig(filename="arb.log", level=logging.DEBUG, format=formatter)
    stderrLogger = logging.StreamHandler()
    stderrLogger.setFormatter(logging.Formatter(formatter))
    logging.getLogger().addHandler(stderrLogger)

    try:
        ArbScheme('EUR', ['LTC']).execute_arb()
    except Exception as e:
        logging.exception(e)

