#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from datetime import timedelta
from datetime import date
from datetime import time
from collections import defaultdict
import urllib2

#----------Beginning of manually upated financial data-------

# 银监会数据
# http://www.cbrc.gov.cn/chinese/home/docViewPage/110009.html
# 2013年
#  不良贷款率 1%
#  拨备覆盖率 300%
#  存贷比 66%
#  年均ROA 1.345%
#  年均ROE 20.5%
#  季度平均杠杆率 15
#  季度净息差 2.57% 2.59% 2.63% 2.68%
#  季度非利息收入占比 23.84% 23.73% 22.46% 21.15%
#  季度成本收入比 29.18% 29.44% 30.21% 32.90%
#  季度大型商业银行不良贷款率 0.98% 0.97% 0.98% 1.00%
#  季度股份制银行不良贷款率 0.77% 0.80% 0.83% 0.86%

# 加权风险资产收益率=净利润/加权风险资产
# 加权风险资产：银行业各类资产风险系数--（现金 证券 贷款 固定资产 无形资产)0% 10% 20% 50% 100%


# Number of total shares
SHARES = {
  # 招商银行，2013年末
  '招商银行': 25219845680,

  #2013年3季度末
  '中国银行': int(189179033607 / 0.6777),

  #2013年3季度末
  '兴业银行': int(3402173769 / 0.1786),
}

# 最大市值估计
CAP = {
}

BVPS1 = {
}

BVPS = {
  # 兴业银行，2013年3季度财报
  '兴业银行': (
              194477 * 10**6
              * (1.0 + 18.0 / 100 / 4) #加上4季度估计利润
              - (532 + 446) * 10**6 #减去商誉和无形资产
              - 1309940 * 10**6 * 1 / 100 #减去估计的不良资产 贷款总额乘以不良率
              ) / SHARES['兴业银行']
              * 0.95, # 激进打折

  # 招商银行, 2013年业绩快报数据
  '招商银行': (
             265872 * 10**6 # 报告值
             - 9598 * 10**6 # 减去商誉
             - 2195807 * 10**6 * 1.0 / 100
             ) / SHARES['招商银行']
             * 1.15, # 品牌溢价

  #中国银行，2013年3季度财报
  '中国银行': (
              (889259 * 10**6)
              * (1.0 + 15.0 / 100 / 4) #加上4季度估计利润
              - (12307 + 1850) * 10**6 #减去商誉和无形资产
              - 75353.74 * 10**8 * (0.02 + 0.08 * 0.15) #减去估计的不良资产，房地产开发贷占8%
              ) / SHARES['中国银行'],
}

# Sales per share.
SPS = {
  # 来自DeNA 2013H1财报估计
  # '2432': 143100 * 10**6 * 4 / 3 / 131402874,
  # Guidance for Full Year Ending March 31, 2014 (2013Q3 report)
  # 打八折
  ':DeNA': 182.6 * 10 ** 9 / 130828462 * 0.8,
}

EPS = {
  #南方A50ETF，数据来自sse 50ETF统计页面
  # http://www.sse.com.cn/market/sseindex/indexlist/indexdetails/indexturnover/index.shtml?FUNDID=000016&productId=000016&prodType=4&indexCode=000016
  '南方A50': 8.3412 / 8.01,
  # 来自DeNA 2013H1财报估计
  # '2432': 199.51 * 4 / 3,
  # 来自DeNA 2013Q3财报估计，打八折
  ':DeNA': 241.34 * 0.8,
  # 招商银行, 2013年业绩快报数据
  # 报告值
  # 乘以报收预测增长
  '招商银行': 51795.0  * 10**6 / SHARES['招商银行'],
  
  # 根据2013年3季报估计
  '中国银行': (
              119768.0 * 10**6
              + 34762 * 10**6 * 1.1 # 加四季度估计
              ) / SHARES['中国银行'],
}

# The portion of EPS used for dividend.
DVPS = {
  # Apple once a quarter.
  # 20140206 - 3.05
  # Tax rate 0.1
  'Apple': 3.05 * 4 * 0.9,
  # :DeNA once a year.
  # For FY2013
  ':DeNA': 37.0 * 0.9,
  # 招商银行, 2013年业绩快报数据
  # 假定30%分红率，税率10%.
  '招商银行': EPS['招商银行'] * 0.3 * 0.9,
  # 过去三年分红率 [0.35, 0.34, 0.36]
  '中国银行': EPS['中国银行'] * 0.35 * 0.9,
}

#----------End of manually upated financial data-------

#----------Beginning of crawler util functions-----------------

def GetValueFromUrl(url, feature_str, end_str, func, throw_exp = True):
  try:
    request=urllib2.Request(url)
    content=urllib2.urlopen(request).read()
    for fs in feature_str:
      content = content[len(fs) + content.find(fs):]
    return func(content[0:content.find(end_str)])
  except Exception, e:
    sys.stderr.write('Exception ' + str(e) +'\n')
    sys.stderr.write('Failed to open url: ' + url + '\n')
    if throw_exp: raise
    return func('0.0')

def GetJapanStockPriceAndChange(code):
  url = 'http://jp.reuters.com/investing/quotes/quote?symbol=%s.T'%(str(code))
  try:
    return (GetValueFromUrl(url, ['<div id="priceQuote">', '<span class="valueContent">'],
                            '</span>', lambda s: float(s.replace(',', ''))),
            GetValueFromUrl(url, ['<div id="percentChange">', '<span class="valueContent"><span class="', '>'],
                            '%', lambda s: float(s.replace(',', ''))))
  except:
    return [float('inf'), 0.0]

#----------End of crawler util functions-----------------

#----------Begining of global variables------------------

CURRENCY = 'RMB'
NO_RISK_RATE = 0.05
LOAN_RATE = 0.016

CODE_TO_NAME = {
}

NAME_TO_CODE = {
}

WATCH_LIST_BANK = {
  '601398': '工商银行',
  '601288': '农业银行',
  '601988': '中国银行',
  '601939': '建设银行',
  '600036': '招商银行',
  '600016': '民生银行',
  '601166': '兴业银行',
  '600000': '浦发银行',
  #'600015': '华夏银行',
  #'601328': '交通银行',
  #'601998': '中信银行',
  #'601818': '光大银行',
}

WATCH_LIST_INSURANCE = {
  '601318': '中国平安',
  '601336': '新华保险',
}

WATCH_LIST_INTERNET = {
  '2432': ':DeNA',
  'FB': 'Facebook',
  'GOOG': 'Google',
  'AAPL': 'Apple',
}

WATCH_LIST_CB = {
}

WATCH_LIST_ETF = {
  #南方A50 ETF
  '02822': '南方A50',
  '510300': 'iShare A50 ETF',
} 

AH_PAIR = {
    '600036': '03968',
    '601988': '03988',
    '600016': '01988',
    '601939': '00939',
    '601398': '01398',
    '601318': '02318',
    '601288': '01288',
    '601998': '00998',
    '601328': '03328',
    '601818': '06818',
    '601336': '01336',
}

CB_INFO = {
}

EX_RATE = {
  'RMB-RMB': 1.0,
  'HKD-RMB': 0.78,
  'USD-RMB': 6.08,
  'YEN-RMB': 0.06,
}

ETF_BOOK_VALUE_FUNC = {
  #南方A50 ETF
  # http://www.csopasset.com/tchi/products/china_A50_etf.php
  '南方A50': lambda: GetValueFromUrl('http://www.csop.mdgms.com/iopv/nav.html?l=tc',
                                      ['即日估計每基金單位資產淨值', '<td id="nIopvPriceHKD">'],
                                      '</td>',
                                      float,
                                      )
}

# In the form of '2432': [price, change].
market_price_cache = {
}

market_price_func = {
  '2432': lambda: GetJapanStockPriceAndChange('2432'),
}

total_capital = defaultdict(int)

total_capital_cost = defaultdict(int)

total_investment = {
  'RMB': 0, 'USD': 0, 'HKD': 0, 'YEN': 0,
}

total_transaction_fee = defaultdict(float)

total_market_value = defaultdict(int) 

holding_percent = defaultdict(float)
NET_ASSET = 0.0

#----------Begining of global variables------------------

#--------------Beginning of logic util functions---------------
def GetCurrency(code):
  if code.isdigit() and code[0] == '0':
    return 'HKD'
  elif code.isalpha():
    return 'USD'
  return 'RMB'

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
  return float('inf')

def GetPS(code, mp):
  if code in SPS:
    return myround(mp / SPS[code], 1)
  return float('inf')

def GetDR(code, mp):
  if code in DVPS:
    return round(DVPS[code] / mp, 3)
  return 0.0
  
def GetPB1(code, mp):
  if code in BVPS1:
    return mp / BVPS1[code]
  return float('inf')

def GetPB(code, mp):
  if code in BVPS:
    return mp / BVPS[code]
  return float('inf')
 
def GetCAP(code, mp):
  if code in CAP:
    return CAP[code]
  return 0

def GetXueqiuUrlPrefix(code):
  currency = GetCurrency(code)
  if currency == 'RMB': return ['SH', 'SZ']
  return ['']

def GetXueqiuMarketPrice(code):
  url_prefix = 'http://xueqiu.com/S/'
  price_feature_str = ['<div class="currentInfo"><strong data-current="']
  price_end_str = '"'
  change_feature_str = ['<span class="quote-percentage">', '(']
  change_end_str = '%)'
  for pr in GetXueqiuUrlPrefix(code):
    url = url_prefix + pr + code
    try:
      price = GetValueFromUrl(url, price_feature_str, price_end_str, float)
      change = GetValueFromUrl(url, change_feature_str, change_end_str, float)
      return [price, change]
    except:
      continue
  return [float('inf'), 0.0]

def GetMarketPrice(code):
  sys.stderr.write('Getting market price for ' + code + '\n')
  if code in market_price_cache:
    return market_price_cache[code][0]
  func = lambda: GetXueqiuMarketPrice(code)
  if code in market_price_func:
    func = market_price_func[code] 
  try:
    mp = func()
    market_price_cache[code] = mp
    sys.stderr.write('Got market price for ' + code + '\n')
    return mp[0]
  except:
    return 0.0

def GetMarketPriceChange(code):
  if code not in market_price_cache:
    GetMarketPrice(code)
  if code in market_price_cache:
    return market_price_cache[code][1]
  return 0.0

def GetMarketPriceInRMB(code):
  mp = GetMarketPrice(code)
  if code.isdigit() and code[0] == '0':
    mp *= EX_RATE['HKD-RMB']
  elif not code.isdigit():
    mp *= EX_RATE['USD-RMB']
  return mp

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

def GetAHDiscount(code, mp = 0):
  if code not in AH_PAIR:
     return 0
  mp_rmb, mp_pair_rmb = GetMarketPriceInRMB(code), GetMarketPriceInRMB(AH_PAIR[code])
  return (mp_pair_rmb - mp_rmb) / mp_rmb

FINANCIAL_FUNC = {
  'P/E': GetPE,
  'P/B': GetPB,
  'P/S': GetPS,
  'CAP': GetCAP,
  'AHD': GetAHDiscount,
  'DR': GetDR,
}

#--------------End of logic util functions---------------

#--------------Beginning of print functions-------------

def PrintOneLine(table_header, col_len, silent_column):
  silent_column = set(silent_column)
  line = '|'
  for i in range(len(col_len)):
    if table_header[i] in silent_column: continue
    line += '-' * col_len[i] + '|'
  return line

def PrintTable(table_header, records, silent_column):
  silent_column = set(silent_column)
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

#--------------End of print functions-------------

#--------------Beginning of strategy functions-----

def GenericDynamicStrategy(code, indicator,
                           indicator_range,
                           percent_range,
                           percent_delta = 0.015,
                           buy_condition = lambda code: True,
                           sell_condition = lambda code: True):
  mp = GetMarketPrice(code)
  mp_rmb = GetMarketPriceInRMB(code)
  indicator_value = FINANCIAL_FUNC[indicator](code, mp)
  target_percent = (percent_range[1] - percent_range[0]) * (indicator_value - indicator_range[0]) / (
                    indicator_range[1] - indicator_range[0]) + percent_range[0]
  target_percent = max(0.0, target_percent)
  current_percent = holding_percent[code]
  if code in AH_PAIR:
    current_percent += holding_percent[AH_PAIR[code]]
  percent = target_percent - current_percent
  if (percent > percent_delta and buy_condition(code)) or (
      percent < -percent_delta and sell_condition(code)):
    percent = min(percent_delta, abs(percent)) * percent / abs(percent)
    return 'Buy %s %d units @%.2f change: %.1f%% due to %s = %.3f. Target: %.1f%% current: %.1f%%'%(
      CODE_TO_NAME[code],
      int(NET_ASSET * percent / mp_rmb),
      mp,
      GetMarketPriceChange(code), indicator, indicator_value,
      target_percent * 100, current_percent * 100)
  return '';
  
def BuyApple():
  return GenericDynamicStrategy(
    NAME_TO_CODE['Apple'],
    'DR', [0.0183, 0.03],
    [0, 0.4],
    buy_condition = lambda code: GetMarketPriceChange(code) <= 0);
  
def BuyBig4BanksH():
  codes = map(lambda name: NAME_TO_CODE[name],
              [
               '中国银行H',
               '工商银行H',
               '建设银行H',
               '农业银行H',
              ])
  discount, buy = -1, ''
  for code in codes:
    dis = GetAHDiscount(code)
    changeH = GetMarketPriceChange(code)
    change = GetMarketPriceChange(AH_PAIR[code])
    if dis > discount and changeH < change and GetPB(code, GetMarketPrice(code)) < 1.0:
      discount = dis
      buy = code
  if discount > 0.0:
    return '%s @%.2f AH discount=%.1f%%'%(CODE_TO_NAME[buy], GetMarketPrice(buy), discount * 100.0)
  return ''

def BuyCMBH():
  code = NAME_TO_CODE['招商银行H']
  dis, changeH, change = GetAHDiscount(code), GetMarketPriceChange(code), GetMarketPriceChange(AH_PAIR[code])
  if dis > -0.01 and changeH < change:
    return '@%.2f AH discount=%.1f%%'%(GetMarketPrice(code), dis * 100)
  return ''

def BuyCMB():
  return GenericDynamicStrategy(
    NAME_TO_CODE['招商银行'],
    'P/B', [1.1, 0.7],
    [0., 0.5],
    buy_condition = lambda code: GetAHDiscount(code) >= 0 and GetMarketPriceChange(code) < 0);

def BuyDeNA():
  return GenericDynamicStrategy(
    NAME_TO_CODE[':DeNA'],
    'P/S', [1.9, 1],
    [0.0, 0.2],
    buy_condition = lambda code: GetMarketPriceChange(code) < 0.0);

def BuyMSBH():
  return GenericDynamicStrategy(
    NAME_TO_CODE['民生银行H'],
    'AHD', [0.20, 0.40],
    [0., 0.4],
    buy_condition = lambda code: GetMarketPriceChange(code) < 0.0);

def BuyA50():
  return GenericDynamicStrategy(
    NAME_TO_CODE['南方A50'],
    'P/E', [9, 6],
    [0, 0.80],
    buy_condition = lambda code: GetMarketPriceChange(code) < 0.0);

def BuyCIB():
  return GenericDynamicStrategy(
    NAME_TO_CODE['兴业银行'],
    'P/B', [1.1, 0.7],
    [0, 0.4],
    buy_condition = lambda code: GetMarketPriceChange(code) < 0.0);
  
STRATEGY_FUNCS = {
  BuyApple: '',
  BuyBig4BanksH: 'Buy 四大行H股 ',
  BuyDeNA:  '',
  BuyCMBH:  'Buy 招商银行H ',
  BuyCMB:  '',
  BuyMSBH: '',
  BuyCIB: '',
}

#--------------End of strategy functions-----

def InitAll():
  for pr in EX_RATE.keys():
    currencies = pr.split('-')
    assert(len(currencies) == 2)
    EX_RATE[currencies[1] + '-' + currencies[0]] = 1.0 / EX_RATE[pr]

  for key in AH_PAIR.keys():
    AH_PAIR[AH_PAIR[key]] = key

  for dt in [WATCH_LIST_BANK, WATCH_LIST_INSURANCE, WATCH_LIST_INTERNET,
             WATCH_LIST_ETF, WATCH_LIST_CB]:
    for code in dt.keys():
      CODE_TO_NAME[code] = dt[code]
      if code in AH_PAIR:
        CODE_TO_NAME[AH_PAIR[code]] = dt[code] + 'H'.encode('utf-8')

  for code in CODE_TO_NAME.keys():
    NAME_TO_CODE[CODE_TO_NAME[code]] = code

  for dt in [WATCH_LIST_BANK, WATCH_LIST_INSURANCE]:
    keys = dt.keys()
    for code in keys:
      if code in AH_PAIR:
        dt[AH_PAIR[code]] = dt[code] + 'H'.encode('utf-8')

  for dt in [EPS, DVPS, SPS, BVPS, ETF_BOOK_VALUE_FUNC]:
    keys = dt.keys()
    for key in keys:
      dt[NAME_TO_CODE[key]] = dt[key]

  for dt in [EPS, DVPS, SPS, BVPS]:
    for key in dt.keys():
      if key in AH_PAIR:
        dt[AH_PAIR[key]] = dt[key] * EX_RATE[GetCurrency(key) + '-' + GetCurrency(AH_PAIR[key])]

  if 'all' in set(sys.argv):
    sys.argv += ['stock', 'hold', 'etf', 'Price']

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

def ReadRecords(input):
  all_records = defaultdict(list)
  for line in input:
    cells = line.strip().split(',')
    all_records[cells[2]].append(cells)
  return all_records

def PrintHoldingSecurities(all_records):
  global NET_ASSET
  table_header = ['MV',
                  'NCF',
                  'CC',
                  '#TxN',
                  'TNF',
                  'DTP',
                  '#DT',
                  'HS',
                  'MP',
                  'Chg',
                  'P/E',
                  'P/S',
                  'P/B',
                  'DR',
                  'AHD',
                  'HCPS',
                  'CPS',
                  'Percent',
                  'Stock name']
  silent_column = [
    #'MV',
    'MP',
    'HS',
    '#TxN',
    'TNF',
    'DTP',
    '#DT',
    'CC',
    'HCPS',
    'CPS',
    'NCF',
  ]
  for col in ['Price']:
    if col not in set(sys.argv):
      silent_column.append(col)

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
    total_transaction_fee[currency] += txn_fee
    ex_rate = EX_RATE[currency + '-' + CURRENCY]
    mp, chg, mp_pair_rmb, mv, CPS, change_rate = 0.0001, 0, 1, 0, 0, ''
    if remain_stock > 0 :
      mp = GetMarketPrice(key)
      chg = GetMarketPriceChange(key)
      mp_pair_rmb = mp * ex_rate
      mv = mp * remain_stock * ex_rate
      CPS = myround(investment / ex_rate / remain_stock, 3)
      change_rate = '(' + str(myround((mp - holding_cps) / holding_cps * 100, 2)) + '%)'
      if key in AH_PAIR:
        mp_pair_rmb = GetMarketPriceInRMB(AH_PAIR[key])
    total_market_value[currency] += mv
    record = {
        'Code': key,
        'MV': myround(mv, 0),
        'Price': mp,
        'Chg': round(chg, 2),
        'NCF': myround(net_profit, 0),
        'CC': myround(capital_cost, 0),
        '#TxN': len(all_records[key]),
        'TNF': myround(txn_fee, 0),
        'DTP': myround(dtp, 0),
        '#DT': dt,
        'HS': remain_stock,
        'MP': str(mp),
        'P/E': myround(GetPE(key, mp), 2),
        'P/S': myround(GetPS(key, mp), 2),
        'P/B': myround(GetPB(key, mp), 2),
        'DR':  myround(GetDR(key, mp) * 100 , 2),
        'AHD': str(myround(100.0 * (mp_pair_rmb - mp * ex_rate ) / mp / ex_rate, 1)) + '%',
        'HCPS': myround(holding_cps / ex_rate, 3),
        'CPS': str(CPS),
        'Stock name': name + '(' + key + ')',
    }
    for col in ['MV', 'NCF', 'CC', '#TxN', 'TNF', 'DTP', '#DT']:
      summation[col] = summation.get(col, 0) + record[col]
    if remain_stock > 0:
      stat_records_map.append(record)
  
  total_investment['USD'] += total_investment['HKD']
  total_investment['USD'] += total_investment['YEN']
  total_market_value['USD'] += total_market_value['HKD']
  total_market_value['USD'] += total_market_value['YEN']
  total_transaction_fee['USD'] += total_transaction_fee['HKD']
  total_transaction_fee['USD'] += total_transaction_fee['YEN']
  
  capital_header = ['Currency', 'Market Value', 'Cash', 'Investment', 'Free Cash',
                    'Transaction Fee', 'Max Decline', 'IRR']
  capital_table_map = []
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
  
  for dt in [cash_flow, total_market_value, total_capital,
             total_investment, total_transaction_fee]:
    dt['ALL'] = dt['USD'] + dt['RMB']
  
  for currency in ['USD', 'RMB', 'ALL']:
    capital_table_map.append(
        {
        'Currency': currency,
        'Market Value': str(myround(total_market_value[currency] / 1000, 0)) + 'K',
        'Cash': str(myround(total_capital[currency] / 1000, 0)) + 'K',
        'Investment': str(myround(total_investment[currency] / 1000, 0)) + 'K',
        'Free Cash': str(myround((total_capital[currency] - total_investment[currency]) / 1000, 0)) + 'K',
        'Transaction Fee': str(myround(total_transaction_fee[currency] / 100.0, 0)) + 'h(' +
          str(myround(100.0 * total_transaction_fee[currency] / total_investment[currency], 2)) + '%)',
        'Max Decline': str(myround((total_market_value[currency] + 2 * total_capital[currency] - 2 * total_investment[currency]) * 100.0 / total_market_value[currency], 0)) + '%',
        'IRR': str(myround(GetIRR(total_market_value[currency], cash_flow[currency]) * 100, 2)) + '%',
        }
    )
  
  PrintTableMap(capital_header, capital_table_map, set())
  NET_ASSET = total_market_value['USD'] + total_market_value['RMB'] + total_capital['USD']  + total_capital['RMB'] - total_investment['USD'] - total_investment['RMB'];
  for col in ['Chg', 'DR']:
    summation[col] = 0.0
  for record in stat_records_map:
    holding_percent[record['Code']] = 1.0 * record['MV'] / NET_ASSET
    record['Percent'] = str(myround(holding_percent[record['Code']] * 100, 1)) + '%'
    for col in ['Chg', 'DR']:
      summation[col] += holding_percent[record['Code']] * record[col]
  for col in ['Chg', 'DR']:
    summation[col] = round(summation[col], 2)
  if 'hold' in set(sys.argv):
    stat_records_map.append(summation)
    stat_records_map.sort(reverse = True, key = lambda record: record.get('MV', 0))
    PrintTableMap(table_header, stat_records_map, silent_column)

def PrintWatchedETF():
  table_header = [
                  'Change',
                  'Real Value',
                  'Discount',
                  'P/E',
                  'Stock name',
                 ]
  table_map = []
  for code in WATCH_LIST_ETF.keys():
    if code in ETF_BOOK_VALUE_FUNC:
      price, change, real_value = GetMarketPrice(code), GetMarketPriceChange(code), ETF_BOOK_VALUE_FUNC[code]()
      table_map.append({
        'Change': str(round(change, 1)) + '%',
        'Real Value': real_value,
        'Discount': str(myround((real_value - price) * 100 / real_value, 0)) + '%',
        'P/E': GetPE(code, price),
        'Stock name': CODE_TO_NAME[code],
      })
  silent = []
  if 'Price' not in set(sys.argv):
    silent += ['Price']
  PrintTableMap(table_header, table_map, silent)

def PrintWatchedStocks(watch_list, table_header, sort_key, rev = False):
  table, silent = [], []
  if 'Price' not in set(sys.argv):
    silent += ['Price']
  for code in watch_list.keys():
    mp = GetMarketPrice(code)
    record = {
              'Stock name': watch_list[code] + ('(' + code + ')').encode('utf-8'),
    }
    for col in table_header:
      if col == 'Change':
        record[col] = str(GetMarketPriceChange(code)) + '%'
      elif col in FINANCIAL_FUNC:
        record[col] = round(FINANCIAL_FUNC[col](code, mp), 2)
    table.append(record)
  table.sort(reverse = rev, key = lambda record: record.get(sort_key, 0))
  PrintTableMap(table_header, table, silent)

def PrintWatchedBank():
  table_header = [
                  'Change',
                  'P/E',
                  'P/B',
                  'DR',
                  'AHD',
                  'Stock name'
                  ]
  PrintWatchedStocks(WATCH_LIST_BANK, table_header, 'P/B')

def PrintWatchedInsurance():
  table_header = [
                  'Change',
                  'P/E',
                  'P/B',
                  'P/S',
                  'DR',
                  'AHD',
                  'Stock name'
                  ]
  PrintWatchedStocks(WATCH_LIST_INSURANCE, table_header, 'P/S')

def PrintWatchedInternet():
  table_header = [
                  'Change',
                  'P/E',
                  'P/S',
                  'CAP',
                  'DR',
                  'Stock name'
                  ]
  PrintWatchedStocks(WATCH_LIST_INTERNET, table_header, 'CAP')

def RunStrategies():
  for strategy in STRATEGY_FUNCS.keys():
    sys.stderr.write("Running straregy: %s\n"%(STRATEGY_FUNCS[strategy]))
    suggestion = strategy()
    if suggestion != '':
      print '%s%s'%(STRATEGY_FUNCS[strategy], suggestion)

try:
  InitAll()
  
  if 'etf' in set(sys.argv):
    PrintWatchedETF()
  
  if 'stock' in set(sys.argv) or 'insurance' in set(sys.argv):
    PrintWatchedInsurance()
  
  if 'stock' in set(sys.argv) or 'internet' in set(sys.argv):
    PrintWatchedInternet()
  
  if 'stock' in set(sys.argv) or 'bank' in set(sys.argv):
    PrintWatchedBank()
  
  PrintHoldingSecurities(ReadRecords(sys.stdin))
  
  RunStrategies()
except Exception as ins:
  print 'Run time error: ', ins
