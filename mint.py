import json
import re
from queue import Queue
from threading import Thread, Lock
import os
import sys
import urllib.request, urllib.parse, urllib.error
import time
import argparse
from yahoo_finance import Share
from rtstock.stock import Stock
from pprint import pprint
from datetime import datetime, timedelta
from functools import reduce
import csv
from multiprocessing import Pool
import googlefinance 

mutex = Lock()
total_stocks_count = 0

############## UTILITY FUNCTIONS ##############
def get_ratio(now, base):
    return (float(now)-float(base))/float(base)

def get_ratio_percent(now, base):
    return "{0:.2f}%".format(get_ratio(now, base) * 100)

def get_today():
    return datetime.today().strftime("%Y-%m-%d")

def modification_date(filename):
    t = os.path.getmtime(filename)
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d")

def get_output_folder():
    return os.path.join("D:\\", 'data', 'stocks', 'db')

def initialize():
    directory = get_output_folder()
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_historical_data_csv_file(ticker_symbol):
    return os.path.join(get_output_folder(), ticker_symbol + ".csv")

def make_url(ticker_symbol):
    base_url = "http://ichart.finance.yahoo.com/table.csv?s="
    return base_url + ticker_symbol

class HistoricCsvFile:
    '''
    API for a set of historic data points in CSV file format
    '''
    def __init__(self, ticker_symbol):
        self._data_set = []
        self._headers = []
        with open(get_historical_data_csv_file(ticker_symbol), mode='r') as infile:
            reader = csv.reader(infile)
            for row in reader:
                if self._headers:
                    mydict = dict()
                    row_size = len(row)
                    for col_index in range(len(self._headers)):
                        if col_index < row_size:
                            mydict[self._headers[col_index]] = row[col_index]
                    self._data_set.append(mydict)
                else:
                    for column in row:
                        self._headers.append(column.replace(" ", "_"))
        self._data_set.reverse() # sort from oldest to newest

    def get_historical(self, start_date):
        """
        @brief Get Yahoo Finance Stock historical price range.
        @param start_date (must be earlier than end_date): string date in format '2009-09-26'
        @param end_date (must be later than start_date): string date in format '2016-09-26'.
                        None means end_date is today.
        @return: list of data sorted from earliest to latest historical data

        Keys are:
            Date
            Open
            High
            Low
            Close
            Volume
            Adj_Close
        """
        start_i = start_date.split('-')
        data_subset = []
        include_me = False
        for data in self._data_set:
            if include_me:
                data_subset.append(data)
            else:
                curr_i = data['Date'].split('-')
                if start_i[0] <= curr_i[0] and start_i[1] <= curr_i[1] and start_i[2] <= curr_i[2]:
                    include_me = True
                    data_subset.append(data)
        return data_subset

class HistoricDataPoint:
    '''
    API for a particular historic data point
    '''
    def __init__(self, data):
        self._data = data

    def get_date(self):
        return self._data['Date']

    def get_closing_price(self):
        return float(self._data['Adj_Close'])

    def get_price_swing_ratio(self):
        return get_ratio(self._data['High'], self._data['Low'])

class HistoricDataSetView:
    '''
    API for a subset of historic data points
    '''
    def __init__(self, yahoo, csv_data, days_to_subtract):
        self._yahoo = yahoo
        self._days_to_subtract = days_to_subtract
        self._data_set = [HistoricDataPoint(data) for data in csv_data.get_historical(self._get_today_minus_days(self._days_to_subtract))]
        if not self._data_set:
            print (" > {}:     Data is missing for {}!".format(self._get_stats_title(), self._get_today_minus_days(self._days_to_subtract)))

    def _get_today_minus_days(self, total_days_to_subtract):
        d = datetime.today() - timedelta(days=total_days_to_subtract)
        return d.strftime("%Y-%m-%d")

    def _get_ith_day_closing_price(self, ith_day):
        '''Zero-based index from oldest to newest date'''
        return self._data_set[ith_day].get_closing_price()

    def _get_price_swing_ratio(self):
        min = None
        max = None
        sum = 0
        for ps in [x.get_price_swing_ratio() for x in self._data_set]:
            sum += ps
            if not min or ps < min:
                min = ps
            if not max or ps > max:
                max = ps
        return ["{0:.2f}%".format(min*100), "{0:.2f}%".format(max*100), "{0:.2f}%".format(100*(sum / len(self._data_set)))]

    def _get_moving_average(self):
        sum = reduce(lambda x, y: x + y, [x.get_closing_price() for x in self._data_set])
        return sum / len(self._data_set)

    def _get_stats_title(self):
        count = self._days_to_subtract
        measure = "day"
        if count >= 365:
            count = int(count / 365)
            measure = "year"
        elif count >= 90:
            count = count / 30
            count = "{0:.0f}".format(count)
            measure = "mon"
        return "{} {}".format(count, measure)

    def print_stats(self, moving_average=None, percent_change_moving_average=None):
        if not self._data_set:
            return
        if not moving_average:
            moving_average = self._get_moving_average()
        if not percent_change_moving_average:
            percent_change_moving_average = get_ratio_percent(self._yahoo.get_price(), moving_average)
        price_swing = self._get_price_swing_ratio()
        print (" > {}:     {} @ {} ({}: {} @ {}, Day fluct: min[{}] max[{}] avg[{}])".format(
                                                                self._get_stats_title(),
                                                                percent_change_moving_average,
                                                                "${0:.2f}".format(float(moving_average)),
                                                                self._data_set[0].get_date(),
                                                                get_ratio_percent(self._yahoo.get_price(), self._data_set[0].get_closing_price()),
                                                                "${0:.2f}".format(self._data_set[0].get_closing_price()),
                                                                price_swing[0], price_swing[1], price_swing[2]))

class TickerData:
    def __init__(self, ticker_symbol):
        self._name = ticker_symbol
        self._yahoo = Share(ticker_symbol)
        self._csv_data = HistoricCsvFile(ticker_symbol)

    def get_name(self):
        return self._name

    def get_yahoo(self):
        return self._yahoo

    def get_csv_data(self):
        return self._csv_data

def print_ticker_info(ticker):
    ticker_symbol = ticker.get_name()
    yahoo = ticker.get_yahoo()
    csv_data = ticker.get_csv_data()
    if not yahoo.get_name():
        print ("Error: {} is not a valid stock name".format(ticker_symbol))
        return False
    print ("Ticker: {} ({})".format(ticker_symbol.upper(), yahoo.get_name()))
    print (" > Last price: ${}".format(yahoo.get_price()))
    print (" > Last trade: {}".format(yahoo.get_trade_datetime()))
    print (" > Open:       {} @ {} / ${}".format(yahoo.get_percent_change(), yahoo.get_change(), yahoo.get_open()))
    HistoricDataSetView(yahoo, csv_data, 50).print_stats(yahoo.get_50day_moving_avg(),
                                                         yahoo.get_percent_change_from_50_day_moving_average())
    HistoricDataSetView(yahoo, csv_data, 200).print_stats(yahoo.get_200day_moving_avg(),
                                                          yahoo.get_percent_change_from_200_day_moving_average())
    HistoricDataSetView(yahoo, csv_data, 365).print_stats()
    HistoricDataSetView(yahoo, csv_data, 5*365).print_stats()
    print (" > Year high:  {} @ ${}".format(yahoo.get_percent_change_from_year_high(), yahoo.get_year_high()))
    print (" > Year low:   {} @ ${}".format(yahoo.get_percent_change_from_year_low(), yahoo.get_year_low()))
    if yahoo.get_short_ratio():
        print (" > Short:       {} @ {}".format(yahoo.get_short_ratio(), get_ratio_percent(yahoo.get_volume(), yahoo.get_avg_daily_volume()) if yahoo.get_volume() and yahoo.get_avg_daily_volume() else 'Missing volume'))
        print (" > P/E:         {} @ (Growth: {}, Earning: {})".format(yahoo.get_price_earnings_ratio(), yahoo.get_price_earnings_growth_ratio(), yahoo.get_earnings_share()))

    # ========= Old stuff ========= #
    # realtime = Stock(ticker_symbol)
    # print (realtime.get_latest_price())
    return True

def get_default_symbols():
    return ['itot',
            'ive',
            'ijj',
            'ijs',
            'frel',
            'feny',
            'iefa',
            'iemg',
            'agg',
            'lqd',
            'iagg',
            'emb',
            'AAPL', 'GOOGL', 'AMZN', 'BRK-B', 'FDC', 'MSFT', 'TWTR', 'TSLA', 'GLOB']

def process_options():
    parser = argparse.ArgumentParser(description='Analyze stock prices.')
    parser.add_argument('ticker_symbols', metavar='TICKER_SYMBOL', nargs='*', help='NAME of the stock ticker symbol')
    parser.add_argument('--file', metavar='FILE_NAME', help='FILE_NAME listing stock ticker symbols')
    args = parser.parse_args()
    return args

def read_stock_list_file(file_name):
    '''White line delimited list of stock symbols'''
    with open(file_name, mode='r') as infile:
        return [re.sub('[^0-9a-zA-Z]+', '-', row[0].strip()) for row in csv.reader(infile)]
    return []

def get_symbols():
    args = process_options()
    ticker_symbols = args.ticker_symbols
    if not ticker_symbols and args.file:
        ticker_symbols = read_stock_list_file(args.file)
    if not ticker_symbols:
        ticker_symbols = get_default_symbols()
    return ticker_symbols

def split_into_sublists(seq, num):
    avg = len(seq) / float(num)
    out = []
    last = 0.0
    while last < len(seq):
        sublist = seq[int(last):int(last + avg)]
        if sublist:
            out.append(sublist)
        last += avg
    return out

def load_historic_data_for_subset(thread_id, ticker_symbols, ticker_queue, unknown_queue):
    global total_stocks_count
    for ticker_symbol_sublist in split_into_sublists(ticker_symbols, 150):
        tickers = []
        for ticker_symbol in ticker_symbol_sublist:
            output_file = get_historical_data_csv_file(ticker_symbol)
            is_okay = True
            if not os.path.exists(output_file) or modification_date(output_file) != get_today():
                try:
                    urllib.request.urlretrieve(make_url(ticker_symbol), output_file)
                except urllib.error.ContentTooShortError as e:
                    outfile = open(output_file, "w")
                    outfile.write(e.content)
                    outfile.close()
                except:
                    print ("ERROR: No Yahoo data for {}".format(ticker_symbol))
                    unknown_queue.put(ticker_symbol)
                    is_okay = False
                if is_okay:
                    print ("({}) Updated {}".format(thread_id, output_file))
            # Add ticker in the queue
            if is_okay:
                #TODO: ticker_queue.put(TickerData(ticker_symbol))
                #      causes a MemoryError
                tickers.append(TickerData(ticker_symbol))
        mutex.acquire()
        for ticker in tickers:
            total_stocks_count += 1
            print_ticker_info(ticker)
        mutex.release()

def convert_to_list(myqueue):
    mylist = []
    while not myqueue.empty():
        mylist.append(myqueue.get(False))
    return mylist

def load_historic_data(ticker_symbols):
    global total_stocks_count
    start_time = time.time()
    mythreads = []
    thread_id = 0
    ticker_queue = Queue()
    unknown_queue = Queue()
    num_threads = 200
    print ("Loading historic data with {} threads...".format(num_threads))
    for ticker_symbol_sublist in split_into_sublists(ticker_symbols, num_threads):
        t = Thread(target=load_historic_data_for_subset, args=(thread_id, ticker_symbol_sublist, ticker_queue, unknown_queue, ))
        t.start()
        mythreads.append(t)
        thread_id += 1
    for t in mythreads:
        t.join()
    print ("CSV load time ({} stocks, {} threads): {}".format(total_stocks_count, thread_id, time.time()-start_time))
    return (convert_to_list(ticker_queue), convert_to_list(unknown_queue))

def google_analysis(stock_list):
    start_time = time.time()
    print (json.dumps(googlefinance.getQuotes(stock_list), indent=2))
    print ("Google finance analyzed {} symbols in {}".format(len(stock_list), time.time()-start_time))

def main():
    start_time = time.time()
    initialize()
    (_, unknown_list) = load_historic_data(get_symbols())
    # Try GoogleFinance for unknown stocks
    if unknown_list:
        google_analysis(unknown_list)
    print ("Total elapsed time: {}".format(time.time()-start_time))

main()
