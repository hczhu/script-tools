#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from datetime import timedelta
from datetime import date
from datetime import time
from collections import defaultdict
import urllib2
import traceback
import copy

from table_printer import *
from stock_data import *

#----------------------Template-----------------------------

# Number of total shares

FORGOTTEN = {
  # 'Facebook': 0,
}

URL_CONTENT_CACHE = {
}

#----------End of manually upated financial data-------

#----------Beginning of crawler util functions-----------------

# appannie header: User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36

def AppannieScore(company, country = 'japan'):
  url_temp = 'http://www.appannie.com/apps/%s/top/%s/overall/%s'
  urls = [
           url_temp%('ios', country, '?device=iphone'),
           url_temp%('ios', country, '?device=ipad'),
           url_temp%('google-play', country, ''),
         ]
  res = 0
  for url in urls:
    if url not in URL_CONTENT_CACHE:
      request = urllib2.Request(url)
      request.add_header('User-Agent',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36') 
      sys.stderr.write('Getting url: %s\n', url)
      URL_CONTENT_CACHE[url] = urllib2.urlopen(request).read()
    content = URL_CONTENT_CACHE[url]
    idx = content.find(company)
    while idx >= 0:
      content = content[idx + len(company):]
      res += 1
      idx = content.find(company)
  return res
    

def GetValueFromUrl(url, feature_str, end_str, func, throw_exp = True):
  try:
    if url not in URL_CONTENT_CACHE:
      request = urllib2.Request(url)
      URL_CONTENT_CACHE[url] = urllib2.urlopen(request).read()
    content = URL_CONTENT_CACHE[url]
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

def GetJapanStockBeta(code):
  url = 'http://jp.reuters.com/investing/quotes/quote?symbol=%s.T'%(str(code))
  try:
    return GetValueFromUrl(url,
        ['<span id="quoteBeta">'],
         '</span>', lambda s: float(s.replace(',', '')))
  except:
    return 0.0

#----------End of crawler util functions-----------------

#----------Begining of global variables------------------

MAX_PERCENT_PER_STOCK = 0.2

PERCENT_UPPER = {
  '南方A50': 0.5,
  '中国银行': 0.72,
  '建设银行': 0.4,
  '招商银行': 0.40,
}

CURRENCY = 'RMB'
NO_RISK_RATE = 0.05
LOAN_RATE = 0.016

STOCK_BETA = {
  '2432': GetJapanStockBeta,
}

REAL_TIME_VALUE_CACHE = {
}

REALTIME_VALUE_FUNC = {
}

CODE_TO_NAME = {
  'RMB': 'RMB',
  'USD': 'USD',
  'HKD': 'HKD',
}

NAME_TO_CODE = {
}

# In the form of '2432': [price, change, cap].
market_price_cache = {
}

market_price_func = {
  '2432': lambda: GetJapanStockPriceAndChange('2432'),
  'ni225': lambda: [0,
                    GetValueFromUrl('http://www.bloomberg.com/quote/NKY:IND',
                                    ['<meta itemprop="priceChangePercent" content="'],
                                    '"', lambda s: float(s.replace(',', '')))]
}

total_capital = defaultdict(int)

total_capital_cost = defaultdict(int)

total_investment = {
  'RMB': 0, 'USD': 0, 'HKD': 0, 'YEN': 0,
}
net_asset = defaultdict(int)

total_transaction_fee = defaultdict(float)

total_market_value = defaultdict(int) 

holding_percent = defaultdict(float)
NET_ASSET = 0.0

#----------Begining of global variables------------------

#--------------Beginning of logic util functions---------------
def IsLambda(v):
  return isinstance(v, type(lambda: None)) and v.__name__ == (lambda: None).__name__

def GetCurrency(code):
  if code in STOCK_CURRENCY:
    return STOCK_CURRENCY[code]
  elif code.isdigit() and code[0] == '0' and len(code) == 5:
    return 'HKD'
  elif code.isalpha():
    return 'USD'
  elif code.isdigit() and len(code) == 4:
    return 'YEN'
  return 'RMB'

def myround(x, n):
  if n == 0:
    return int(x)
  return round(x, n)

def myround(x, n):
  if n == 0:
    return int(x)
  return round(x, n)

def GetPE0(code, mp):
  return myround(mp / EPS0[code], 1) if code in EPS0 else float('inf')

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
    return round(DVPS[code] / mp * (1.0 - DV_TAX), 3)
  return 0.0

def GetDR0(code, mp):
  if code in DVPS0:
    return round(DVPS0[code] / mp * (1.0 - DV_TAX), 3)
  return 0.0

def GetPB1(code, mp):
  if code in BVPS1:
    return mp / BVPS1[code]
  return float('inf')

def GetBeta(code):
  return STOCK_BETA[code](code) if code in STOCK_BETA else 10

def GetPB0(code, mp):
  if code in BVPS0:
    dilution = 1.0
    if code in CB:
      trans = CB[code][1]
      if trans < BVPS0[code]:
        dilution = (1.0 + CB[code][0] * 1.0 / BVPS0[code] / SHARES[code]) / (
          1.0 + CB[code][0] / trans / SHARES[code])
    book_value = BVPS0[code]() if IsLambda(BVPS0[code]) else BVPS0[code]
    return mp / (book_value * dilution)
  return float('inf')
 
def GetPB(code, mp):
  if code in BVPS:
    dilution = 1.0
    if code in CB:
      trans = CB[code][1]
      if code in DVPS:
        trans -= DVPS[code]
      if trans < BVPS[code]:
        dilution = (1.0 + CB[code][0] * 1.0 / BVPS[code] / SHARES[code]) / (
          1.0 + CB[code][0] / trans / SHARES[code])
    return mp / (BVPS[code] * dilution)
  return float('inf')
 
def GetCAP(code, mp):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  if code in CAP:
    return CAP[code]() if IsLambda(CAP[code]) else CAP[code]
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
  cap_feature_str = ['市值：<span>']
  cap_end_str = '<'
  book_value_str = ['单位净值', '<span>']
  book_value_end_str = '<'
  for pr in GetXueqiuUrlPrefix(code):
    url = url_prefix + pr + code
    try:
      price = GetValueFromUrl(url, price_feature_str, price_end_str, float)
      change = GetValueFromUrl(url, change_feature_str, change_end_str, float)
      cap = GetValueFromUrl(url, cap_feature_str, cap_end_str,
                            lambda s: float(s.replace('亿', '')) * 10**8, False)
      book_value = GetValueFromUrl(url, book_value_str, book_value_end_str, float, False)
      return [price, change, cap, book_value]
    except:
      continue
  return [0.01, 0.0, 0.0, 1.0]

def GetSinaUrlPrefix(code):
  currency = GetCurrency(code)
  if currency == 'RMB': return ['sh', 'sz']
  elif currency == 'HKD': return ['hk']
  elif currency == 'USD': return ['gb_']
  return ['']

def GetMarketPriceFromSina(code):
  url_prefix = 'http://hq.sinajs.cn/list='
  price_end_str = '"'
  for pr in GetSinaUrlPrefix(code):
    suffix = pr + code.lower()
    url = url_prefix + suffix
    try:
      values = GetValueFromUrl(url, 'hq_str_%s="'%(suffix), '"', str)
      if len(values) == 0: continue
      sys.stderr.write('Get string for %s: %s\n'%(code, values))
      values = values.split(',')
      if suffix.find('hk') == 0: values = values[1:]
      price, change, cap, book_value = 0, 0, 0, 1.0
      if suffix.find('gb_') == 0:
        price, change, cap = float(values[1]), myround(float(values[2]), 1), float(values[12])
      elif suffix.find('hk') == 0:
        price, change = float(values[5]), myround(float(values[7]), 1)
      else:
        price = float(values[3])
        prev_price = float(values[2])
        change = myround(100.0 * (price - prev_price) / prev_price, 1)
      data = [price, change, cap, book_value]
      sys.stderr.write('Got market data for %s = %s\n'%(code, str(data)))
      return data
    except:
      continue
  return [0.0, 0.0, 0.0, 0.0]

def GetXueqiuETFBookValue(code):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  return GetXueqiuMarketPrice(code)[3]

def GetMarketPrice(code):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  sys.stderr.write('Getting market price for ' + code + '\n')
  if code in market_price_cache:
    return market_price_cache[code][0]
  func = lambda: GetMarketPriceFromSina(code)
  if code in market_price_func:
    func = market_price_func[code] 
  try:
    data = func()
    market_price_cache[code] = data
    return data[0]
  except:
    sys.stderr.write('Failed to get market price for %s.\n'%(code))
    return 0.0

def GetMarketCap(code):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  if code not in market_price_cache:
    GetMarketPrice(code)
  if code in market_price_cache:
    return market_price_cache[code][2]
  return 0.0

def GetMarketPriceChange(code):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  if code not in market_price_cache:
    GetMarketPrice(code)
  if code in market_price_cache:
    return market_price_cache[code][1]
  return 0.0

def GetMarketPriceInBase(code):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  mp = GetMarketPrice(code)
  currency = GetCurrency(code);
  mp *= EX_RATE[currency + '-' + CURRENCY]
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
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  if code not in AH_PAIR:
     return 0
  mp_base, mp_pair_base = GetMarketPriceInBase(code), GetMarketPriceInBase(AH_PAIR[code])
  return (mp_pair_base - mp_base) / mp_base

def GetRZ(code, mp = 0):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  if GetCurrency(code) != 'RMB': return 0.0
  url_pattern = 'http://data.eastmoney.com/rzrq/detail/%s,1.html'
  try:
    rz = GetValueFromUrl(url_pattern%(code),
                           [
                            '<th>融资余额(元)</th>',
                            '<td class="right">',
                           ],
                           '</td>' , lambda s: int(s.replace(',', '')))
    rq = GetValueFromUrl(url_pattern%(code),
                           [
                            '<th>融资余额(元)</th>',
                            '<td class="right">',
                            '<td class="right">',
                            '<td class="right">',
                            '<td class="right">',
                           ],
                           '</td>' , lambda s: int(s.replace(',', '')))
  except:
    return float('-1')
  return 1.0 * (rz - rq) / RZ_BASE[CODE_TO_NAME[code]] if code in CODE_TO_NAME and CODE_TO_NAME[code] in RZ_BASE else rz - rq

FINANCIAL_FUNC = {
  'P/E0': GetPE0,
  'P/E': GetPE,
  'P/B0': GetPB0,
  'P/B': GetPB,
  'P/S': GetPS,
  'CAP': GetCAP,
  'AHD': GetAHDiscount,
  'DR': GetDR,
  'DR0': GetDR0,
  'MP': lambda code, mp: GetMarketPrice(code),
}

#--------------End of logic util functions---------------

#--------------Beginning of strategy functions-----

def InBetween(value_range, x):
  return (x - value_range[0]) * (x - value_range[1]) <= 0.0

def GenericDynamicStrategy(name,
                           indicator,
                           buy_range,
                           hold_percent_range,
                           sell_point,
                           percent_delta = 0.015,
                           buy_condition = lambda code: True,
                           sell_condition = lambda code: True):
  code = NAME_TO_CODE[name]
  mp = GetMarketPrice(code)
  mp_base = GetMarketPriceInBase(code)
  indicator_value = FINANCIAL_FUNC[indicator](code, mp)
  if InBetween(buy_range, indicator_value):
    target_percent = (hold_percent_range[1] - hold_percent_range[0]) * (indicator_value - buy_range[0]) / (
                    buy_range[1] - buy_range[0]) + hold_percent_range[0]
    target_percent = max(hold_percent_range[0], target_percent)
    target_percent = min(hold_percent_range[1], target_percent)
    current_percent = holding_percent[code]
    percent = target_percent - current_percent
    if percent >= percent_delta and buy_condition(code):
      percent = percent_delta
      return 'Buy %s(%s) %d units @%.2f change: %.1f%% due to %s = %.3f. Target: %.1f%% current: %.1f%%'%(
          CODE_TO_NAME[code], code,
          int(NET_ASSET * percent / mp_base),
          mp,
          GetMarketPriceChange(code), indicator, indicator_value,
          target_percent * 100, current_percent * 100)
  elif InBetween([buy_range[0], indicator_value], sell_point):
    current_percent = holding_percent[code]
    percent = min(current_percent, percent_delta)
    if percent > 0.0 and sell_condition(code):
      return 'Sell %s(%s) %d units @%.2f change: %.1f%% due to %s = %.3f.'%(
          CODE_TO_NAME[code], code,
          int(NET_ASSET * percent / mp_base),
          mp,
          GetMarketPriceChange(code), indicator, indicator_value)
  elif InBetween([buy_range[0], indicator_value], buy_range[1]):
    return 'Extreme price for %s(%s) @%.2f due to %s = %.3f.'%(
      CODE_TO_NAME[code], code,
      mp, indicator, indicator_value)
  return ''

def GenericSwapStrategy(name1, name2,
                        indicator,
                        zero1, fair,
                        percent_delta):
  code1 = NAME_TO_CODE[name1]
  code2 = NAME_TO_CODE[name2]
  mp1 = GetMarketPrice(code1)
  mp2 = GetMarketPrice(code2)
  mp_base1 = GetMarketPriceInBase(code1)
  mp_base2 = GetMarketPriceInBase(code2)
  indicator_value = indicator() if IsLambda(indicator) else \
    FINANCIAL_FUNC[indicator](code1, mp1) / FINANCIAL_FUNC[indicator](code2, mp2)
  holding1 = holding_percent[code1]
  holding2 = holding_percent[code2]
  fair_percent = (holding1 + holding2) / 2
  target1 = fair_percent * (indicator_value - zero1) / (fair - zero1)
  target2 = holding2 + holding1 - target1
  if abs(target1 - holding1) >= percent_delta:
    money = NET_ASSET * percent_delta
    if target1 > holding1:
      code1, code2 = code2, code1
      mp1, mp2 = mp2, mp1
      mp_base1, mp_base2 = mp_base2, mp_base1 
      target1, target2 = target2, target1
    return '%s(%s)(target = %.1f%%) %d units @%.2f ==> %s(%s)(target = %.1f%%) %d units @%.2f due to %s ratio = %.3f.'%(
          CODE_TO_NAME[code1], code1, target1 * 100, int(money / mp_base1), mp1,
          CODE_TO_NAME[code2], code2, target2 * 100, int(money / mp_base2), mp2,
          'Function' if IsLambda(indicator) else indicator, indicator_value)
  return ''
  
def GenericChangeAH(name, adh_lower, adh_upper):
  code = NAME_TO_CODE[name]
  codeh = AH_PAIR[code]
  adh = GetAHDiscount(code)
  if adh >= adh_upper and holding_percent[codeh] > 0.0:
    return '%s(%s) @%.3f --> %s(%s) @%.3f due to AHD = %.4f'%(
      CODE_TO_NAME[codeh], codeh, GetMarketPrice(codeh),
      CODE_TO_NAME[code], code, GetMarketPrice(code), adh)
  if adh <= adh_lower and holding_percent[code] > 0.0:
    return '%s(%s) @%.3f --> %s(%s) @%.3f due to AHD = %.4f'%(
      CODE_TO_NAME[code], code, GetMarketPrice(code),
      CODE_TO_NAME[codeh], codeh, GetMarketPrice(codeh), adh)
  return ''
  
def BuyYandex():
  return GenericDynamicStrategy(
    'Yandex',
    'P/B0',
    [.7, 0.3],
    [0.02, 0.08],
    0.8,
    buy_condition = lambda code: GetMarketPriceChange(code) <= -2);

def BuyYahoo():
  return GenericDynamicStrategy(
    'Yahoo',
    'P/B0',
    [1.0, 0.8],
    [0.05, 0.12],
    1.1,
    buy_condition = lambda code: GetMarketPriceChange(code) <= -1,
    sell_condition = lambda code: GetMarketPriceChange(code) >= 1);

def BuyApple():
  return GenericDynamicStrategy(
    'Apple',
    'DR0',
    [0.03, 0.04],
    [0.1, 0.3],
    0.15,
    buy_condition = lambda code: GetMarketPriceChange(code) <= 0);
  
def BuyBig4BanksH():
  codes = map(lambda name: NAME_TO_CODE[name],
              [
               '工商银行H',
               '建设银行H',
               '中国银行H',
              ])
  for code in codes:
    dis = GetAHDiscount(code)
    changeH = GetMarketPriceChange(code)
    change = GetMarketPriceChange(AH_PAIR[code])
    if dis >= 0.01 and changeH < 0:
      return 'Buy %s(%s) %d units @%.2f AH discount=%.1f%%'%(
        CODE_TO_NAME[code], code, int(NET_ASSET * 0.02 / GetMarketPriceInBase(code)),
        GetMarketPrice(code), dis * 100.0)
  return ''

def BuyCMBH():
  return GenericDynamicStrategy(
    '招商银行H',
    'AHD',
    [-0.05, 0],
    [0.2, 0.4],
    -0.1,
    buy_condition = lambda code: GetMarketPriceChange(code) < 0)

def BuyCMB():
  return GenericDynamicStrategy(
    '招商银行',
    'P/B',
    [0.9, 0.7],
    [0.3, 0.5],
    1.0,
    buy_condition = lambda code: GetAHDiscount(code) >= 0 and GetMarketPriceChange(code) < 0)

def BuyDeNA():
  # 同类公司P/S
  # KONAMI: 1.5
  # SEGA: 1.3
  # Zynga: 1.2
  return GenericDynamicStrategy(
    ':DeNA',
    'P/S',
    [1.1, 0.8],
    [0.05, 0.12],
    2.0,
    buy_condition = lambda code: GetMarketPriceChange(code) < min(0.0,
      1.1 * GetBeta(code) * GetMarketPriceChange('ni225')));

def BuyA50():
  return GenericDynamicStrategy(
    '南方A50',
    'P/E',
    [7.5, 7],
    [0.4, 0.6],
    9.0,
    buy_condition = lambda code: GetMarketPriceChange(code) < 0.0);

def BuyBOCH():
  return GenericDynamicStrategy(
    '中国银行H',
    'DR',
    [0.06, 0.07],
    [0.4, 0.5],
    0.05,
    buy_condition = lambda code: GetPB(code, GetMarketPriceChange(code)) < 0.9 and GetMarketPriceChange(
                                 code) < 0.0 and GetAHDiscount('中国银行') >= GetAHDiscount(
                                   '建设银行') / 2 and GetAHDiscount('中国银行') >= GetAHDiscount('工商银行') / 2,
    sell_condition = lambda code: GetMarketPriceChange(code) > 0)

def BuyBOC():
  return GenericDynamicStrategy(
    '中国银行',
    'DR',
    [0.06, 0.075],
    [0.3, 0.4],
    0.05,
    buy_condition = lambda code: GetPB(code, GetMarketPriceChange(code)) < 0.85,
    sell_condition = lambda code: GetMarketPriceChange(code) > 0)
 
def BuyWeibo():
  return GenericDynamicStrategy(
    'Weibo',
    'P/B0',
    [1.15, 0.8],
    [0.5, 0.1],
    # 等阿里收购微博的消息
    1.5,
    buy_condition = lambda code: GetMarketPriceChange(code) < -2);

def KeepDaLanChou():
  holding = 0
  for bank in WATCH_LIST_BANK.keys():
    holding += holding_percent[bank]
    if bank in AH_PAIR:
      holding += holding_percent[AH_PAIR[bank]]
  for etf in WATCH_LIST_ETF.keys():
    holding += holding_percent[etf]
  if holding < 1.0:
    return 'Buy %.1fK RMB DaLanChou'%((1.0 - holding) * NET_ASSET / 1000)
  return ''

def CMBHandCMB():
  return GenericChangeAH('招商银行', 0.05, 0.15)

def BOCHandBOC():
  if GetAHDiscount('中国银行') > GetAHDiscount('建设银行') or GetAHDiscount('中国银行') > GetAHDiscount('工商银行'):
    return '中国银行H(%s) premium is too high: %f'%(NAME_TO_CODE['中国银行H'], GetAHDiscount('中国银行'))
  return ''

def ReduceOverflow():
  for code in holding_percent.keys():
    if holding_percent[code] == 0.0: continue
    if code in AH_PAIR and holding_percent[AH_PAIR[code]] > 0 and GetAHDiscount(code) > 0.0: continue
    upper = PERCENT_UPPER[code] if code in PERCENT_UPPER else MAX_PERCENT_PER_STOCK
    hold = holding_percent[code] + (holding_percent[AH_PAIR[code]] if code in AH_PAIR else 0.0)
    if hold > upper:
      print 'Sell %s(%s) %d units @%.3f'%(
        CODE_TO_NAME[code], code,
        (hold - upper) * NET_ASSET / GetMarketPriceInBase(code),
        GetMarketPrice(code))
  return ''

def CMBandBOC():
  holding_percent[NAME_TO_CODE['中国银行']] += holding_percent[NAME_TO_CODE['中行转债']]
  res = GenericSwapStrategy('中国银行', '招商银行', 'DR', 1.0, 1.25, 0.05)
  holding_percent[NAME_TO_CODE['中国银行']] -= holding_percent[NAME_TO_CODE['中行转债']]
  return res

def BOCHandA50():
  return GenericSwapStrategy('中国银行H', '南方A50',
                             lambda: GetDR(NAME_TO_CODE['中国银行H'], GetMarketPrice('中国银行H')) /
                              (0.5 / GetPE('南方A50', GetMarketPrice('南方A50'))),
                             0.7, 0.95, 0.05)

def SellBOCH():
  code = NAME_TO_CODE['中国银行H']
  if GetAHDiscount(code) < -0.98:
    mp = GetMarketPriceInBase(code)
    return 'Sell 中国银行H(%s) %d units @%.3f due to AHR = %.3f'%(
      code,
      int((holding_percent[code] - 0.2) * NET_ASSET / mp),
      mp,
      GetAHDiscount(code))
  return ''

def BOCandCB():
  return GenericSwapStrategy('中国银行', '中行转债',
                             lambda: GetPB0('中行转债', GetMarketPrice('中行转债')),
                             1.000, 1.01, 0.05)

STRATEGY_FUNCS = {
  BuyApple: 'Buy Apple',
  BuyBig4BanksH: 'Buy 四大行H股 ',
  BuyDeNA:  'Buy :DeNA',
  #BuyCMB:  'Buy CMB',
  BuyA50: 'Buy A50',
  #BuyBOCH: 'Buy BOCH',
  #BuyBOC: 'Buy BOC',
  BuyWeibo: 'Buy Weibo',
  KeepDaLanChou: 'Buy 大蓝筹',
  BOCHandBOC: 'BOCH and BOC',
  CMBHandCMB: 'CMBH and CMB',
  BuyYandex: 'Buy Yandex',
  BuyYahoo: 'Buy Yahoo',
  ReduceOverflow: 'Reduce overflow',
  CMBandBOC: 'CMB<->BOC',
  BOCHandA50: 'A50<->BOCH',
  SellBOCH: 'Sell BOCH',
  BOCandCB: 'BOC<->CB',
}

#--------------End of strategy functions-----

def InitAll():
  for key in AH_PAIR.keys():
    AH_PAIR[AH_PAIR[key]] = key

  for dt in [WATCH_LIST_BANK, WATCH_LIST_BANK_1,  WATCH_LIST_INSURANCE, WATCH_LIST_MOBILE_GAMES,
             WATCH_LIST_INTERNET, WATCH_LIST_ETF, WATCH_LIST_CB, WATCH_LIST_OTHER]:
    for code in dt.keys():
      CODE_TO_NAME[code] = dt[code]
      if code in AH_PAIR:
        CODE_TO_NAME[AH_PAIR[code]] = dt[code] + 'H'.encode('utf-8')

  for code in CODE_TO_NAME.keys():
    NAME_TO_CODE[CODE_TO_NAME[code]] = code

  for dt in [WATCH_LIST_BANK, WATCH_LIST_BANK_1, WATCH_LIST_INSURANCE]:
    keys = dt.keys()
    for code in keys:
      if code in AH_PAIR:
        dt[AH_PAIR[code]] = dt[code] + 'H'.encode('utf-8')

  for dt in [STOCK_CURRENCY, SHARES, CAP, CB, EPS0, EPS, DVPS, DVPS0, SPS,
             BVPS0, BVPS, ETF_BOOK_VALUE_FUNC, FORGOTTEN, PERCENT_UPPER]:
    keys = dt.keys()
    for key in keys:
      dt[NAME_TO_CODE[key]] = dt[key]

  for dt in [SHARES, PERCENT_UPPER]:
    for key in dt.keys():
      if key in AH_PAIR:
        dt[AH_PAIR[key]] = dt[key]

  for dt in [CAP, EPS0, EPS, DVPS, DVPS0, SPS, BVPS0, BVPS]:
    for key in dt.keys():
      if key in AH_PAIR:
        dt[AH_PAIR[key]] = dt[key] * EX_RATE[GetCurrency(key) + '-' + GetCurrency(AH_PAIR[key])]

  for dt in [CB]:
    for key in dt.keys():
      if key in AH_PAIR:
        dt[AH_PAIR[key]] = map(lambda x: x * EX_RATE[GetCurrency(key) + '-' + GetCurrency(AH_PAIR[key])], dt[key])

  if 'all' in set(sys.argv):
    sys.argv += ['stock', 'hold', 'etf', 'Price']
  for name in EPS:
    if name in BVPS0 and (name in WATCH_LIST_BANK or name in WATCH_LIST_BANK_1):
      roe = 1.0 * EPS[name] / BVPS0[name]
      msg = '%s ROE=%.1f%%'%(name, roe * 100)
      if roe < 0.1 or roe > 0.28:
        print 'Bad estimation: %s'%(msg)
      else:
        sys.stderr.write('Estimation for %s\n'%(msg))

def CalOneStock(NO_RISK_RATE, records, code, name):
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
  vid = 'visualization_%s'%(code)
  data = ''
  prices = []
  for cell in records:
    currency = cell[7]
    ex_rate = EX_RATE[currency + '-' + CURRENCY]
    trans_date = cell[0]
    buy_shares = cell[5]
    origin_price = cell[4]
    price = origin_price * ex_rate
    fee = cell[6] * ex_rate
    sum_fee += fee
    value = -price * buy_shares - fee - cell[8] * ex_rate
    if -1 == cell[1].find('股息'):
      data += '[new Date(%d, %d, %d), %.3f, \'%s%d\', \'%.0fK %s\'],\n'%(
          trans_date.year, trans_date.month - 1, trans_date.day,
          origin_price, '+' if buy_shares > 0 else '',
          buy_shares, (value + 500) / 1000, CURRENCY)
      prices.append(origin_price)
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
      assert value <= 0.0
      holding_cost = (holding_cost * holding_shares - value) / (holding_shares + buy_shares)
    holding_shares += buy_shares
    assert holding_shares >= 0.0
  if investment > 0.0:
    capital_cost  += investment * NO_RISK_RATE / 365 * (date.today() - prev_date).days
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

def ReadRecords(input):
  raw_all_records = []
  for line in input:
    if 0 != line.find('20'):
      continue
    cells = line.strip().split(',')
    cells[0] = date(int(cells[0][0:4]), int(cells[0][4:6]), int(cells[0][6:8]))
    raw_all_records.append(cells)
  raw_all_records.sort(key = lambda record: record[0]) 

  all_records = defaultdict(list)
  sell_fee = 18.1 / 10000
  buy_fee = 8.1 / 10000
  for cells in raw_all_records:
    cells.append(0.0)
    price, buy_shares = float(cells[4]), int(cells[5])
    fee = float(cells[6]) if cells[6] != '' else (
      buy_fee * abs(buy_shares * price) if buy_shares > 0 else sell_fee * abs(buy_shares * price))
    cells[4], cells[5], cells[6] = price, buy_shares, fee
    last = all_records[cells[2]][-1] if len(all_records[cells[2]]) > 0 else []
    if (len(last) > 0 and
        (cells[0] - last[0]).days < 7
        and cells[1].find('股息') == -1
        and last[1].find('股息') == -1):
      if buy_shares + last[5] != 0:
        last[4] = (last[8] + buy_shares * price + last[5] * last[4]) / (buy_shares + last[5])
        last[8] = 0
      else:
        last[8] += buy_shares * price + last[5] * last[4]
      last[5] += buy_shares
      last[6] += fee
    else:
      all_records[cells[2]].append(cells)
  return all_records

def PrintHoldingSecurities(all_records):
  global NET_ASSET
  table_header = [
                  'Percent',
                  'CC',
                  '#TxN',
                  'TNF',
                  'DTP',
                  '#DT',
                  'MP',
                  'Chg',
                  'P/E0',
                  'P/E',
                  'P/S',
                  'P/B0',
                  'P/B',
                  'DR0',
                  'DR',
                  'AHD',
                  'DvDays',
                  'Stock name']
  silent_column = [
    'MV',
    'MP',
    '#TxN',
    'TNF',
    'DTP',
    '#DT',
    'CC',
    'NCF',
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
    if key in FORGOTTEN:
      # in CURRENCY
      name = all_records[key][0][3]
      (net_profit, capital_cost, remain_stock, dtp, dt, txn_fee, currency, function,division) = CalOneStock(
          NO_RISK_RATE, all_records[key], key, name)
      net_profit *= EX_RATE[CURRENCY + '-' + currency]
      cells = all_records[key][-1]
      cells[2:7] = [currency, '', 1, int(net_profit), 0]
      all_records[currency].append(cells)
      sys.stderr.write('Convert %s to cash %d in %s\n'%(CODE_TO_NAME[key], net_profit, currency))
      assert net_profit >= 0
      del all_records[key]
      function_html += function
      div_html += division
       
  for key in all_records.keys():
    sys.stderr.write('Processing [' + key + ']\n')
    name = all_records[key][0][3]
    # All in CURRENCY
    (net_profit, capital_cost, remain_stock, dtp, dt, txn_fee, currency, function, division) = CalOneStock(
      NO_RISK_RATE, all_records[key], key, name)
    if key in total_investment:
      total_capital[currency] += -net_profit
      total_capital_cost[currency] += capital_cost
      continue
    function_html += function
    div_html += division
    investment = -net_profit
    total_investment[currency] += investment
    total_transaction_fee[currency] += txn_fee
    ex_rate = EX_RATE[currency + '-' + CURRENCY]
    mp, chg, mp_pair_rmb, mv, = 0.0001, 0, 1, 0
    if remain_stock > 0 :
      mp = GetMarketPrice(key)
      chg = GetMarketPriceChange(key)
      mp_pair_rmb = mp * ex_rate
      mv = mp * remain_stock * ex_rate
      if key in AH_PAIR:
        mp_pair_rmb = GetMarketPriceInBase(AH_PAIR[key])
    total_market_value[currency] += mv
    sys.stderr.write('%s profit %.0f %s from %s\n'%(
      'Realized' if remain_stock == 0 else 'Unrealized',
      net_profit + mv,
      CURRENCY,
      name))
    record = {
        'Code': key,
        'MV': myround(mv, 0),
        'Price': mp,
        'Chg': round(chg, 2),
        'CC': myround(capital_cost, 0),
        '#TxN': len(all_records[key]),
        'TNF': myround(txn_fee, 0),
        'DTP': myround(dtp, 0),
        '#DT': dt,
        'Pos': remain_stock,
        'P/E0': myround(GetPE0(key, mp), 2),
        'P/E': myround(GetPE(key, mp), 2),
        'P/S': myround(GetPS(key, mp), 2),
        'P/B0': myround(GetPB0(key, mp), 3),
        'P/B': myround(GetPB(key, mp), 2),
        'DR0':  myround(GetDR0(key, mp) * 100 , 2),
        'DR':  myround(GetDR(key, mp) * 100 , 2),
        'AHD': str(myround(100.0 * (mp_pair_rmb - mp * ex_rate ) / mp / ex_rate, 1)) + '%',
        'DvDays': ((DIVIDEND_DATE[name] if name in DIVIDEND_DATE else date(2016, 1, 1)) - date.today()).days,
        'Stock name': name + '(' + key + ')',
    }
    for col in ['MV', 'CC', '#TxN', 'TNF', 'DTP', '#DT']:
      summation[col] = summation.get(col, 0) + record[col]
    if remain_stock > 0:
      stat_records_map.append(record)
  
  for dt in [total_market_value, total_capital,
             total_investment, total_transaction_fee]:
    dt['USD'] += dt['HKD']
    dt['USD'] += dt['YEN']
  
  capital_header = ['Currency', 'Market Value', 'Free Cash', 'Net', 'Cash',
                    'Transaction Fee', 'Max Decline', 'IRR']
  capital_table_map = []
  # All are in CURRENCY
  cash_flow = defaultdict(list)
  for key in all_records.keys():
    for cell in all_records[key]:
      currency = cell[7]
      ex_rate = EX_RATE[currency + '-' + CURRENCY]
      trans_date = cell[0]
      fee = cell[6] * ex_rate
      buy_shares = cell[5]
      price = cell[4] * ex_rate
      value = -price * buy_shares - fee - cell[8] * ex_rate
      cash_flow[currency].append([trans_date, key, value]);
  
  cash_flow['USD'] += cash_flow['HKD']
  cash_flow['USD'] += cash_flow['YEN']
  
  for dt in [total_market_value, total_capital,
             total_investment, total_transaction_fee]:
    dt['ALL'] = dt['USD'] + dt['RMB']
    dt['RMB'] *= EX_RATE[CURRENCY + '-RMB']
    dt['USD'] *= EX_RATE[CURRENCY + '-USD']

  cash_flow['ALL'] = copy.deepcopy(cash_flow['USD'] + cash_flow['RMB'])
  for record in cash_flow['RMB']:
    record[2] *= EX_RATE[CURRENCY + '-RMB']
  for record in cash_flow['USD']:
    record[2] *= EX_RATE[CURRENCY + '-USD']
  
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
        'Net': str(myround((total_market_value[currency] + total_capital[currency] - total_investment[currency]) / 1000, 0)) + 'K',
        }
    )
  
  PrintTableMap(capital_header, capital_table_map, set(), truncate_float = False)
  NET_ASSET = total_market_value['ALL'] + total_capital['ALL'] - total_investment['ALL']
  for col in ['Chg', 'DR', 'DR0', 'Percent']:
    summation[col] = 0.0
  for record in stat_records_map:
    holding_percent[record['Code']] = 1.0 * record['MV'] / NET_ASSET
    summation['Percent'] += holding_percent[record['Code']]
    record['Percent'] = str(myround(holding_percent[record['Code']] * 100, 1)) + '%'
    for col in ['Chg', 'DR', 'DR0']:
      summation[col] += holding_percent[record['Code']] * record[col]
  for col in ['Chg', 'DR', 'DR0']:
    summation[col] = round(summation[col], 2)
  summation['Percent'] = str(round(summation['Percent'] * 100, 0)) + '%'
  if 'hold' in set(sys.argv):
    stat_records_map.append(summation)
    stat_records_map.sort(reverse = True, key = lambda record: record.get('MV', 0))
    PrintTableMap(table_header, stat_records_map, silent_column, truncate_float = False)
  if 'chart' in set(sys.argv):
    open('/tmp/charts.html', 'w').write(
      HTML_TEMPLATE%(function_html, div_html) 
    )

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
    func = ETF_BOOK_VALUE_FUNC[code] if code in ETF_BOOK_VALUE_FUNC else lambda: GetXueqiuETFBookValue(code)
    price, change, real_value = GetMarketPrice(code), GetMarketPriceChange(code), func()
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
  PrintTableMap(table_header, table_map, silent, truncate_float = False)

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
        record[col] = round(FINANCIAL_FUNC[col](code, mp), 3)
    table.append(record)
  table.sort(reverse = rev, key = lambda record: record.get(sort_key, 0))
  PrintTableMap(table_header, table, silent, truncate_float = False)

def PrintWatchedBank():
  table_header = [
                  'Change',
                  'P/E0',
                  'P/E',
                  'P/B0',
                  'P/B',
                  'DR',
                  'DR0',
                  'AHD',
                  'Stock name'
                  ]
  PrintWatchedStocks(WATCH_LIST_BANK_1, table_header, 'P/B')
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
                  'P/B0',
                  'DR0',
                  'Stock name'
                  ]
  PrintWatchedStocks(WATCH_LIST_INTERNET, table_header, 'CAP')

def RunStrategies():
  for strategy in STRATEGY_FUNCS.keys():
    sys.stderr.write("Running straregy: %s\n"%(STRATEGY_FUNCS[strategy]))
    suggestion = strategy()
    if suggestion != '':
      print '%s'%(suggestion)

try:
  InitAll()
  
  if 'etf' in set(sys.argv):
    PrintWatchedETF()
  
  #if 'stock' in set(sys.argv) or 'insurance' in set(sys.argv):
    #PrintWatchedInsurance()
  
  if 'stock' in set(sys.argv) or 'internet' in set(sys.argv):
    PrintWatchedInternet()
  
  if 'stock' in set(sys.argv) or 'bank' in set(sys.argv):
    PrintWatchedBank()
  
  PrintHoldingSecurities(ReadRecords(sys.stdin))
  RunStrategies()
except Exception as ins:
  print 'Run time error: ', ins
  traceback.print_exc(file=sys.stdout)
