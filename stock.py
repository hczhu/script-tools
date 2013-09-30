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
    trans_date = date(int(cell[0][0:4]), int(cell[0][4:6]), int(cell[0][6:8]))
    fee = sum(map(float, cell[9:14]))
    sum_fee += fee
    buy_shares = int(cell[6])
    flow_in = 0
    if buy_shares != 0:
      flow_in = -abs(buy_shares) / buy_shares
    value = flow_in * float(cell[7]) - fee
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
#  print 'Net cash flow: %f\nCapital cost: %f\nInvestment: %f\n\
#  Remaining stock shares: %d\nCost per share: %f'\
#      %(net_profit,
#        capital_cost,
#        investment,
#        remain_stock,
#        (capital_cost + investment) / max(1, remain_stock))

table_header = ['MV', 'NCF', 'CC', '#TxN', 'TNF', 'DTP', '#DT',
                'HS', 'MP', 'P/E', 'P/B',
                'A2H-PR', 'HCPS',
                'CPSCC(CPS)',
                'Margin', 'Stock name']
silent_column = {
  '#TxN' : 1,
  'TNF' : 1,
  'DTP' : 1,
  '#DT' : 1,
  'CC' : 1,
  #'HCPS' : 1,
  'CPSCC(CPS)' : 1,
}
FROZEN_FREE_CASH = 80000
R = 0.05
if len(sys.argv) > 1:
  R = float(sys.argv[1]) / 100.0
HK2RMB = 0.79
MAX_MARKET_VAELUE = 360000

A2H_code = {
    '600036' : '03968',
    '601988' : '03988',
    '600016' : '01988',
    '601939' : '00939',
    '601398' : '01398',
}

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
    '600036' : 10.6,
}

def GetMarketPrice(code):
  mp = GetRealTimeMarketPrice(code)
  if mp < 0.1 and code in market_price_cache:
    mp = market_price_cache[code]
  return mp

all_records = defaultdict(list)
for line in sys.stdin:
  cells = line.strip().split(',')
  all_records[cells[4] + ',' + cells[3]].append(cells)
  ctime = map(int, cells[1].split(':'))
  cells[1] = time(ctime[0], ctime[1], ctime[2]).isoformat()
#sys.stderr.write('There are ' + str(len(all_records)) + ' records.\n')

stat_records = []

summation = [0] * (len(table_header) - 1)
summation.append('Summary')

ignored_keys = {
  #'511880' : 1,
  '513100' : 1,
  #'601988' : 1,
  '511990' : 1,
  '511010' : 1,
  '113001' : 1,
  '601318' : 1,
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

total_capital = 0

for key in all_records.keys():
  sys.stderr.write('Processing [' + key + ']\n')
  if len(key.split(',')) < 2: continue
  code = key.split(',')[1]
  if code == '':
    for cells in all_records[key]:
      total_capital += float(cells[14])
    continue
  if code in skipped_keys:
    continue
  (net_profit, capital_cost, remain_stock, holding_cps, dtp, dt, txn_fee) = CalOneStock(R, all_records[key])
  investment = -net_profit
  mp, mp_hk, mv, CPS, CPSCC, change_rate, margin = 1, 1, 0, 0, 0, '', 0
  if code not in ignored_keys:
    mp = GetMarketPrice(code)
    mp_hk = mp
    if code in A2H_code:
      mp_hk = GetMarketPrice(A2H_code[code]) * HK2RMB
  if remain_stock > 0 :
    mv = mp * remain_stock
    CPS = myround(investment / remain_stock, 3)
    CPSCC = myround((investment + capital_cost) / remain_stock, 3)
    change_rate = '(' + str(myround((mp - holding_cps) / holding_cps * 100, 2)) + '%)'
  margin = str(int((mv - investment - capital_cost + 30)/100)) + 'h(' + str(myround((mp - CPSCC) / mp * 100, 2)) + '%)'
  record = [myround(mv, 0), myround(net_profit, 0),
            myround(capital_cost, 0), len(all_records[key]), myround(txn_fee, 0),
            myround(dtp, 0), dt,
            remain_stock,
            str(mp), #+ change_rate,
            myround(GetPE(code, mp), 2),
            myround(GetPB(code, mp), 2),
            str(myround(100.0 * (mp - mp_hk) / mp_hk, 1)) + '%',
            myround(holding_cps, 3),
            str(CPSCC), #+ '(' + str(CPS) + ')',
            margin,
            key]
  for i in range(7): summation[i] += record[i]
  if code not in ignored_keys or remain_stock > 0:
    stat_records.append(record)

summation[14] = str(summation[0] + summation[1] - summation[2]) + '(' + str(myround( 100.0 * (summation[0] + summation[1] - summation[2]) / -summation[1], 2)) + '%)'

stat_records.append(summation)
stat_records.sort(reverse = True)
free_cash = total_capital + summation[1]

print 'Total Capital: %.0fK Free cash: %.0fK Stock ratio: %.0f%% Frozen cash: %.0fK'%(
    myround((total_capital - FROZEN_FREE_CASH) / 1000, 0),
    myround((free_cash - FROZEN_FREE_CASH) / 1000, 0),
    myround(100.0 * (total_capital -  free_cash) / (total_capital - FROZEN_FREE_CASH), 2),
    myround(FROZEN_FREE_CASH / 1000, 0))
print 'Over investment: %.0fK'%(myround((summation[0] - MAX_MARKET_VAELUE) / 1000.0, 0))

PrintTable(table_header, stat_records)

