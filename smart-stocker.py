#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import datetime
import time
import collections
import urllib2
import traceback
import copy
import re
import os.path

from table_printer import *
from smart_stocker_private_data import *
from smart_stocker_public_data import *
from smart_stocker_global import *
from smart_stocker_strategy import *

#--------------Beginning of logic util functions---------------
class bcolors:
  HEADER = '\033[95m'
  OKBLUE = '\033[94m'
  OKGREEN = '\033[92m'
  WARNING = '\033[93m'
  FAIL = '\033[91m'
  RED = '\033[31m'
  ENDC = '\033[0m'

def GetIRR(market_value, cash_flow_records):
  if len(cash_flow_records) == 0:
    return 0.0
  cash_flow_records.sort()
  low, high = -1.0, 5.0
  day_loan_rate = pow(LOAN_RATE + 1, 1.0 / 365)
  now = datetime.date.today()
  while low + 0.004 < high:
    mid = (low + high) / 2
    day_rate = pow(mid + 1, 1.0 / 365)
    balance = 0
    prev_date = cash_flow_records[0][0]
    dcf = 0
    for record in cash_flow_records:
      if balance < 0:
        balance *= pow(day_loan_rate, (record[0] - prev_date).days)
      prev_date = record[0]
      if record[1] in TOTAL_INVESTMENT:
        #invest money or withdraw cash
        balance -= record[2]
        dcf += record[2] * pow(day_rate, (now - record[0]).days)
      else:
        balance += record[2]
    if balance < 0:
      balance *= pow(day_loan_rate, (now - prev_date).days)
    if balance + market_value + dcf > 0:
      low = mid
    else:
      high = mid
  return low

#--------------End of logic util functions---------------

def InitAll():
  InitExRate()
  home = os.path.expanduser("~")
  global GD_CLIENT
  GD_CLIENT = LoginMyGoogle(home + '/.smart-stocker-google-email.txt',
                            home + '/.smart-stocker-google-password.txt')

def CalOneStock(records, code, name):
  capital_cost = 0.0
  net_profit = 0.0
  investment = 0.0
  prev_date = datetime.date(2000, 1, 1)
  holding_cost = 0.0
  holding_shares = 0
  day_trade_profit = 0
  day_trade_net_shares = 0
  sum_day_trade_profit = 0
  day_trade_time = -1
  sum_fee = 0
  vid = 'visualization_%s'%(code)
  data = ''
  prices = []
  for record in records:
    currency = record['currency'].lower()
    ex_rate = EX_RATE[currency + '-' + CURRENCY]
    trans_date = record['date']
    buy_shares = record['amount']
    origin_price = record['price']
    price = origin_price * ex_rate
    fee = record['commission'] * ex_rate
    sum_fee += fee
    value = -price * buy_shares - fee - record['extra'] * ex_rate
    if -1 == record['transection'].find('股息'):
      data += '[new Date(%d, %d, %d), %.3f, \'%s%d\', \'%.0fK %s\'],\n'%(
          trans_date.year, trans_date.month - 1, trans_date.day,
          origin_price, '+' if buy_shares > 0 else '',
          buy_shares, (value + 500) / 1000, CURRENCY)
      prices.append(origin_price)
    if investment > 0.0:
      diff_days = (trans_date - prev_date).days
      assert diff_days >= 0
    if prev_date == trans_date:
      day_trade_net_shares += buy_shares
      day_trade_profit += value
    else:
      if day_trade_net_shares == 0:
        sum_day_trade_profit += day_trade_profit
        day_trade_time += 1
      day_trade_profit = value
      day_trade_net_shares = buy_shares

    investment -= value
    #assert investment >= 0.0
    net_profit += value
    prev_date = trans_date
    if buy_shares > 0 and holding_shares > 0:
      assert value <= 0.0
      holding_cost = (holding_cost * holding_shares - value) / (holding_shares + buy_shares)
    holding_shares += buy_shares
  if day_trade_net_shares == 0:
    sum_day_trade_profit += day_trade_profit
    day_trade_time += 1
  return (net_profit, capital_cost, holding_shares, sum_day_trade_profit, day_trade_time, sum_fee,
          currency,
          FUNCTION_TEMPLATE%(
            name,
            data,
            vid,
            min(prices),
            max(prices),
            currency),
          DIV_TEMPLATE%(vid))

def ReadRecords():
  records = GetTransectionRecords(GD_CLIENT)
  for record in records:
    date_str = record['date']
    record['date'] = datetime.date(int(date_str[0:4]), int(date_str[4:6]), int(date_str[6:8]))

  records.sort(key = lambda record: record['date']) 

  all_records = collections.defaultdict(list)
  sell_fee = 18.1 / 10000
  buy_fee = 8.1 / 10000
  for record in records:
    record['extra'] = 0.0
    price, buy_shares = float(record['price']), int(record['amount'])
    fee = float(record['commission']) if record['commission'] is not None else (
      buy_fee * abs(buy_shares * price) if buy_shares > 0 else sell_fee * abs(buy_shares * price))
    record['price'], record['amount'], record['commission'] = price, buy_shares, fee
    last = all_records[record['ticker']][-1] if len(all_records[record['ticker']]) > 0 else {}
    if (len(last) > 0 and
        (record['date'] - last['date']).days < 7
        and record['transection'].find('股息') == -1
        and last['transection'].find('股息') == -1):
      if buy_shares + last['amount'] != 0:
        last['price'] = (last['extra'] + buy_shares * price + last['amount'] * last['price']) / (buy_shares + last['amount'])
        last['extra'] = 0
      else:
        last['extra'] += buy_shares * price + last['amount'] * last['price']
      last['amount'] += buy_shares
      last['commission'] += fee
    else:
      all_records[record['ticker']].append(record)
  return all_records

def PrintHoldingSecurities(all_records, charts = False):
  global NET_ASSET_BY_CURRENCY
  silent_column = [
  ]
  for col in ['Price']:
    if col not in set(sys.argv):
      silent_column.append(col)

  stat_records_map = []
  
  summation = {}
  summation['Stock name'] = 'Summary'
  
  function_html = ''
  div_html = ''
  
  for key in all_records.keys():
    sys.stderr.write('Processing [' + key + ']\n')
    name = all_records[key][0]['name']
    name = name if name is not None else ''
    # All in CURRENCY
    (net_profit, capital_cost, remain_stock, dtp, dt, txn_fee, currency, function, division) = CalOneStock(
     all_records[key], key, name)
    if key in TOTAL_INVESTMENT:
      TOTAL_CAPITAL[currency] += -net_profit
      continue
    if key in STOCK_INFO and currency != STOCK_INFO[key]['currency']:
      print 'Inconsistent currency for %s: %s != %s'%(CODE_TO_NAME[key], currency, STOCK_INFO[key]['currency'])
    function_html += function
    div_html += division
    investment = -net_profit
    TOTAL_INVESTMENT[currency] += investment
    TOTAL_TRANSACTION_FEE[currency] += txn_fee
    ex_rate = EX_RATE[currency + '-' + CURRENCY]
    mp, chg, mv, = 0.0001, 0, 0
    if remain_stock != 0:
      mp = GetMarketPrice(key)
      chg = GetMarketPriceChange(key)
      mv = mp * remain_stock * ex_rate
    TOTAL_MARKET_VALUE[currency] += mv
    HOLDING_SHARES[key] = remain_stock
    sys.stderr.write('Profit %.0f from %s shares %d\n'%(net_profit + mv, CODE_TO_NAME[key] if key in CODE_TO_NAME else key, remain_stock))
    record = {
        'Code': key,
        'HS': remain_stock,
        'MV': myround(mv, 0),
        'MV(K)': myround(mv / 1000.0, 0),
        'currency': currency,
        'Price': mp,
        'Chg': round(chg, 2),
        'CC': myround(capital_cost, 0),
        '#TxN': len(all_records[key]),
        'TNF': myround(txn_fee, 0),
        'DTP': myround(dtp, 0),
        '#DT': dt,
        'Pos': remain_stock,
        'Stock name': name + '(' + key + ')',
    }
    for col in ['MV', 'MV(K)', 'CC', '#TxN', 'TNF', 'DTP', '#DT']:
      summation[col] = summation.get(col, 0) + record[col]
    if remain_stock != 0:
      stat_records_map.append(record)
  
  for dt in [TOTAL_MARKET_VALUE, TOTAL_CAPITAL,
             TOTAL_INVESTMENT, TOTAL_TRANSACTION_FEE]:
    dt['usd'] += dt['hkd']
    dt['usd'] += dt['jpy']
  
  # All are in CURRENCY
  cash_flow = collections.defaultdict(list)
  for key in all_records.keys():
    for record in all_records[key]:
      currency = record['currency'].lower()
      ex_rate = EX_RATE[currency + '-' + CURRENCY]
      trans_date = record['date']
      fee = record['commission'] * ex_rate
      buy_shares = record['amount']
      price = record['price'] * ex_rate
      value = -price * buy_shares - fee - record['extra'] * ex_rate
      cash_flow[currency].append([trans_date, key, value]);
  
  cash_flow['usd'] += cash_flow['hkd']
  cash_flow['usd'] += cash_flow['jpy']
  
  for dt in [TOTAL_MARKET_VALUE, TOTAL_CAPITAL,
             TOTAL_INVESTMENT, TOTAL_TRANSACTION_FEE]:
    dt['all'] = dt['usd'] + dt['cny']
    dt['cny'] *= EX_RATE[CURRENCY + '-cny']
    dt['usd'] *= EX_RATE[CURRENCY + '-usd']

  cash_flow['all'] = copy.deepcopy(cash_flow['usd'] + cash_flow['cny'])
  for record in cash_flow['cny']:
    record[2] *= EX_RATE[CURRENCY + '-cny']
  for record in cash_flow['usd']:
    record[2] *= EX_RATE[CURRENCY + '-usd']
  
  for currency in ['usd', 'cny', 'all']:
    NET_ASSET_BY_CURRENCY[currency] = TOTAL_MARKET_VALUE[currency] + TOTAL_CAPITAL[currency] - TOTAL_INVESTMENT[currency]
    CAPITAL_INFO[currency] = {
        'cash': TOTAL_CAPITAL[currency],
        'currency': currency,
        'net': int(TOTAL_MARKET_VALUE[currency] + TOTAL_CAPITAL[currency] - TOTAL_INVESTMENT[currency]),
        'market-value': int(TOTAL_MARKET_VALUE[currency]),
        'free-cash': int(TOTAL_CAPITAL[currency] - TOTAL_INVESTMENT[currency]),
        'txn-fee': int(TOTAL_TRANSACTION_FEE[currency]),
        'txn-fee-ratio': 100.0 * TOTAL_TRANSACTION_FEE[currency] / TOTAL_MARKET_VALUE[currency],
        'IRR': GetIRR(TOTAL_MARKET_VALUE[currency], cash_flow[currency]) * 100,
    }
  for currency in ['usd', 'cny']:
    CAPITAL_INFO[currency]['SMA'] = CAPITAL_INFO[currency]['free-cash'] + CAPITAL_INFO[currency]['market-value'] * SMA_DISCOUNT[currency]
  for code in HOLDING_SHARES.keys():
    if HOLDING_SHARES[code] < 0:
      CAPITAL_INFO['usd']['SMA'] += int(HOLDING_SHARES[code] * GetMarketPrice(code) * EX_RATE[STOCK_INFO[code]['currency'] + '-usd'])

  for currency in ['usd', 'cny']:
    CAPITAL_INFO[currency]['SMA-ratio'] = 100.0 * CAPITAL_INFO[currency]['SMA'] / CAPITAL_INFO[currency]['market-value']
    CAPITAL_INFO[currency]['buying-power'] = (CAPITAL_INFO[currency]['SMA-ratio'] / 100.0 - MIN_SMA_RATIO[currency]
        ) * CAPITAL_INFO[currency]['market-value'] / (SMA_DISCOUNT[currency] if SMA_DISCOUNT[currency] > 0 else 1.0)

  CAPITAL_INFO['all']['buying-power'] = CAPITAL_INFO['usd']['buying-power'] * EX_RATE['usd-' + CURRENCY] + CAPITAL_INFO['cny']['buying-power'] * EX_RATE['cny-' + CURRENCY]
  
  for currency in set(CURRENCIES) - set(['usd', 'cny']):
    CAPITAL_INFO[currency]['buying-power'] = EX_RATE['usd-' + currency] * CAPITAL_INFO['usd']['buying-power']

  for currency in CURRENCIES:
    CAPITAL_INFO[currency]['buying-power-ratio'] = CAPITAL_INFO[currency]['buying-power'] * EX_RATE[
                currency + '-' + CURRENCY] / CAPITAL_INFO['all']['net']
  capital_table_map = [CAPITAL_INFO['usd'], CAPITAL_INFO['cny'], CAPITAL_INFO['all']]
  capital_header = [
    'currency',
    'market-value',
    'net',
    'cash',
    'free-cash',
    'txn-fee-ratio',
    'IRR',
    'SMA',
    'SMA-ratio',
    'buying-power',
  ]
  PrintTableMap(capital_header, capital_table_map, set(), truncate_float = True)
  for col in ['Chg', 'Percent']:
    summation[col] = 0.0
  for record in stat_records_map:
    HOLDING_PERCENT[record['Code']] = 1.0 * record['MV'] / CAPITAL_INFO['all']['net']
    summation['Percent'] += HOLDING_PERCENT[record['Code']]
    record['Percent'] = str(myround(HOLDING_PERCENT[record['Code']] * 100, 1)) + '%'
    currency = 'cny' if record['currency'] == 'cny' else 'usd'
    record['Percent1'] = str(myround(100.0 * record['MV'] * EX_RATE[CURRENCY + '-' + currency] / NET_ASSET_BY_CURRENCY[currency], 1)) + '%'
    for col in ['Chg']:
      summation[col] += HOLDING_PERCENT[record['Code']] * record[col]
  for col in ['Chg']:
    summation[col] = round(summation[col], 2)
  summation['Percent'] = str(round(summation['Percent'] * 100, 0)) + '%'
  stat_records_map.append(summation)
  stat_records_map.sort(reverse = True, key = lambda record: record.get('MV', 0))
  # PrintTableMap(table_header, stat_records_map, silent_column, truncate_float = False)
  if charts:
    open('/tmp/charts.html', 'w').write(
      HTML_TEMPLATE%(function_html, div_html) 
    )

  for code in HOLDING_PERCENT:
    asset_info = ASSET_INFO[code]
    asset_info['market-value'] = HOLDING_SHARES[code] * GetMarketPrice(code)
    asset_info['currency'] = STOCK_INFO[code]['currency']
  for currency in ['usd', 'cny']:
    ASSET_INFO['buying-power-' + currency]['market-value'] = CAPITAL_INFO[currency]['buying-power']
    ASSET_INFO['buying-power-' + currency]['currency'] = currency if currency != 'all' else CURRENCY

  for currency in CURRENCIES:
    CAPITAL_INFO[currency]['asset'] = 0.0
  
  for code in ASSET_INFO:
    asset_info = ASSET_INFO[code]
    currency = asset_info['currency']
    if currency == 'cny':
      CAPITAL_INFO[currency]['asset'] += ASSET_INFO[code]['market-value']
    else:
      CAPITAL_INFO['usd']['asset'] += ASSET_INFO[code]['market-value'] * EX_RATE[currency + '-usd']

  CAPITAL_INFO['all']['asset'] = CAPITAL_INFO['usd']['asset'] * EX_RATE['usd-' + CURRENCY] + CAPITAL_INFO['cny']['asset'] * EX_RATE['cny-' + CURRENCY]

  for currency in set(CURRENCIES) - set(['usd', 'cny']):
    CAPITAL_INFO[currency]['asset'] = EX_RATE['usd-' + currency] * CAPITAL_INFO['usd']['asset']
    CAPITAL_INFO[currency]['net'] = EX_RATE['usd-' + currency] * CAPITAL_INFO['usd']['net']

  asset_record_map = []

  for code in ASSET_INFO.keys():
    asset_info = ASSET_INFO[code]
    currency = asset_info['currency']
    asset_info['net-percent'] = EX_RATE[currency + '-' + CURRENCY] * asset_info['market-value'] / CAPITAL_INFO['all']['net']
    asset_info['net-currency-percent'] = asset_info['market-value'] / CAPITAL_INFO[currency]['net']
    asset_info['asset-percent'] = EX_RATE[currency + '-' + CURRENCY] * asset_info['market-value'] / CAPITAL_INFO['all']['asset']
    asset_info['asset-currency-percent'] = asset_info['market-value'] / CAPITAL_INFO[currency]['asset']
    asset_record_map.append({
      'market-value': myround(asset_info['market-value'] / 1000, 0),
      'net-percent': myround(asset_info['net-percent'] * 100, 1),
      'net-currency-percent': myround(asset_info['net-currency-percent'] * 100, 1),
      'asset-percent': myround(asset_info['asset-percent'] * 100, 1),
      'asset-currency-percent': myround(asset_info['asset-currency-percent'] * 100, 1),
      'chg': GetMarketPriceChange(code) if code in CODE_TO_NAME else 0.0,
      'stock name': (CODE_TO_NAME[code] + '(' + code +')') if code in CODE_TO_NAME else code,
      'shares': HOLDING_SHARES[code] if code in HOLDING_SHARES else 0,
    })
  asset_summary = {}
  for key in ['net-percent', 'asset-percent']:
    asset_summary[key] = sum([record[key] if record['stock name'].find('buying-power') == -1 else 0 for record in asset_record_map])

  asset_summary['chg'] = myround(sum(record['chg'] * record['net-percent'] / 100 for record in asset_record_map), 1)

  asset_record_map.sort(key = lambda record: record['net-percent'], reverse = True)

  asset_record_map = [asset_summary] + asset_record_map
  table_header = [
                  'net-percent',
                  'net-currency-percent',
                  'market-value',
                  'shares',
                  # 'asset-percent',
                  # 'asset-currency-percent',
                  'chg',
                  'stock name',
                 ]
  PrintTableMap(table_header, asset_record_map, silent_column, truncate_float = False, header_transformer = lambda name: name.replace('-percent', ''))
  for currency in set(CURRENCIES) - set(['usd', 'cny']):
    for key in ['asset-percent', 'net-percent']:
      ASSET_INFO['buying-power-' + currency][key] = ASSET_INFO['buying-power-usd'][key]

def RunStrategies():
  for strategy in STRATEGY_FUNCS:
    tip = strategy()
    if tip != '': print bcolors.FAIL + 'ACTION!!! ' + tip + bcolors.ENDC

def PrintStocks(names):
  tableMap = []
  header = [col for col in (FINANCIAL_KEYS - set(['name']))]
  header += ['name']
  for code in FINANCAIL_DATA_ADVANCE.keys():
    if any([CODE_TO_NAME[code].find(name) != -1 for name in names]):
      data = dict(FINANCAIL_DATA_ADVANCE[code])
      data['name'] = CODE_TO_NAME[code]
      tableMap.append(data)
  PrintTableMap(header, tableMap, float_precision = 5)

try:
  args = set(sys.argv[1:])
  prices = filter(lambda arg: arg.find('=') != -1, args)
  target_names = args - set(prices)
  InitAll()
  GetStockPool(GD_CLIENT)

  if len(prices) > 0:
    for pr in prices:
      info = pr.split('=')
      MARKET_PRICE_CACHE[NAME_TO_CODE[info[0]]] = (float(info[1]), 0, 0)
    sys.stderr.write('market data cache = %s\n'%(str(MARKET_PRICE_CACHE)))

  PopulateMacroData()
  GetFinancialData(GD_CLIENT) 
  PopulateFinancialData()
  PrintHoldingSecurities(ReadRecords(), 'chart' in args)
  if len(target_names) > 0:
    names = ','.join(target_names).split(',')
    PrintStocks(names)
  RunStrategies()
except Exception as ins:
  print 'Run time error: ', ins
  traceback.print_exc(file=sys.stdout)
