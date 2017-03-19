import stock_loader
import pickle
import os
import time
import argparse

class StockAccount:
    def __init__(self):
        self.balance = None
        self.stocks = None

class StockAssistant:
    def __init__(self, requested_target_balance, commit_transaction, refresh_financials):
        # Load my account
        self._account = self.load_account_data(requested_target_balance)
        # Load stock data from Yahoo and Google Finance
        stock_loader.initialize(refresh_financials)
        (ticker_list, unknown_list) = stock_loader.load_historic_data(self.get_default_symbols())
        # Determine what to buy or sell
        self.determine_transactions(requested_target_balance, ticker_list, commit_transaction)

    def get_default_symbols(self):
        return list(self._account.stocks.keys())

    def determine_transactions(self, requested_target_balance, ticker_list, commit_transaction):
        ticker_list.sort(key=lambda x: x.get_name())
        buy_shares = []
        sell_shares = []
        total_holding_balance = 0
        total_action_balance = 0
        db_is_modified = False

        for ticker in ticker_list:
            price = float(ticker.get_last_price())
            name = ticker.get_name()
            percent_holding = self._account.stocks[name][0]
            holding = self._account.stocks[name][1]
            holding_balance = float("{0:.3f}".format(price*holding))
            total_holding_balance += holding_balance
            target_balance = float("{0:.3f}".format((percent_holding/100)*requested_target_balance))
            action_balance = float("{0:.3f}".format(target_balance-holding_balance))
            total_action_balance += action_balance
            action = "buy"
            action_shares = int(round(action_balance/price))
            self._account.stocks[name][1] += action_shares
            if action_balance < 0:
                action = "sell"
                action_balance = -1*action_balance
                action_shares = -1*action_shares
                if action_shares > 0:
                    sell_shares.append("{}: Sell {} shares @ ${} (old: {}, new: {})".format(name.upper(), action_shares, price, holding, self._account.stocks[name][1]))
            elif action_shares > 0:
                buy_shares.append("{}: Buy {} shares @ ${} (old: {}, new: {})".format(name.upper(), action_shares, price, holding, self._account.stocks[name][1]))
            print ("{}".format(name.upper()))
            print("> Name: {}".format(ticker.get_long_name()))
            print("> Expected: ${}".format(target_balance))
            print("> Actual: ${} (${} x {})".format(holding_balance,
                                                     price,
                                                     holding))
            print("> To {}: ${} ({} shares)".format(action, action_balance,action_shares))

        print("\n================================================")
        action_messages = buy_shares+sell_shares
        for message in action_messages:
            db_is_modified = True
            print(message)
        print("Summary")
        print("> Transactions: {}".format(len(action_messages)))
        print("> Transaction cost: ${}".format("{0:.3f}".format(total_action_balance)))
        print("> Holdings: ${}".format(total_holding_balance))
        print("> Old target: ${}".format(self._account.balance))
        print("> New target: ${}".format(requested_target_balance))
        print("================================================\n")
        # Commit transactions
        output_file = self.get_db_file()
        if (db_is_modified and commit_transaction) or not os.path.exists(output_file):
            self._account.balance = requested_target_balance
            self.write_account_data(self._account)
        else:
            print("Account database is already up-to-date")

    def get_db_file(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "401k.db")

    def write_account_data(self, account):
        output_file = self.get_db_file()
        start_time = time.time()
        fileObject = open(output_file,'wb')
        pickle.dump(account,fileObject)
        fileObject.close()
        print ("Wrote: {}".format(output_file))

    def load_account_data(self, requested_target_balance):
        start_time = time.time()
        output_file = self.get_db_file()
        account = None
        if os.path.exists(output_file):
            fileObject = open(output_file,'rb')
            account = pickle.load(fileObject)
            print ("Loaded: {}".format(output_file))
        else:
            # Default value
            print ("New account: {}".format(output_file))
            account = StockAccount()
            account.balance = requested_target_balance
            account.stocks = {  'itot' : [14.6, 27],
                'ive'  : [14.6, 14],
                'ijj'  : [4.7, 3],
                'ijs'  : [4.1, 3],
                'frel' : [1.5, 6],
                'feny' : [1.5, 7],
                'iefa' : [30.8, 55],
                'iemg' : [8.3, 18],
                'agg'  : [6.6, 6],
                'lqd'  : [3.4, 3],
                'iagg' : [7.0, 14],
                'emb'  : [3.0, 3], }
        return account

def process_options():
    parser = argparse.ArgumentParser(description='Analyze ticker_symbol prices.')
    parser.add_argument('--target_balance', metavar='BALANCE', help='Target BALANCE to keep in stocks and bonds', default=10000)
    parser.add_argument('--commit', action="store_true", help='Commit the transaction (buy/sell stocks and bonds)')
    parser.add_argument('--refresh', action="store_true", help='Refresh stock data)')
    args = parser.parse_args()
    return args

def main():
    start_time = time.time()
    args = process_options()
    StockAssistant(int(args.target_balance), args.commit, args.refresh)
    print ("Total elapsed time: {}".format(time.time()-start_time))

if __name__ == '__main__':
    main()
