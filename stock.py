#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from datetime import timedelta
from datetime import date
from datetime import time
from collections import defaultdict
import urllib2

def CalOneStock(R, records):
  capital_cost = 0.0
  net_profit = 0.0
  investment = 0.0
  prev_date = date(2000, 1, 1)
  holding_cost = 0.0
  holding_shares = 0
  records.sort()
  day_trade_profit = 0
  day_trade_net_shares = 0
  sum_day_trade_profit = 0
  day_trade_time = -1
  sum_fee = 0
  for cell in records:
    currency = cell[7]
    ex_rate = EX_RATE[currency + '-' + CURRENCY]
    trans_date = date(int(cell[0][0:4]), int(cell[0][4:6]), int(cell[0][6:8]))
    fee = sum(map(float, cell[6:7])) * ex_rate
    sum_fee += fee
    buy_shares = int(cell[5])
    price = float(cell[4]) * ex_rate
    value = -price * buy_shares - fee
    if investment > 0.0:
      diff_days = (trans_date - prev_date).days
      capital_cost  += investment * R / 365 * diff_days
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
    if buy_shares > 0:
      assert value < 0.0
      holding_cost = (holding_cost * holding_shares - value) / (holding_shares + buy_shares)
    holding_shares += buy_shares
    assert holding_shares >= 0.0
  if investment > 0.0:
    capital_cost  += investment * R / 365 *(date.today() - prev_date).days
  if day_trade_net_shares == 0:
    sum_day_trade_profit += day_trade_profit
    day_trade_time += 1
  return (net_profit, capital_cost, holding_shares, holding_cost, sum_day_trade_profit, day_trade_time, sum_fee)

table_header = ['MV',
                'NCF',
                'CC',
                '#TxN',
                'TNF',
                'DTP',
                '#DT',
                'HS',
                'MP',
                'P/E',
                'P/B',
                'A2H-PR',
                'HCPS',
                'CPS',
                'Margin',
                'Overflow',
                'Stock name']
silent_column = {
  '#TxN' : 1,
  'TNF' : 1,
  'DTP' : 1,
  '#DT' : 1,
  'CC' : 1,
  #'HCPS' : 1,
  'CPS' : 1,
  'NCF' : 1,
  #'Margin' : 1,
  'HS' : 1,
}

FROZEN_FREE_CASH = 0
R = 0.05
if len(sys.argv) > 1:
  R = float(sys.argv[1]) / 100.0

EX_RATE = {
  'RMB-RMB' : 1.0,
  'HKD-RMB' : 0.79,
  'USD-RMB' : 6.09,
}

CURRENCY = 'RMB'

MAX_OFFSET_PERCENT = 0.1
TARGET_MARKET_VALUE = {
    # 300ETF,融资买入，考虑买入杠杆基金。
    '510300' : 300000,
    # 招商银行，相对H股有较大折价
    '600036' : 200000,
    # 兴业银行
    '601166' : 160000,
    # 民生银行
    '600016' : 1000,
    # 浦发银行
    '600000' : 20000,
    # 民生银行H股，相对A股有较大折价。
    '01988' : 200000,
    # 金融ETF，银行开始差异化竞争，行业整体走下坡路，需要选择竞争力强的银行.
    # 少量头寸作为机动资金，随时不计成本卖出
    '510230' : 10000,
    # 中国平安，观察仓位，需要理解保险业务，所谓牛市的放大器。
    '601318' : 50000,
    # 现金数量
    '' : 600000,
    'FB' : 200000,
}

AH_PAIR = {
    '600036' : '03968',
    '601988' : '03988',
    '600016' : '01988',
    '601939' : '00939',
    '601398' : '01398',
    '601318' : '02318',
    '601288' : '01288',
}
for key in AH_PAIR.keys():
  AH_PAIR[AH_PAIR[key]] = key

# Estimation of 2013
# 统一
EPS = {
    # Finance ETF. From http://www.csindex.com.cn/sseportal/csiportal/indexquery.do
    '510230' : 3.33 / 7.50,
    # 300 ETF. From http://www.csindex.com.cn/sseportal/csiportal/indexquery.do
    '510300' : 2.483 / 10.06,
    # 招商银行
}

# Esitmation at the end of 2013
# 2013H的值加上估计利润
BVPS = {
    # 兴业银行，7月份10送5分红5.7 再乘以估计的ROE
    '601166' : (14.51 * 10 - 5.7)/15 * ( 1 + 0.1),
}

# Earning(net income) growth rate
EGR = {
}

def GetPE(code, mp):
  if code in EPS:
    return mp / EPS[code]
  return 0.0

def GetPB(code, mp):
  if code in BVPS:
    return mp / BVPS[code]
  return 0.0

def myround(x, n):
  if n == 0:
    return int(x)
  return round(x, n)

def PrintOneLine(table_header, col_len):
  line = '|'
  for i in range(len(col_len)):
    if table_header[i] in silent_column: continue
    line += '-' * col_len[i] + '|'
  return line

def PrintTable(table_header, records):
  col_len = map(len, table_header)
  for cells in records:
    for i in range(len(cells)):
      col_len[i] = max(col_len[i], len(str(cells[i])))
  line = PrintOneLine(table_header, col_len)
  header = '+' + line[1:len(line) - 1] + '+'
  print header
  records.insert(0, table_header)
  first = True
  for cells in records:
    assert len(cells) == len(records[0])
    row = '|'
    for i in range(len(cells)):
      if table_header[i] in silent_column: continue
      row += (' ' * (col_len[i] - len(str(cells[i])))) + str(cells[i]) + '|'
    if first: first = False
    else: print line
    print row
  print header

def GetRealTimeMarketPrice(code):
  url_prefix = 'http://xueqiu.com/S/'
  feature_str = '<div class="currentInfo"><strong data-current="'
  st_prefix = ['SH', 'SZ', '']
  for i in range(3):
    for pr in st_prefix:
      url = url_prefix + pr + code
      try:
        content=urllib2.urlopen(url).read()
        pos = content.find(feature_str)
        if pos < 0: continue
        pos += len(feature_str)
        end = content[pos:].find('"') + pos
        if end < 0: continue
        return max(0.001, float(content[pos:end]))
      except:
        continue
      time.sleep(0.3)
  return 0.001

market_price_cache = {
}

def GetMarketPrice(code):
  mp = GetRealTimeMarketPrice(code)
  if mp < 0.1 and code in market_price_cache:
    mp = market_price_cache[code]
  return mp

def GetMarketPriceInRMB(code):
  mp = GetMarketPrice(code)
  if code.isdigit() and code[0] == '0':
    mp *= EX_RATE['HKD-RMB']
  elif not code.isdigit():
    mp *= EX_RATE['USD-RMB']
  return mp

all_records = defaultdict(list)
for line in sys.stdin:
  cells = line.strip().split(',')
  all_records[cells[2]].append(cells)
#sys.stderr.write('There are ' + str(len(all_records)) + ' records.\n')

stat_records = []

summation = [0] * (len(table_header) - 1)
summation.append('Summary')

ignored_keys = {
  #现金流
  '' : 1,
  #'511880' : 1,
  '513100' : 1,
  #'601988' : 1,
  '511990' : 1,
  '511010' : 1,
  '113001' : 1,
  #'601318' : 1,
  '112109' : 1,
  '110023' : 1,
  '' : 1,
}

skipped_keys = {
  '131800' : 1,
  '131810' : 1,
  '204001' : 1,
  '204014' : 1,
  '131809' : 1,
  '660001' : 1,
  '660091' : 1,
  '660063' : 1,
}

total_capital = {
}
total_capital_cost = {
}
total_investment = {
  'RMB' : 0, 'USD' : 0, 'HKD' : 0,
}


for key in all_records.keys():
  sys.stderr.write('Processing [' + key + ']\n')
  name = all_records[key][0][3]
  currency = all_records[key][0][7]
  # All in CURRENCY
  (net_profit, capital_cost, remain_stock, holding_cps, dtp, dt, txn_fee) = CalOneStock(R, all_records[key])
  if key in total_investment:
    # 现金流
    total_capital[currency] = -net_profit
    total_capital_cost[currency] = capital_cost
    continue
  investment = -net_profit
  total_investment[currency] += investment
  ex_rate = EX_RATE[currency + '-' + CURRENCY]
  mp, mp_pair_rmb, mv, CPS, change_rate, margin = 1, 1, 0, 0, '', 0
  mp = GetMarketPrice(key)
  mp_pair_rmb = mp * ex_rate
  if key in AH_PAIR:
    mp_pair_rmb = GetMarketPriceInRMB(AH_PAIR[key])
  if remain_stock > 0 :
    mv = mp * remain_stock * ex_rate
    CPS = myround(investment / ex_rate / remain_stock, 3)
    change_rate = '(' + str(myround((mp - holding_cps) / holding_cps * 100, 2)) + '%)'
  target_market_value = 1
  if key in TARGET_MARKET_VALUE:
    target_market_value = TARGET_MARKET_VALUE[key]
  margin = str(int((mv - investment + 30)/100)) + 'h(' + str(myround((mp - CPS) / mp * 100, 2)) + '%)'
  overflow = mv - target_market_value
  record = [myround(mv, 0), myround(net_profit, 0),
            myround(capital_cost, 0), len(all_records[key]), myround(txn_fee, 0),
            myround(dtp, 0), dt,
            remain_stock,
            str(mp), #+ change_rate,
            myround(GetPE(key, mp), 2),
            myround(GetPB(key, mp), 2),
            str(myround(100.0 * (mp_pair_rmb - mp * ex_rate) / mp / ex_rate, 1)) + '%',
            myround(holding_cps / ex_rate, 3),
            str(CPS),
            margin,
            str(myround(overflow / 1000, 0)) + 'K(' + str(myround(100.0 * overflow / target_market_value, 0)) + '%)',
            name]
  for i in range(7): summation[i] += record[i]
  summation[15] += int(overflow)
  if key in TARGET_MARKET_VALUE or remain_stock > 0:
    stat_records.append(record)

summation[14] = str(summation[0] + summation[1]) + '(' + str(myround( 100.0 * (summation[0] + summation[1] - summation[2]) / -summation[1], 2)) + '%)'

stat_records.append(summation)
stat_records.sort(reverse = True)
total_investment['USD'] += total_investment['HKD']

capital_header = ['Currency', 'Cash', 'Investment', 'Free Cash', 'Capital Cost']
capital_table = []
for currency in ['USD', 'RMB']:
  capital_table.append(
    [
    currency,
    str(myround(total_capital[currency] / 1000, 0)) + 'K',
    str(myround(total_investment[currency] / 1000, 0)) + 'K',
    str(myround((total_capital[currency] - total_investment[currency]) / 1000, 0)) + 'K',
    str(myround(total_capital_cost[currency] / 100, 0)) + 'H',
    ]
  )
PrintTable(capital_header, capital_table)
PrintTable(table_header, stat_records)

