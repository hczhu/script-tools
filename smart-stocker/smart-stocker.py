#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
sys.path.append('..')

import datetime
import time
import collections
import urllib
import traceback
import copy
import re
import os.path
import cgi

from table_printer import *
from smart_stocker_private_data import *
from smart_stocker_public_data import *
from smart_stocker_global import *
from smart_stocker_strategy import *
import HTML
import html
import logging

#--------------Beginning of logic util functions---------------
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    RED = '\033[31m'
    ENDC = '\033[0m'

def GetIRR(final_net_value, inflow_records):
    if len(inflow_records) == 0:
        return 0.0
    inflow_records.sort()
    low, high = -1.0, 5.0
    now = datetime.date.today()
    while low + 0.004 < high:
        mid = (low + high) / 2
        day_rate = pow(mid + 1, 1.0 / 365)
        dcf = 0
        for inflow in inflow_records:
            dcf -= inflow[1] * pow(day_rate, (now - inflow[0]).days)
        if abs(final_net_value + dcf) < 1:
            low = high = mid
        elif final_net_value + dcf > 0:
            low = mid
        else:
            high = mid
    return low

#--------------End of logic util functions---------------

def PrintTableMapHtml(header, tableMap, float_precision = 0):
    table_data = [
        ['' if key not in row else str(myround(row[key], float_precision)) if isinstance(row[key], float) else row[key]
            for key in header] 
        for row in tableMap
    ]
    return HTML.table(
        table_data,
        header_row = header,
        col_align  = ['center'] * len(header),
        # attribs = {'border': '5'},
        style='border: 2px solid black;'
    )

def CreateHtmlPageAndBody():
    page = html.HTML('html')
    page.head('<meta charset="UTF-8">', escape=False)
    body = page.body()
    return page, body

def WriteToStaticHtmlFile(filename, content, anchor):
    link = 'smart-stocker/' + filename
    filename = WWW_ROOT + '/' + link
    with open(filename, 'w') as output_file:
        os.chmod(filename, 0o600)
        output_file.write(content) 
    return HTML.link(anchor, link)

def InitLogger():
    FORMAT = '%(asctime)s %(filename)s:%(lineno)s %(levelname)s:%(message)s'
    logging.basicConfig(format=FORMAT, stream = sys.stderr, level=logging.INFO)
    logging.info('Got a logger.')

def InitAll():
    InitExRate()
    home = os.path.expanduser("~")
    global GD_CLIENT
    GD_CLIENT = LoginMyGoogleWithFiles()

def ReadRecords():
    logging.info('Reading trade records...\n')
    records = GetTransectionRecords(GD_CLIENT)
    logging.info('Finished reading trade records.\n')
    for record in records:
        date_str = record['date']
        record['date'] = datetime.date(int(date_str[0:4]), int(date_str[4:6]), int(date_str[6:8]))

    records.sort(key = lambda record: record['date']) 

    sell_fee = 18.1 / 10000
    buy_fee = 8.1 / 10000
    for record in records:
        record['extra'] = 0.0
        price, buy_shares = float(record['price']), int(record['amount'])
        fee = float(record['commission']) if record['commission'] != '' else (
            buy_fee * abs(buy_shares * price) if buy_shares > 0 else sell_fee * abs(buy_shares * price))
        record['price'], record['amount'], record['commission'] = price, buy_shares, fee
    return records

def ProcessRecords(all_records, accounts = set([]), goback = 0, tickers = set([]), name_patterns = set([])):
    all_records.sort(key = lambda record: record['date'])
    cutoff_date = datetime.date.today() - (datetime.timedelta(days = goback))
    logging.info('cut off date = %s\n'%(str(cutoff_date)))
    is_interested = lambda ticker, name: ticker in tickers or any([name.find(name_pattern) >= 0 for name_pattern in name_patterns]) or \
                                        ticker == 'investment' or (len(tickers) == 0 and len(name_patterns) == 0)
    filtered_record = []
    for record in all_records:
        account = record['account']
        if len(accounts) > 0 and account not in accounts:
            continue
        if record['date'] > cutoff_date:
            continue
        if record.get('disabled', '0') == '1':
            continue
        filtered_record.append(record)
        account_info = ACCOUNT_INFO[account]
        ticker = record['ticker']
        name = record['name']
        if not is_interested(ticker, name): continue
        currency = record['currency'].lower()
        # logging.info('record: %s\n'%(str(record)))
        if goback > 0 and name != '':
            STOCK_INFO[ticker]['currency'] = currency
            STOCK_INFO[ticker]['name'] = name
            NAME_TO_CODE[name] = ticker
            CODE_TO_NAME[ticker] = name
        base_currency = ACCOUNT_INFO[account]['currency']
        ex_rate = EX_RATE[currency + '-' + base_currency]
        trans_date = record['date']
        buy_shares = record['amount']
        origin_price = record['price']
        price = origin_price * ex_rate
        fee = record['commission'] * ex_rate
        inflow = price * buy_shares * (1.0 if ticker in account_info else -1.0)
        inflow -= fee
        account_info['txn-fee'] += fee if fee > 0 else 0
        account_info['cash'] += inflow
        if ticker == 'investment':
            account_info['cash-flow'] += [(record['date'], inflow)]
            account_info[ticker] += inflow
        elif ticker in account_info:
            account_info[ticker] += -inflow
        elif fee < 0 and buy_shares ==0:
            # Dividend
            account_info['dividend'] += inflow
            STOCK_INFO[ticker]['profit'] = inflow / ex_rate + STOCK_INFO[ticker].get('profit', 0.0)
        else:
            account_info['holding-shares'][ticker] += buy_shares
            STOCK_INFO[ticker]['profit'] = inflow / ex_rate + STOCK_INFO[ticker].get('profit', 0.0)
            STOCK_INFO[ticker]['holding-shares'] = buy_shares + STOCK_INFO[ticker].get('holding-shares', 0)
            if name not in STOCK_INFO[ticker]:
                STOCK_INFO[ticker]['name'] = name
                STOCK_INFO[ticker]['currency'] = currency
    return filtered_record

def PrintAccountInfo():
    aggregated_accout_info = {
        'account': 'ALL',
        'currency': CURRENCY,
        'investment': 0.0,
        'market-value': 0.0,
        'cash': 0.0,
        'net': 0.0,
        'dividend': 0,
        'interest-loss': 0,
        'margin-interest': 0,
        'txn-fee': 0,
        'cash-flow': [],
        'holding-shares': collections.defaultdict(int),
        'holding-percent': collections.defaultdict(float),
        'holding-percent-all': collections.defaultdict(float),
        'holding-value': collections.defaultdict(float),
        'support-currencies': [],
        'buying-power': 0.0,
    }
    for account, account_info in ACCOUNT_INFO.items():
        base_currency = ACCOUNT_INFO[account]['currency']
        holding = account_info['holding-shares']
        account_info['holding-shares'] = holding = {ticker: shares for ticker, shares in holding.items() if shares != 0}
        for ticker in holding.keys():
            if holding[ticker] != 0:
                mv = GetMarketPrice(ticker) * EX_RATE[GetCurrency(ticker) + '-' + base_currency] * holding[ticker]
                account_info['market-value'] += mv
                account_info['holding-value'][ticker] = mv
                if holding[ticker] > 0: account_info['margin-requirement'] += mv * (1 if ticker.find('@') >=0 else account_info['margin-ratio'])
                else: account_info['margin-requirement'] -= mv
        account_info['net'] = account_info['market-value'] + account_info['cash']
        account_info['buying-power'] = (account_info['net'] - account_info['margin-requirement']) / account_info['margin-ratio']
        account_info['cushion-ratio'] = (account_info['net'] - account_info['margin-requirement']) / max(1, account_info['market-value']) * 100.0

    header = [
        'account',
        'currency',
        'market-value',
        'investment',
        'net',
        'txn-fee',
        'dividend',
        'margin-interest',
        'tax',
        # 'margin-requirement',
        # 'leverage',
        'cash',
        'cash-ratio',
        # 'cushion-ratio',
        'IRR',
        # 'buying-power'
    ]
    for account, account_info in ACCOUNT_INFO.items():
        base_currency = ACCOUNT_INFO[account]['currency']
        ex_rate = EX_RATE[base_currency + '-' + aggregated_accout_info['currency']]
        account_info['cash-ratio'] = 100.0 * account_info['cash'] / max(1, account_info['net'])
        for key in ['buying-power', 'net', 'investment', 'market-value', 'cash', 'dividend', 'margin-interest', 'txn-fee',]:
            aggregated_accout_info[key] += ex_rate * account_info[key]
        for key in ['cash-flow']:
            aggregated_accout_info[key] += map(lambda inflow: (inflow[0], inflow[1] * ex_rate), account_info[key])
        for key in ['holding-shares']:
            for ticker, value in account_info[key].items():
                aggregated_accout_info[key][ticker] += value
        for key in ['holding-value']:
            for ticker, value in account_info[key].items():
                aggregated_accout_info[key][ticker] += value * ex_rate

    aggregated_accout_info['cash-ratio'] = 100.0 * aggregated_accout_info['cash'] / aggregated_accout_info['net']
    
    records = [
        ACCOUNT_INFO[account] for account in ACCOUNT_INFO.keys()
    ]
    records += [aggregated_accout_info]

    ACCOUNT_INFO['ALL'] = aggregated_accout_info

    for account, account_info in ACCOUNT_INFO.items():
        ex_rate = EX_RATE[account_info['currency'] + '-' + ACCOUNT_INFO['ALL']['currency']] 
        account_info['txn-fee-ratio'] = account_info['txn-fee'] / max(max(1.0, account_info['net']), account_info['market-value']) * 1000
        account_info['leverage'] = 100.0 * account_info['market-value'] / max(1, account_info['net'])
        account_info['IRR'] = GetIRR(account_info['net'], account_info['cash-flow']) * 100
        account_info['buying-power-percent'] = account_info['buying-power'] / max(1, account_info['net'])
        account_info['buying-power-percent-all'] = ex_rate * account_info['buying-power'] / max(1, ACCOUNT_INFO['ALL']['net'])
        for ticker, value in account_info['holding-value'].items():
            account_info['holding-percent'][ticker] = value / max(1, account_info['net'])
            account_info['holding-percent-all'][ticker] = ex_rate * value / max(1, ACCOUNT_INFO['ALL']['net'])
        logging.info('%s\n'%(str(account_info)))

    return PrintTableMapHtml(header, records)
      
def PrintHoldingSecurities():
    stat_records_map = []
    
    summation = {
        'Chg': 0.0,
        'Percent': 0.0,
        'Stock name': 'Summary',
        'sdv/p': 0.0,
        'ddv/p': 0.0,
    }
    holding_shares = ACCOUNT_INFO['ALL']['holding-shares']
    holding_value = ACCOUNT_INFO['ALL']['holding-value']
    holding_percent = ACCOUNT_INFO['ALL']['holding-percent-all']
    for ticker, shares in holding_shares.items():
        if shares == 0: continue
        chg = GetMarketPriceChange(ticker)
        currency = GetCurrency(ticker)
        name = STOCK_INFO[ticker]['name']
        logging.info('Collecting info for %s(%s)\n'%(ticker, name))
        record = {
                'Percent': holding_percent[ticker],
                'Shares': shares,
                'MV': str(myround(holding_value[ticker] * EX_RATE[CURRENCY + '-' + currency] / 1000.0, 0)) + 'K',
                'Currency': currency,
                'Chg': chg,
                'sdv/p': myround(FINANCAIL_DATA_ADVANCE[ticker]['sdv/p'] * 100, 2) if 'sdv/p' in FINANCAIL_DATA_ADVANCE[ticker] else 0.0,
                'ddv/p': myround(FINANCAIL_DATA_ADVANCE[ticker]['ddv/p'] * 100, 2) if 'ddv/p' in FINANCAIL_DATA_ADVANCE[ticker] else 0.0,
                'Stock name': name + '(' + ticker + ')',
        }
        stat_records_map.append(record)
    
    for record in stat_records_map:
        summation['Percent'] += record['Percent']
        summation['sdv/p'] += record['Percent'] * record['sdv/p']
        summation['ddv/p'] += record['Percent'] * record['ddv/p']
        for col in ['Chg']:
            summation[col] += record['Percent'] * record['Chg']

    summation['sdv/p'] /= max(1.0, summation['Percent'])
    summation['sdv/p'] = myround(summation['sdv/p'], 1)

    summation['ddv/p'] /= max(1.0, summation['Percent'])
    summation['ddv/p'] = myround(summation['ddv/p'], 1)

    stat_records_map.sort(reverse = True, key = lambda record: record.get('Percent', 0))
    stat_records_map.insert(0, summation)

    for record in stat_records_map:
        record['Percent'] = str(myround(record['Percent'] * 100, 0)) + '%'
        record['Chg'] = str(myround(record['Chg'], 1)) + '%'
        if 'MV' in record:
            record['MV'] += ' ' + record['Currency']
    table_header = [
        'Percent',
        'Shares',
        'MV',
        'Chg',
        # 'sdv/p',
        # 'ddv/p',
        'Stock name',
    ]
    return PrintTableMapHtml(table_header, stat_records_map)

def RunStrategies():
    tipList = []  
    for name, strategy in STRATEGY_FUNCS.items():
        logging.info('Running strategy: %s\n'%(name))
        tip = strategy()
        if tip != '':
            tipList.append('<pre>\n' + tip + '\n</pre>')
    return HTML.list(tipList)

def PrintStocks(names):
    tableMap = []
    header = [col for col in (FINANCIAL_KEYS - set(['name']))]
    header += ['name']
    stocks_from_category = set([])
    for name in names: stocks_from_category |= set(CATEGORIZED_STOCKS[name])

    for code in FINANCAIL_DATA_ADVANCE.keys():
        if any([CODE_TO_NAME[code].find(name) != -1 or code in stocks_from_category for name in names]):
            data = dict(FINANCAIL_DATA_ADVANCE[code])
            data['name'] = ('*' if code in ACCOUNT_INFO['ALL']['holding-shares'] else '') + CODE_TO_NAME[code]
            tableMap.append(data)
    tableMap.sort(key = lambda recordMap: recordMap['p/book-value'] if 'p/book-value' in recordMap else 0)
    PrintTableMap(header, tableMap, float_precision = 3, header_transformer = lambda header: header.replace('book-value', 'bv'))

def OutputVisual(all_records, tickers, path):
    template_file = path + '/visual-trades-temp.html' 
    all_trades = {}
    all_records.sort(key = lambda record: record['date'])
    min_day_gap = 1
    transformer = lambda ticker: ticker if ticker.find('@') == -1 else ticker[0:ticker.find('@')]
    if '*' in tickers:
        tickers = set([transformer(record['ticker']) for record in all_records])
    for ticker in tickers:
        prev_date = datetime.date(2000, 1, 1)
        shares, invest = 0, 0.0
        for record in all_records:
            if transformer(record['ticker']) != ticker: continue
            if record['name'] == '': continue
            CODE_TO_NAME[ticker] = record['name']
            ticker = transformer(ticker)
            currency = record['currency']
            trans_date = record['date']
            diff_days = (trans_date - prev_date).days
            if diff_days < min_day_gap:
                trans_date = prev_date + datetime.timedelta(days = min_day_gap)
            prev_date = trans_date
            shares += record['amount']
            invest += record['commission'] + record['amount'] * record['price']
            mv = shares * record['price']
            if ticker not in all_trades: all_trades[ticker] = []
            all_trades[ticker].append([
                # 'new Date(%d, %d, %d)'%(trans_date.year, trans_date.month - 1, trans_date.day),
                int(time.mktime(trans_date.timetuple())) * 1000,
                record['price'],
                ('+' if record['amount'] > 0 else '') + str(int(record['amount'])),
                'shares: %d profit: %dK %s mv: %dK'%(shares, (mv - invest) / 1000, currency, mv / 1000),
            ])
            if len(all_trades[ticker]) > 1:
                assert all_trades[ticker][-1][0] > all_trades[ticker][-2][0]
                
    content = ''
    with open(template_file, 'r') as temp_file:
        content = temp_file.read() 
    content = content.replace('%TRADES%', ',\n'.join([
        '"%s": %s'%(CODE_TO_NAME[key], str(value)) for key, value in all_trades.items()
    ]))
    return WriteToStaticHtmlFile('charts.html', content, 'Visual trades')

def PrintProfitBreakDown():
    tableMap = []
    header = ['profit', 'name', ]
    category_profit = collections.defaultdict(float)
    # Add option profit to its share.
    for ticker in STOCK_INFO.keys():
        if 'profit' not in STOCK_INFO[ticker]: continue
        if ticker.find('@') >= 0 and ticker.find('-') >= 0:
            mv = 0.0
            if STOCK_INFO[ticker]['holding-shares'] > 0:
                mv = STOCK_INFO[ticker]['holding-shares'] * GetMarketPrice(ticker)
            code = ticker[0:ticker.find('-')]
            STOCK_INFO[code]['profit'] = mv + STOCK_INFO[code].get('profit', 0.0) + STOCK_INFO[ticker]['profit']

    for ticker in STOCK_INFO.keys():
        if 'profit' not in STOCK_INFO[ticker]: continue
        if ticker.find('@') >= 0 and ticker.find('-') >= 0: continue
        mv = 0.0
        if STOCK_INFO[ticker].get('holding-shares', 0) > 0:
            mv = STOCK_INFO[ticker]['holding-shares'] * GetMarketPrice(ticker)
        tableMap += [{
            'name': STOCK_INFO[ticker]['name'],
            'profit': EX_RATE[GetCurrency(ticker) + '-' + CURRENCY] *(mv + STOCK_INFO[ticker]['profit']),
        }]
        if 'category' not in STOCK_INFO[ticker]:
            for k, v in REGEX_TO_CATE.items():
                if re.match(k, STOCK_INFO[ticker]['name']) is not None:
                    STOCK_INFO[ticker]['category'] = v
                    break
        category_profit[STOCK_INFO[ticker].get('category', 'uncategorized')] += tableMap[-1]['profit']

    page, body = CreateHtmlPageAndBody()

    tableMap.sort(reverse = True, key = lambda recordMap: abs(recordMap['profit']))

    catTableMap = [ {'name': k, 'profit': v} for k,v in category_profit.items() ]
    catTableMap.sort(reverse = True, key = lambda recordMap: abs(recordMap['profit']))

    body.p(PrintTableMapHtml(header, catTableMap, float_precision = 0), escape=False)
    body.p(PrintTableMapHtml(header, tableMap, float_precision = 0), escape=False)
    return WriteToStaticHtmlFile('profit.html', str(page), 'Profit breakdown')

def PrintDeposit(all_records, path):
    template_file = path + '/visual-trades-temp.html' 
    all_deposit = []
    invest = 0
    for record in all_records:
        if record['ticker'] != 'investment': continue
        currency = record['currency']
        trans_date = record['date']
        deposit = int((record['commission'] + record['amount'] * record['price']) * EX_RATE[currency + '-' + CURRENCY])
        invest += deposit
        all_deposit.append([
            int(time.mktime(trans_date.timetuple())) * 1000,
            invest,
            '$' + str(invest),
            '$' + str(deposit),
        ])
    content = ''
    with open(template_file, 'r') as temp_file:
        content = temp_file.read() 
    content = content.replace('%TRADES%', '"Deposit": ' + str(all_deposit))
    return WriteToStaticHtmlFile('deposit-charts.html', content, 'Visual deposit')

def PopParam(params, name, trans = str, default = str()):
    if name in params:
        res = trans(params[name]) 
        del params[name]
        return res
    return default

def main():
    page, body = CreateHtmlPageAndBody()
    try:
        InitLogger()
        input_params = cgi.FieldStorage()
        input_params = {k: input_params.getfirst(k) for k in input_params.keys() }
    
        goback = PopParam(input_params, 'goback', int, -1)

        input_args = collections.defaultdict(set)
        for key in ['accounts', 'tickers', 'names', 'visual']:
            value = PopParam(input_params, key)
            if value != '':
                input_args[key] = set(value.split(','))

        logging.info('input args: %s\n'%(str(input_args)))
    
        for ticker, price in input_params.items():
            price = float(price)
            MARKET_PRICE_CACHE[ticker] = (price, 0, 0)
        logging.info('market data cache = %s\n'%(str(MARKET_PRICE_CACHE)))

        InitAll()
     
        all_records = ReadRecords()

        GetAllStocks(GD_CLIENT)

        all_records = ProcessRecords(all_records, input_args['accounts'], goback, input_args['tickers'], input_args['names'])

        PopulateMacroData()
        PopulateFinancialData()
    
        body.p(PrintAccountInfo(), escape=False)
        body.p(PrintHoldingSecurities(), escape=False)
        body.p(RunStrategies(), escape=False)
        body.p(PrintProfitBreakDown(), escape=False)
        body.p(OutputVisual(all_records, input_args['visual'], os.path.dirname(sys.argv[0])), escape=False)
        body.p(PrintDeposit(all_records, os.path.dirname(sys.argv[0])), escape=False)

    except Exception as ins:
        traceback.print_exc(file=sys.stderr)
    print page 

main()
