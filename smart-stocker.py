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

def InitAll():
  InitExRate()
  home = os.path.expanduser("~")
  global GD_CLIENT
  GD_CLIENT = LoginMyGoogle(home + '/.smart-stocker-google-email.txt',
                            home + '/.smart-stocker-google-password.txt')

def ReadRecords():
  records = GetTransectionRecords(GD_CLIENT)
  for record in records:
    date_str = record['date']
    record['date'] = datetime.date(int(date_str[0:4]), int(date_str[4:6]), int(date_str[6:8]))

  records.sort(key = lambda record: record['date']) 

  sell_fee = 18.1 / 10000
  buy_fee = 8.1 / 10000
  for record in records:
    record['extra'] = 0.0
    price, buy_shares = float(record['price']), int(record['amount'])
    fee = float(record['commission']) if record['commission'] is not None else (
      buy_fee * abs(buy_shares * price) if buy_shares > 0 else sell_fee * abs(buy_shares * price))
    record['price'], record['amount'], record['commission'] = price, buy_shares, fee
  return records

def ProcessRecords(all_records):
  all_records.sort(key = lambda record: record['date'])
  for record in all_records:
    account = record['account']
    account_info = ACCOUNT_INFO[account]
    ticker = record['ticker']
    currency = record['currency'].lower()
    base_currency = ACCOUNT_INFO[account]['currency']
    ex_rate = EX_RATE[currency + '-' + base_currency]
    trans_date = record['date']
    buy_shares = record['amount']
    origin_price = record['price']
    price = origin_price * ex_rate
    fee = record['commission'] * ex_rate
    inflow = price * buy_shares * (1.0 if ticker in account_info else -1.0)
    inflow -= fee
    account_info['txn-fee'] += fee
    account_info['free-cash'] += inflow
    if ticker == 'investment':
      account_info['cash-flow'] += [(record['date'], inflow)]
    if ticker in account_info:
      account_info[ticker] += inflow
    else:
      account_info['holding-shares'][ticker] += buy_shares

def PrintAccountInfo():
  aggregated_accout_info = {
    'account': 'ALL',
    'currency': CURRENCY,
    'investment': 0.0,
    'market-value': 0.0,
    'free-cash': 0.0,
    'sma': 0.0,
    'net': 0.0,
    'dividend': 0,
    'interest-loss': 0,
    'txn-fee': 0,
    'cash-flow': [],
    'holding-shares': collections.defaultdict(int),
  }
  for account, account_info in ACCOUNT_INFO.items():
    account_info['sma'] = account_info['free-cash']
    base_currency = ACCOUNT_INFO[account]['currency']
    holding = account_info['holding-shares']
    account_info['holding-shares'] = holding = {ticker: shares for ticker, shares in holding.items() if shares != 0}
    for ticker in holding.keys():
      if holding[ticker] != 0:
        mv = GetMarketPrice(ticker) * EX_RATE[GetCurrency(ticker) + '-' + base_currency] * holding[ticker]
        account_info['market-value'] += mv
        if holding[ticker] > 0: account_info['sma'] += account_info['sma-discount'] * mv
        else: account_info['sma'] += mv
    account_info['net'] = account_info['market-value'] + account_info['free-cash']

  header = [
    'account',
    'currency',
    'net',
    'free-cash',
    'market-value',
    'sma',
    'leverage',
    'txn-fee-ratio',
    'sma-ratio',
    'IRR',
  ]
  for account, account_info in ACCOUNT_INFO.items():
    base_currency = ACCOUNT_INFO[account]['currency']
    ex_rate = EX_RATE[base_currency + '-' + aggregated_accout_info['currency']]
    for key in ['net', 'investment', 'market-value', 'free-cash', 'sma', 'dividend', 'interest-loss', 'txn-fee',]:
      aggregated_accout_info[key] += ex_rate * account_info[key]
    for key in ['cash-flow']:
      aggregated_accout_info[key] += map(lambda inflow: (inflow[0], inflow[1] * ex_rate), account_info[key])
    for key in ['holding-shares']:
      for ticker, shares in account_info[key].items():
        aggregated_accout_info[key][ticker] += shares
  
  records = [
    ACCOUNT_INFO[account] for account in ACCOUNT_INFO.keys()
  ]
  records += [aggregated_accout_info]

  ACCOUNT_INFO['ALL'] = aggregated_accout_info

  for account, account_info in ACCOUNT_INFO.items():
    account_info['sma-ratio'] = account_info['sma'] / max(account_info['net'], account_info['market-value']) * 100
    account_info['txn-fee-ratio'] = account_info['txn-fee'] / max(max(1.0, account_info['net']), account_info['market-value']) * 1000
    account_info['leverage'] = 100.0 * account_info['market-value'] / account_info['net']
    account_info['IRR'] = GetIRR(account_info['net'], account_info['cash-flow']) * 100
    sys.stderr.write('%s\n'%(str(account_info)))

  PrintTableMap(header, records, set(), truncate_float = True, float_precision = 0)
   
def PrintHoldingSecurities(all_records):
  global NET_ASSET_BY_CURRENCY
  silent_column = [
  ]
  for col in ['Price']:
    if col not in set(sys.argv):
      silent_column.append(col)

  stat_records_map = []
  
  summation = {}
  summation['Stock name'] = 'Summary'
  
  for account in ACCOUNT_INFO.keys():
    ProcessOneAccount(filter(lambda record: record['account'] != account, records))

  for ticker in HOLDING_SHARES.keys():
    if HOLDING_SHARES[ticker] == 0: continue
    mp = GetMarketPrice(ticker)
    chg = GetMarketPriceChange(ticker)
    currency = STOCK_INFO[ticker]['currency']
    ex_rate = EX_RATE[currency + '-' + CURRENCY]
    mv = mp * HOLDING_SHARES[ticker]  * ex_rate
    record = {
        'Code': ticker,
        'HS': HOLDING_SHARES[ticker],
        'MV': myround(mv, 0),
        'MV(K)': myround(mv / 1000.0, 0),
        'currency': currency,
        'Price': mp,
        'Chg': round(chg, 2),
        'Stock name': name + '(' + ticker + ')',
    }
    for col in ['MV', 'MV(K)']:
      summation[col] = summation.get(col, 0) + record[col]
    if remain_stock != 0:
      stat_records_map.append(record)
  
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
  # GetFinancialData(GD_CLIENT) 
  PopulateFinancialData()
  ProcessRecords(ReadRecords())
  PrintAccountInfo()
  if len(target_names) > 0:
    names = ','.join(target_names).split(',')
    PrintStocks(names)
  # RunStrategies()
except Exception as ins:
  print 'Run time error: ', ins
  traceback.print_exc(file=sys.stdout)
