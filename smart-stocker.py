#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from datetime import timedelta
from datetime import date
from datetime import time
import time
from collections import defaultdict
import urllib2
import traceback
import copy
import re
from os.path import expanduser

from table_printer import *
from smart_stocker_private_data import *
from smart_stocker_public_data import *
from smart_stocker_global import *
from smart_stocker_strategy import *

#--------------Beginning of logic util functions---------------
def GetIRR(market_value, cash_flow_records):
  if len(cash_flow_records) == 0:
    return 0.0
  cash_flow_records.sort()
  low, high = -1.0, 5.0
  day_loan_rate = pow(LOAN_RATE + 1, 1.0 / 365)
  now = date.today()
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
  home = expanduser("~")
  global GD_CLIENT
  GD_CLIENT = LoginMyGoogle(home + '/.smart-stocker-google-email.txt',
                            home + '/.smart-stocker-google-password.txt')

def CalOneStock(records, code, name):
  capital_cost = 0.0
  net_profit = 0.0
  investment = 0.0
  prev_date = date(2000, 1, 1)
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
    currency = record['currency']
    ex_rate = EX_RATE[currency + '-' + CURRENCY]
    trans_date = record['date']
    buy_shares = record['amount']
    origin_price = record['price']
    price = origin_price * ex_rate
    fee = record['commission'] * ex_rate
    sum_fee += fee
    value = -price * buy_shares - fee - record['extra'] * ex_rate
    if -1 == record['transection'].find(u'股息'):
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
    record['date'] = date(int(date_str[0:4]), int(date_str[4:6]), int(date_str[6:8]))

  records.sort(key = lambda record: record['date']) 

  all_records = defaultdict(list)
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
        and record['transection'].find(u'股息') == -1
        and last['transection'].find(u'股息') == -1):
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

def PrintHoldingSecurities(all_records):
  global NET_ASSET_BY_CURRENCY
  table_header = [
                  'Percent',
                  'Percent1',
                  'MV(K)',
                  'Chg',
                  'Stock name']
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
    name = name.encode('utf-8') if name is not None else ''
    # All in CURRENCY
    (net_profit, capital_cost, remain_stock, dtp, dt, txn_fee, currency, function, division) = CalOneStock(
     all_records[key], key, name)
    if key in TOTAL_INVESTMENT:
      TOTAL_CAPITAL[currency] += -net_profit
      continue
    function_html += function
    div_html += division
    investment = -net_profit
    TOTAL_INVESTMENT[currency] += investment
    TOTAL_TRANSACTION_FEE[currency] += txn_fee
    ex_rate = EX_RATE[currency + '-' + CURRENCY]
    mp, chg, mp_pair_rmb, mv, = 0.0001, 0, 1, 0
    if remain_stock != 0:
      mp = GetMarketPrice(key)
      chg = GetMarketPriceChange(key)
      mp_pair_rmb = mp * ex_rate
      mv = mp * remain_stock * ex_rate
      if key in AH_PAIR:
        mp_pair_rmb = GetMarketPriceInBase(AH_PAIR[key])
    TOTAL_MARKET_VALUE[currency] += mv
    sys.stderr.write('%s profit %.0f %s from %s\n'%(
      'Realized' if remain_stock == 0 else 'Unrealized',
      net_profit + mv,
      CURRENCY, name))
    HOLDING_SHARES[key] = remain_stock
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
    dt['usd'] += dt['yen']
  
  capital_header = ['Currency', 'Market Value', 'Free Cash', 'Net', 'Cash',
                    'Transaction Fee', 'Max Decline', 'IRR']
  capital_table_map = []
  # All are in CURRENCY
  cash_flow = defaultdict(list)
  for key in all_records.keys():
    for record in all_records[key]:
      currency = record['currency']
      ex_rate = EX_RATE[currency + '-' + CURRENCY]
      trans_date = record['date']
      fee = record['commission'] * ex_rate
      buy_shares = record['amount']
      price = record['price'] * ex_rate
      value = -price * buy_shares - fee - record['extra'] * ex_rate
      cash_flow[currency].append([trans_date, key, value]);
  
  cash_flow['usd'] += cash_flow['hkd']
  cash_flow['usd'] += cash_flow['yen']
  
  for dt in [TOTAL_MARKET_VALUE, TOTAL_CAPITAL,
             TOTAL_INVESTMENT, TOTAL_TRANSACTION_FEE]:
    dt['ALL'] = dt['usd'] + dt['rmb']
    dt['rmb'] *= EX_RATE[CURRENCY + '-rmb']
    dt['usd'] *= EX_RATE[CURRENCY + '-usd']

  cash_flow['ALL'] = copy.deepcopy(cash_flow['usd'] + cash_flow['rmb'])
  for record in cash_flow['rmb']:
    record[2] *= EX_RATE[CURRENCY + '-rmb']
  for record in cash_flow['usd']:
    record[2] *= EX_RATE[CURRENCY + '-usd']
  
  for currency in ['usd', 'rmb', 'ALL']:
    NET_ASSET_BY_CURRENCY[currency] = TOTAL_MARKET_VALUE[currency] + TOTAL_CAPITAL[currency] - TOTAL_INVESTMENT[currency]
    capital_table_map.append(
        {
        'Currency': currency,
        'Market Value': str(myround(TOTAL_MARKET_VALUE[currency] / 1000, 0)) + 'K',
        'Cash': str(myround(TOTAL_CAPITAL[currency] / 1000, 0)) + 'K',
        'Investment': str(myround(TOTAL_INVESTMENT[currency] / 1000, 0)) + 'K',
        'Free Cash': str(myround((TOTAL_CAPITAL[currency] - TOTAL_INVESTMENT[currency]) / 1000, 0)) + 'K',
        'Transaction Fee': str(myround(TOTAL_TRANSACTION_FEE[currency] / 100.0, 0)) + 'h(' +
          str(myround(100.0 * TOTAL_TRANSACTION_FEE[currency] / NET_ASSET_BY_CURRENCY[currency], 2)) + '%)',
        'Max Decline': str(myround((TOTAL_MARKET_VALUE[currency] + 2 * TOTAL_CAPITAL[currency] - 2 * TOTAL_INVESTMENT[currency]) * 100.0 / max(1, TOTAL_MARKET_VALUE[currency]), 0)) + '%',
        'IRR': str(myround(GetIRR(TOTAL_MARKET_VALUE[currency], cash_flow[currency]) * 100, 2)) + '%',
        'Net': str(myround((TOTAL_MARKET_VALUE[currency] + TOTAL_CAPITAL[currency] - TOTAL_INVESTMENT[currency]) / 1000, 0)) + 'K',
        }
    )
  NET_ASSET = TOTAL_MARKET_VALUE['ALL'] + TOTAL_CAPITAL['ALL'] - TOTAL_INVESTMENT['ALL']
  
  PrintTableMap(capital_header, capital_table_map, set(), truncate_float = False)
  for col in ['Chg', 'Percent']:
    summation[col] = 0.0
  for record in stat_records_map:
    HOLDING_PERCENT[record['Code']] = 1.0 * record['MV'] / NET_ASSET
    summation['Percent'] += HOLDING_PERCENT[record['Code']]
    record['Percent'] = str(myround(HOLDING_PERCENT[record['Code']] * 100, 1)) + '%'
    currency = 'rmb' if record['currency'] == 'rmb' else 'usd'
    record['Percent1'] = str(myround(100.0 * record['MV'] * EX_RATE[CURRENCY + '-' + currency] / NET_ASSET_BY_CURRENCY[currency], 1)) + '%'
    for col in ['Chg']:
      summation[col] += HOLDING_PERCENT[record['Code']] * record[col]
  for col in ['Chg']:
    summation[col] = round(summation[col], 2)
  summation['Percent'] = str(round(summation['Percent'] * 100, 0)) + '%'
  stat_records_map.append(summation)
  stat_records_map.sort(reverse = True, key = lambda record: record.get('MV', 0))
  PrintTableMap(table_header, stat_records_map, silent_column, truncate_float = False)
  if 'chart' in set(sys.argv):
    open('/tmp/charts.html', 'w').write(
      HTML_TEMPLATE%(function_html, div_html) 
    )

def RunStrategies():
  for strategy in STRATEGY_FUNCS:
    strategy()

def PrintStocks(names):
  tableMap = []
  header = [col for col in (SHOW_KEYS - set(['name']))]
  header += ['name']
  for code in FINANCAIL_DATA.keys():
    data = FINANCAIL_DATA[code]
    if any([data['name'].find(name) != -1 for name in names]):
      tableMap.append(data)
  PrintTableMap(header, tableMap)

try:
  InitAll()
  GetStockPool(GD_CLIENT)
  GetFinancialData(GD_CLIENT) 
  PopulateFinancialData()
  if len(sys.argv) > 1:
    names = ','.join(sys.argv[1:]).split(',')
    PrintStocks(names)
  else:
    PrintHoldingSecurities(ReadRecords())
  RunStrategies()
except Exception as ins:
  print 'Run time error: ', ins
  traceback.print_exc(file=sys.stdout)
