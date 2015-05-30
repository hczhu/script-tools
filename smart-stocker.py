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
  GD_CLIENT = LoginMyGoogleWithFiles()

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
    fee = float(record['commission']) if record['commission'] != '' else (
      buy_fee * abs(buy_shares * price) if buy_shares > 0 else sell_fee * abs(buy_shares * price))
    record['price'], record['amount'], record['commission'] = price, buy_shares, fee
  return records

def ProcessRecords(all_records, accounts = set([])):
  all_records.sort(key = lambda record: record['date'])
  for record in all_records:
    account = record['account']
    if len(accounts) > 0 and account not in accounts:
      continue
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
    'buying-power': 0,
    'txn-fee': 0,
    'cash-flow': [],
    'holding-shares': collections.defaultdict(int),
    'holding-percent': collections.defaultdict(float),
    'holding-percent-all': collections.defaultdict(float),
    'holding-value': collections.defaultdict(float),
    'support-currencies': [],
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
        account_info['holding-value'][ticker] = mv
        if holding[ticker] > 0: account_info['sma'] += account_info['sma-discount'] * mv
        else: account_info['sma'] += mv
    account_info['net'] = account_info['market-value'] + account_info['free-cash']
    account_info['buying-power'] = account_info['sma'] - account_info['min-sma-ratio'] * account_info['market-value']

  header = [
    'account',
    'currency',
    'investment',
    'net',
    'buying-power',
    'leverage',
    'txn-fee-ratio',
    'sma-ratio',
    'IRR',
  ]
  for account, account_info in ACCOUNT_INFO.items():
    base_currency = ACCOUNT_INFO[account]['currency']
    ex_rate = EX_RATE[base_currency + '-' + aggregated_accout_info['currency']]
    for key in ['buying-power', 'net', 'investment', 'market-value', 'free-cash', 'sma', 'dividend', 'interest-loss', 'txn-fee',]:
      aggregated_accout_info[key] += ex_rate * account_info[key]
    for key in ['cash-flow']:
      aggregated_accout_info[key] += map(lambda inflow: (inflow[0], inflow[1] * ex_rate), account_info[key])
    for key in ['holding-shares']:
      for ticker, value in account_info[key].items():
        aggregated_accout_info[key][ticker] += value
    for key in ['holding-value']:
      for ticker, value in account_info[key].items():
        aggregated_accout_info[key][ticker] += value * ex_rate
  
  records = [
    ACCOUNT_INFO[account] for account in ACCOUNT_INFO.keys()
  ]
  records += [aggregated_accout_info]

  ACCOUNT_INFO['ALL'] = aggregated_accout_info

  for account, account_info in ACCOUNT_INFO.items():
    ex_rate = EX_RATE[account_info['currency'] + '-' + ACCOUNT_INFO['ALL']['currency']] 
    account_info['sma-ratio'] = account_info['sma'] / max(max(1, account_info['net']), account_info['market-value']) * 100
    account_info['txn-fee-ratio'] = account_info['txn-fee'] / max(max(1.0, account_info['net']), account_info['market-value']) * 1000
    account_info['leverage'] = 100.0 * account_info['market-value'] / max(1, account_info['net'])
    account_info['IRR'] = GetIRR(account_info['net'], account_info['cash-flow']) * 100
    account_info['buying-power-percent'] = account_info['buying-power'] / max(1, account_info['net'])
    account_info['buying-power-percent-all'] = ex_rate * account_info['buying-power'] / max(1, ACCOUNT_INFO['ALL']['net'])
    for ticker, value in account_info['holding-value'].items():
      account_info['holding-percent'][ticker] = value / max(1, account_info['net'])
      account_info['holding-percent-all'][ticker] = ex_rate * value / max(1, ACCOUNT_INFO['ALL']['net'])
    sys.stderr.write('%s\n'%(str(account_info)))

  PrintTableMap(header, records, set(), truncate_float = True, float_precision = 0)
   
def PrintHoldingSecurities():
  stat_records_map = []
  
  summation = {
    'Chg': 0.0,
    'Percent': 0.0,
    'Stock name': 'Summary',
  }
  holding_shares = ACCOUNT_INFO['ALL']['holding-shares']
  holding_value = ACCOUNT_INFO['ALL']['holding-value']
  holding_percent = ACCOUNT_INFO['ALL']['holding-percent-all']
  for ticker, shares in holding_shares.items():
    if shares == 0: continue
    chg = GetMarketPriceChange(ticker)
    currency = STOCK_INFO[ticker]['currency']
    name = STOCK_INFO[ticker]['name']
    record = {
        'Percent': holding_percent[ticker],
        'Shares': shares,
        'MV': str(myround(holding_value[ticker] * EX_RATE[CURRENCY + '-' + currency] / 1000.0, 0)) + 'K',
        'Currency': currency,
        'Chg': chg,
        'Stock name': name + '(' + ticker + ')',
    }
    stat_records_map.append(record)
  
  for record in stat_records_map:
    summation['Percent'] += record['Percent']
    for col in ['Chg']:
      summation[col] += record['Percent'] * record['Chg']

  stat_records_map.append(summation)
  stat_records_map.sort(reverse = True, key = lambda record: record.get('Percent', 0))

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
    'Stock name',
  ]
  PrintTableMap(table_header, stat_records_map, truncate_float = False)

def RunStrategies():
  for name, strategy in STRATEGY_FUNCS.items():
    sys.stderr.write('Running strategy: %s\n'%(name))
    tip = strategy()
    if tip != '': print bcolors.FAIL + 'ACTION!!! ' + tip + bcolors.ENDC + '\n'

def PrintStocks(names):
  tableMap = []
  header = [col for col in (FINANCIAL_KEYS - set(['name']))]
  header += ['name']
  for code in FINANCAIL_DATA_ADVANCE.keys():
    if any([CODE_TO_NAME[code].find(name) != -1 for name in names]):
      data = dict(FINANCAIL_DATA_ADVANCE[code])
      data['name'] = ('*' if code in ACCOUNT_INFO['ALL']['holding-shares'] else '') + CODE_TO_NAME[code]
      tableMap.append(data)
  tableMap.sort(key = lambda recordMap: recordMap['p/book-value'] if 'p/book-value' in recordMap else 0)
  PrintTableMap(header, tableMap, float_precision = 3, header_transformer = lambda header: header.replace('book-value', 'bv'))

try:
  args = set(sys.argv[1:])
  prices = filter(lambda arg: arg.find('=') != -1, args)
  args = args - set(prices)
  accounts = filter(lambda arg: arg.find('accounts:') == 0, args)
  args = args - set(accounts)
  if len(accounts) > 0:
    accounts = set(accounts[0][len('accounts:'):].split(','))

  target_names = args
  InitAll()
  GetStockPool(GD_CLIENT)

  if len(prices) > 0:
    for pr in prices:
      info = pr.split('=')
      MARKET_PRICE_CACHE[NAME_TO_CODE[info[0]]] = (float(info[1]), 0, 0)
    sys.stderr.write('market data cache = %s\n'%(str(MARKET_PRICE_CACHE)))

  PopulateMacroData()
  GetFinancialData(GD_CLIENT) 
  GetBankData(GD_CLIENT)
  PopulateFinancialData()
  ProcessRecords(ReadRecords(), accounts)
  PrintAccountInfo()
  PrintHoldingSecurities()
  if len(target_names) > 0:
    names = ','.join(target_names).split(',')
    PrintStocks(names)
  if len(accounts) == 0:
    RunStrategies()
except Exception as ins:
  print 'Run time error: ', ins
  traceback.print_exc(file=sys.stdout)
