import stock_loader
import pickle
import os
import time
import argparse

STOCKS = {  'itot' : [14.6, 27],
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

def get_default_symbols():
    global STOCKS
    return list(STOCKS.keys())

def process_options():
    parser = argparse.ArgumentParser(description='Analyze ticker_symbol prices.')
    parser.add_argument('--balance', metavar='BALANCE', help='BALANCE to keep in stocks and bonds', default=10000)
    args = parser.parse_args()
    return args

def what_to_buy(total_target_balance, ticker_list):
    ticker_list.sort(key=lambda x: x.get_name())
    buy_shares = []
    sell_shares = []
    total_holding_balance = 0
    total_action_balance = 0
    for ticker in ticker_list:
        #stock_loader.print_ticker_info(ticker)
        price = float(ticker.get_last_price())
        name = ticker.get_name()
        percent_holding = STOCKS[name][0]
        holding = STOCKS[name][1]
        holding_balance = float("{0:.3f}".format(price*holding))
        total_holding_balance += holding_balance
        target_balance = float("{0:.3f}".format((percent_holding/100)*total_target_balance))
        action_balance = float("{0:.3f}".format(target_balance-holding_balance))
        total_action_balance += action_balance
        action = "buy"
        action_shares = int(round(action_balance/price))
        if action_balance < 0:
            action = "sell"
            action_balance = -1*action_balance
            action_shares = -1*action_shares
            if action_shares > 0:
                sell_shares.append("{}: Sell {} shares @ ${}".format(name.upper(), action_shares, price))
        elif action_shares > 0:
            buy_shares.append("{}: Buy {} shares @ ${}".format(name.upper(), action_shares, price))
        print("{}".format(name.upper()))
        print("> Expected: ${}".format(target_balance))
        print("> Actual: ${} (${} x {})".format(holding_balance,
                                                 price,
                                                 holding))
        print("> To {}: ${} ({} shares)".format(action, action_balance,action_shares))
    print("\n================================================")
    action_messages = buy_shares+sell_shares
    for message in action_messages:
        print(message)
    print("Summary")
    print("> Transactions: {}".format(len(action_messages)))
    print("> Transaction cost: ${}".format("{0:.3f}".format(total_action_balance)))
    print("> Holdings: ${}".format(total_holding_balance))
    print("> Target: ${}".format(total_target_balance))
    print("================================================\n")

def get_db_file():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "401k.db")

def write_last_purchase_data():
    start_time = time.time()
    output_file = get_db_file()
    fileObject = open(output_file,'wb')
    pickle.dump(STOCKS,fileObject)
    fileObject.close()
    print ("Wrote: {}".format(output_file))

def load_last_purchase_data():
    start_time = time.time()
    output_file = get_db_file()
    if os.path.exists(output_file):
        fileObject = open(output_file,'rb')
        STOCKS = pickle.load(fileObject) 
        print ("Loaded: {}".format(output_file))

def main():
    start_time = time.time()
    stock_loader.initialize()
    load_last_purchase_data()
    args = process_options()
    (ticker_list, unknown_list) = stock_loader.load_historic_data(get_default_symbols())
    what_to_buy(int(args.balance), ticker_list)
    write_last_purchase_data()
    print ("Total elapsed time: {}".format(time.time()-start_time))

if __name__ == '__main__':
    main()
