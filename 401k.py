import time
from stock_loader import StockAssistant, StockHolding, StockAccount, process_options

def main():
    start_time = time.time()
    args = process_options()
    default_account = StockAccount()
    default_account.db_name = '401k'
    default_account.balance = 10000
    default_account.stocks = {
        'itot' : StockHolding(14.6, 27),
        'ive'  : StockHolding(14.6, 14),
        'ijj'  : StockHolding(4.7, 3),
        'ijs'  : StockHolding(4.1, 3),
        'frel' : StockHolding(1.5, 6),
        'feny' : StockHolding(1.5, 7),
        'iefa' : StockHolding(30.8, 55),
        'iemg' : StockHolding(8.3, 18),
        'agg'  : StockHolding(6.6, 6),
        'lqd'  : StockHolding(3.4, 3),
        'iagg' : StockHolding(7.0, 14),
        'emb'  : StockHolding(3.0, 3), }
    StockAssistant(default_account,
                    args.add,
                    args.target_balance,
                    args.commit,
                    args.refresh)
    print ("Total elapsed time: {}".format(time.time()-start_time))

if __name__ == '__main__':
    main()
