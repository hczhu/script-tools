#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from datetime import timedelta
from datetime import date
from datetime import time
from collections import defaultdict
import urllib2

def GetValueFromUrl(url, feature_str, end_str, func, header = {}):
  try:
    request=urllib2.Request(url, headers=header)
    content=urllib2.urlopen(request).read()
    for fs in feature_str:
      content = content[len(fs) + content.find(fs):]
    return func(content[0:content.find(end_str)])
  except Exception, e:
    sys.stderr.write('Exception ' + str(e) +'\n')
    sys.stderr.write('Failed to open url: ' + url + '\n')
    return func('0.1')

def GetETFBookValue_02822():
  return GetValueFromUrl(
    'http://www.csop.mdgms.com/iopv/nav.html?l=tc',
    ['即日估計每基金單位資產淨值', '<td id="nIopvPriceHKD">'],
    '</td>',
    float,
    {})

CURRENCY = 'RMB'

MAX_OFFSET_PERCENT = 0.1
TARGET_MARKET_VALUE = {
    # 风险！不可能完全了解每个公司内部。
    # 目前单指股票投资额不超过24万。
    # 300ETF,融资买入，考虑买入杠杆基金。
    '510300' : 300000,
    # 招商银行，相对H股有较大折价，服务和口碑。
    '600036' : 300000,
    # 兴业银行
    '601166' : 300000,
    # 民生银行
    '600016' : 1000,
    # 浦发银行
    '600000' : 50000,
    # 民生银行H股，相对A股有较大折价。
    '01988' : 300000,
    # 金融ETF，银行开始差异化竞争，行业整体走下坡路，需要选择竞争力强的银行.
    # 少量头寸作为机动资金，随时不计成本卖出
    '510230' : 10000,
    # 中国平安，观察仓位，需要理解保险业务，所谓牛市的放大器。
    '601318' : 10000,
    'FB' : 300000,
    # 农业银行，财报较好，在年报前低点买入
    '601288' : 100000,
    # 中行转债，相当于先进仓位，银行股大跌是卖出补仓
    '113001' : 300000,
}

WATCH_LIST_STOCK = {
  '01398' : '工商银行H',
  '01288' : '农业银行H',
  '03988' : '中国银行H',
  '00939' : '建设银行H',
  '03968' : '招商银行H',
  '01988' : '民生银行H',
  '600015' : '民生银行',
  '600000' : '浦发银行',
  '601328' : '交通银行',
}

WATCH_LIST_CB = {
}

EX_RATE = {
  'RMB-RMB' : 1.0,
  'HKD-RMB' : 0.78,
  'USD-RMB' : 6.05,
  'YEN-RMB' : 0.06,
}

MIN_HOLD_RATIO = 0.5
NO_RISK_RATE = 0.10
if len(sys.argv) > 1:
  NO_RISK_RATE = float(sys.argv[1]) / 100.0
LOAN_RATE = 0.016

WATCH_LIST_ETF = {
  #南方A50 ETF
  # http://www.csopasset.com/tchi/products/china_A50_etf.php
  '02822' : (GetETFBookValue_02822, '南方A50'),
  '510300': None,
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

EPS = {
  #金融ETF. From http://www.csindex.com.cn/sseportal/csiportal/indexquery.do
  '510230' : 3.119 / 7.10,
  # 300ETF. From http://www.csindex.com.cn/sseportal/csiportal/indexquery.do
  '510300' : 2.289 / 10.06,
  #南方A50ETF，数据来自sse 50ETF统计页面
  # http://www.sse.com.cn/market/sseindex/indexlist/indexdetails/indexturnover/index.shtml?FUNDID=000016&productId=000016&prodType=4&indexCode=000016
  '02822' : 8.743 / 8.11,
  # 来自DeNA 2013H1财报估计
  '2432' : 199.51 * 4 / 3,
}

# The portion of EPS used for dividend.
DR = {
  # Apple once a quarter.
  # 20140206 - 3.05
  'AAPL' : 3.05 * 4,
  # :DeNA once a year.
  # 20140327 - 40.0
  '2432' : 40.0,
}

# Sales per share.
SPS = {
  # 来自DeNA 2013H1财报估计
  '2432' : 143100 * 10**6 * 4 / 3 / 131402874,
}

# Esitmation at the end of 2013
# 2013H的值加上估计利润
BVPS = {
  # 兴业银行，7月份10送5分红5.7 再乘以估计的ROE
  '601166' : (14.51 * 10 - 5.7)/15 * ( 1 + 0.1),
}

market_price_cache = {
  #'2432' : 2156.0,
}

market_price_func = {
  '2432' : lambda: GetValueFromUrl('http://jp.reuters.com/investing/quotes/quote?symbol=2432.T',
                                   ['<div id="priceQuote">', '<span class="valueContent">'],
                                   '</span>', lambda s: float(s.replace(',', ''))),
}

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

total_capital = defaultdict(int)

total_capital_cost = defaultdict(int)

total_investment = {
  'RMB' : 0, 'USD' : 0, 'HKD' : 0, 'YEN' : 0,
}

total_market_value = defaultdict(int)

def CalOneStock(NO_RISK_RATE, records):
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
      capital_cost  += investment * NO_RISK_RATE / 365 * diff_days
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
    capital_cost  += investment * NO_RISK_RATE / 365 *(date.today() - prev_date).days
  if day_trade_net_shares == 0:
    sum_day_trade_profit += day_trade_profit
    day_trade_time += 1
  return (net_profit, capital_cost, holding_shares, holding_cost, sum_day_trade_profit, day_trade_time, sum_fee)

def myround(x, n):
  if n == 0:
    return int(x)
  return round(x, n)

def myround(x, n):
  if n == 0:
    return int(x)
  return round(x, n)

def GetPE(code, mp):
  if code in EPS:
    return myround(mp / EPS[code], 1)
  return 0.0

def GetPS(code, mp):
  if code in SPS:
    return myround(mp / SPS[code], 1)
  return 0.0

def GetDR(code, mp):
  if code in DR:
    return round(DR[code] / mp, 3)
  return 0.0
  

def GetPB(code, mp):
  if code in BVPS:
    return mp / BVPS[code]
  return 0.0

def PrintOneLine(table_header, col_len, silent_column):
  line = '|'
  for i in range(len(col_len)):
    if table_header[i] in silent_column: continue
    line += '-' * col_len[i] + '|'
  return line

def PrintTable(table_header, records, silent_column):
  col_len = map(len, table_header)
  for cells in records:
    for i in range(len(cells)):
      col_len[i] = max(col_len[i], len(str(cells[i])))
  line = PrintOneLine(table_header, col_len, silent_column)
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

# 'records_map' are an array of map.
def PrintTableMap(table_header, records_map, silent_column):
  records = []
  for r in records_map:
    records.append([r.get(col, '') for col in table_header])
  PrintTable(table_header, records, silent_column)

def GetRealTimeMarketPrice(code):
  url_prefix = 'http://xueqiu.com/S/'
  feature_str = '<div class="currentInfo"><strong data-current="'
  st_prefix = ['SH', 'SZ', '']
  for i in range(1):
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
  return 0.001

def GetMarketPrice(code):
  sys.stderr.write('Getting market price for ' + code + '\n')
  if code in market_price_cache:
    return market_price_cache[code]
  func = lambda: GetRealTimeMarketPrice(code)
  if code in market_price_func:
    func = market_price_func[code] 
  mp = func()
  market_price_cache[code] = mp
  sys.stderr.write('Got market price for ' + code + '\n')
  return mp

def GetMarketPriceInRMB(code):
  mp = GetMarketPrice(code)
  if code.isdigit() and code[0] == '0':
    mp *= EX_RATE['HKD-RMB']
  elif not code.isdigit():
    mp *= EX_RATE['USD-RMB']
  return mp

def GetCurrency(code):
  if code.isdigit() and code[0] == '0':
    return 'HKD'
  elif code.isalpha():
    return 'USD'
  return 'RMB'

def ReadRecords(input):
  all_records = defaultdict(list)
  for line in input:
    cells = line.strip().split(',')
    all_records[cells[2]].append(cells)
  return all_records
#sys.stderr.write('There are ' + str(len(all_records)) + ' records.\n')

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
      if record[1] in total_investment:
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

def PrintHoldingSecurities(all_records):
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
                  'P/S',
                  'P/B',
                  'DR',
                  'AH-discount',
                  'HCPS',
                  'CPS',
                  'Margin',
                  'Stock name']
  silent_column = {
    '#TxN' : 1,
    'TNF' : 1,
    'DTP' : 1,
    '#DT' : 1,
    'CC' : 1,
    'HCPS' : 1,
    'CPS' : 1,
    'NCF' : 1,
    #'Margin' : 1,
    #'HS' : 1,
  }

  stat_records_map = []
  
  summation = {}
  summation['Stock name'] = 'Summary'
  for key in all_records.keys():
    sys.stderr.write('Processing [' + key + ']\n')
    name = all_records[key][0][3]
    currency = all_records[key][0][7]
    # All in CURRENCY
    (net_profit, capital_cost, remain_stock, holding_cps, dtp, dt, txn_fee) = CalOneStock(NO_RISK_RATE, all_records[key])
    if key in total_investment:
      total_capital[currency] += -net_profit
      total_capital_cost[currency] += capital_cost
      continue;
    investment = -net_profit
    total_investment[currency] += investment
    if remain_stock <= 0: continue
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
    total_market_value[currency] += mv
    margin = mv - investment
    margin_lit = str(int((mv - investment + 30)/100)) + 'h(' + str(myround((mp - CPS) / mp * 100, 2)) + '%)'
    record = {
        'MV' : myround(mv, 0),
        'NCF' : myround(net_profit, 0),
        'CC' : myround(capital_cost, 0),
        '#TxN' : len(all_records[key]),
        'TNF' : myround(txn_fee, 0),
        'DTP' : myround(dtp, 0),
        '#DT' : dt,
        'HS' : remain_stock,
        'MP' : str(mp),
        'P/E' : myround(GetPE(key, mp), 2),
        'P/S' : myround(GetPS(key, mp), 2),
        'P/B' : myround(GetPB(key, mp), 2),
        'DR' :  myround(GetDR(key, mp) * 100 , 2),
        'AH-discount' : str(myround(100.0 * (mp_pair_rmb - mp * ex_rate ) / mp / ex_rate, 1)) + '%',
        'HCPS' : myround(holding_cps / ex_rate, 3),
        'CPS' : str(CPS),
        'rMargin' : margin,
        'Margin' : margin_lit,
        'Stock name' : name + '(' + key + ')',
    }
    stat_records_map.append(record)
    for col in ['MV', 'NCF', 'CC', '#TxN', 'TNF', 'DTP', '#DT', 'rMargin']:
      summation[col] = summation.get(col, 0) + record[col]
  
  summation['Margin'] = str(summation['rMargin']) + '(' + str(myround( 100.0 * summation['rMargin'] / -summation['NCF'], 2)) + '%)'
  
  stat_records_map.append(summation)
  stat_records_map.sort(reverse = True, key = lambda record : record.get('MV', 0))
  total_investment['USD'] += total_investment['HKD']
  total_investment['USD'] += total_investment['YEN']
  total_market_value['USD'] += total_market_value['HKD']
  total_market_value['USD'] += total_market_value['YEN']
  
  capital_header = ['Currency', 'Cash', 'Investment', 'Free Cash',
                    'Capital Cost', 'Market Value', 'Max Decline', 'IRR']
  capital_table = []
  # All are in CURRENCY
  cash_flow = defaultdict(list)
  for key in all_records.keys():
    for cell in all_records[key]:
      currency = cell[7]
      ex_rate = EX_RATE[currency + '-' + CURRENCY]
      trans_date = date(int(cell[0][0:4]), int(cell[0][4:6]), int(cell[0][6:8]))
      fee = sum(map(float, cell[6:7])) * ex_rate
      buy_shares = int(cell[5])
      price = float(cell[4]) * ex_rate
      value = -price * buy_shares - fee
      cash_flow[currency].append([trans_date, key, value]);
  
  cash_flow['USD'] += cash_flow['HKD']
  cash_flow['USD'] += cash_flow['YEN']
  
  for currency in ['USD', 'RMB']:
    capital_table.append(
        [
        currency,
        str(myround(total_capital[currency] / 1000, 0)) + 'K',
        str(myround(total_investment[currency] / 1000, 0)) + 'K',
        str(myround((total_capital[currency] - total_investment[currency]) / 1000, 0)) + 'K',
        str(myround(total_capital_cost[currency] / 1000, 0)) + 'K',
        str(myround(total_market_value[currency] / 1000, 0)) + 'K',
        str(myround((total_market_value[currency] + 2 * total_capital[currency] - 2 * total_investment[currency]) * 100.0 / total_market_value[currency], 0)) + '%',
        str(myround(GetIRR(total_market_value[currency],
                           cash_flow[currency]) * 100, 2)) + '%',
      ]
    )
  PrintTable(capital_header, capital_table, silent_column)
  PrintTableMap(table_header, stat_records_map, silent_column)

def PrintWatchedETF():
  table_header = ['Price',
                  'Real Value',
                  'Discount',
                  'P/E',
                  'Stock name']
  table = []
  for code in WATCH_LIST_ETF.keys():
    if WATCH_LIST_ETF[code] != None:
      price, real_value = GetMarketPrice(code), WATCH_LIST_ETF[code][0]()
      table.append([price, real_value,
        str(myround((real_value - price) * 100 / real_value, 0)) + '%',
        GetPE(code, price),
        WATCH_LIST_ETF[code][1]])
  PrintTable(table_header, table, [])

def PrintWatchedStocks():
  table_header = ['MP',
                  'P/E',
                  'P/B',
                  'P/S',
                  'DR',
                  'AH-discount',
                  'Stock name']
  table = []
  for code in WATCH_LIST_STOCK.keys():
    mp = GetMarketPrice(code)
    record = {
      'MP' : mp,
      'P/E' : myround(GetPE(code, mp), 2),
      'P/S' : myround(GetPS(code, mp), 2),
      'P/B' : myround(GetPB(code, mp), 2),
      'DR' :  myround(GetDR(code, mp) * 100 , 2),
      'Stock name' : WATCH_LIST_STOCK[code] + '(' + code + ')',
    }
    if code in AH_PAIR:
      currency = GetCurrency(code)
      ex_rate = EX_RATE[currency + '-' + 'RMB']
      mp_pair_rmb = GetMarketPriceInRMB(AH_PAIR[code])
      record['AH-discount'] = str(myround(100.0 * (mp_pair_rmb - mp * ex_rate ) / mp / ex_rate, 1)) + '%'
    table.append(record)
  PrintTableMap(table_header, table, [])

PrintWatchedETF()

PrintWatchedStocks()

PrintHoldingSecurities(ReadRecords(sys.stdin))
