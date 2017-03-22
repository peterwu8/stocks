import time
from stock_loader import StockAssistant, StockHolding, StockAccount, process_options

def main():
    start_time = time.time()
    args = process_options()
    default_account = StockAccount()
    default_account.db_name = 'wealthfront'
    default_account.balance = 632.26
    default_account.stocks = {
        'SCHB'  : StockHolding(18, 1),
        'SCHF'  : StockHolding(13, 2),
        'VWO'  : StockHolding(9, 1),
        'SCHD' : StockHolding(15, 3),
        'SCHH' : StockHolding(8, 1),
        'LQD' : StockHolding(28, 2),
        'PCY' : StockHolding(9, 2), }
    StockAssistant(default_account,
                    args.add,
                    args.target_balance,
                    args.commit,
                    args.refresh)
    print ("Total elapsed time: {}".format(time.time()-start_time))

if __name__ == '__main__':
    main()
