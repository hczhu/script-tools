#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import datetime
import collections
import urllib2
import traceback
import copy
import re

from smart_stocker_global import *

URL_CONTENT_CACHE = {
}

REAL_TIME_VALUE_CACHE = {
}

REALTIME_VALUE_FUNC = {
}

MARKET_PRICE_CACHE = {
}

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

def GetValueFromUrl(url, feature_str, end_str, func, throw_exp = True, reg_exp = '[0-9.]+'):
  try:
    if url not in URL_CONTENT_CACHE:
      request = urllib2.Request(url)
      URL_CONTENT_CACHE[url] = urllib2.urlopen(request).read()
    content = URL_CONTENT_CACHE[url]
    for fs in feature_str:
      content = content[len(fs) + content.find(fs):]
    pat = re.compile(reg_exp)
    match = pat.search(content) 
    if match is None: raise Exception('reg exp [%s] not found'%(reg_exp))
    return func(match.group(0))
  except Exception, e:
    sys.stderr.write('Exception ' + str(e) +'\n')
    sys.stderr.write('Failed to open url: ' + url + '\n')
    if throw_exp: raise
    return func('0.0')

def GetJapanStockPriceAndChange(code):
  url = 'http://jp.reuters.com/investing/quotes/quote?symbol=%s.T'%(str(code))
  try:
    return (GetValueFromUrl(url, ['<div id="priceQuote">', '<span class="valueContent">'],
                            '</span>', lambda s: float(s.replace(',', '')), reg_exp = '[0-9.,]+'),
            GetValueFromUrl(url, ['<div id="percentChange">', '<span class="valueContent"><span class="', '>'],
                            '%', lambda s: float(s.replace(',', '')), reg_exp = '[0-9.,]+'))
  except:
    return [float(0), 0.0]

def GetJapanStockBeta(code):
  url = 'http://jp.reuters.com/investing/quotes/quote?symbol=%s.T'%(str(code))
  try:
    return GetValueFromUrl(url,
        ['<span id="quoteBeta">'],
         '</span>', lambda s: float(s.replace(',', '')))
  except:
    return 0.0

MARKET_PRICE_FUNC = {
  'ni225': lambda: [0,
                    GetValueFromUrl('http://www.bloomberg.com/quote/NKY:IND',
                                    ['<meta itemprop="priceChangePercent" content="'],
                                    '"', lambda s: float(s.replace(',', '')))]
}

def GetCurrency(code):
  return STOCK_INFO[code]['currency'] if code in STOCK_INFO else 'cny'

def GetXueqiuUrlPrefix(code):
  market2prefix = {
    'sz': ['sz'],
    'sh': ['sh'],
    'hk': [''],
    'us': [''],
  }
  return market2prefix[STOCK_INFO[code]['market']]

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
  market2prefix = {
    'sz': ['sz'],
    'sh': ['sh'],
    'hk': ['hk'],
    'us': ['gb_'],
  }
  return market2prefix[STOCK_INFO[code]['market']]

def GetMarketPriceFromSina(code):
  url_prefix = 'http://hq.sinajs.cn/list='
  price_end_str = '"'
  for pr in GetSinaUrlPrefix(code) + GetSinaUrlPrefix(code):
    suffix = pr + code.lower()
    url = url_prefix + suffix
    try:
      values = GetValueFromUrl(url, 'hq_str_%s="'%(suffix), '"', str, reg_exp = '[^"]+')
      sys.stderr.write('Get string for %s: [%s] from url: %s\n'%(code, [values], url))
      if len(values) == 0: continue
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
    except Exception, e:
      sys.stderr.write('Exception: %s\n'%(str(e)))
      time.sleep(3)
      continue
  return [0.0, 0.0, 0.0, 0.0]

def GetXueqiuETFBookValue(code):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  return GetXueqiuMarketPrice(code)[3]

def GetMarketPrice(code):
  if code.find('@') != -1:
    tokens = re.split('[-@]', code)
    strike = float(tokens[2])
    mp = GetMarketPrice(tokens[0])
    return max(0.01, strike - mp) if tokens[1].lower() == 'put' else max(0.01, mp - strike)
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  sys.stderr.write('Getting market price for ' + code + '\n')
  if code in MARKET_PRICE_CACHE:
    return MARKET_PRICE_CACHE[code][0]
  func = lambda: GetMarketPriceFromSina(code) if STOCK_INFO[code]['market'] != 'jp' else GetJapanStockPriceAndChange(code)
  if code in MARKET_PRICE_FUNC:
    func = MARKET_PRICE_FUNC[code] 
  try:
    data = func()
    MARKET_PRICE_CACHE[code] = data
    return data[0]
  except:
    sys.stderr.write('Failed to get market price for %s.\n'%(code))
    return 0.0

def GetMarketCap(code):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  if code not in MARKET_PRICE_CACHE:
    GetMarketPrice(code)
  if code in MARKET_PRICE_CACHE:
    return MARKET_PRICE_CACHE[code][2]
  return 0.0

def GetMarketPriceChange(code):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  if code not in MARKET_PRICE_CACHE:
    GetMarketPrice(code)
  if code in MARKET_PRICE_CACHE:
    return MARKET_PRICE_CACHE[code][1]
  return 0.0

def GetMarketPriceInBase(code):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  mp = GetMarketPrice(code)
  currency = GetCurrency(code);
  mp *= EX_RATE[currency + '-' + CURRENCY]
  return mp

#----------End of crawler util functions-----------------

def InitExRate():
  template_url = 'http://www.bloomberg.com/quote/%s%s:CUR'
  for cur in CURRENCIES:
    if CURRENCY == cur:
      EX_RATE[CURRENCY + '-' + cur] = 1.0
    else:
      EX_RATE[CURRENCY + '-' + cur] = GetValueFromUrl(
        template_url%(CURRENCY, cur),
        ['<meta itemprop="exchange" content="CURRENCY',
         '<span class=" price">'],
        '<span class=', float, throw_exp = True)
  for pr in EX_RATE.keys():
    currencies = pr.split('-')
    assert(len(currencies) == 2)
    EX_RATE[currencies[1] + '-' + currencies[0]] = 1.0 / EX_RATE[pr]
  for a in CURRENCIES:
    for b in CURRENCIES:
      EX_RATE[a + '-' + b] = EX_RATE[a + '-' + CURRENCY] * EX_RATE[CURRENCY + '-' + b]
    EX_RATE[a + '-' + b] = 1.0
  sys.stderr.write('%s\n'%(str(EX_RATE)))

def PopulateFinancialData():
  for code in FINANCAIL_DATA_BASE.keys():
    info = STOCK_INFO[code]
    data = FINANCAIL_DATA_BASE[code]
    adv_data = FINANCAIL_DATA_ADVANCE[code]
    mp = GetMarketPrice(code)
    FINANCAIL_DATA_ADVANCE[code]['mp'] = mp
    if 'cross-share' in data:
      cross_value = 0.0
      for pr in data['cross-share']:
        cross_code = pr[1]
        cross_value += EX_RATE[STOCK_INFO[cross_code]['currency'] + '-' + info['currency']] * GetMarketPrice(cross_code) * pr[0]
      data['cross-share'] = cross_value
    for key in FINANCIAL_KEYS:
      if key.find('p/') != -1 and key[2:] in data:
        adv_data[key] = mp / data[key[2:]]
      elif key.find('/p') != -1 and key[0:-2] in data:
        adv_data[key] = data[key[0:-2]] / mp
    # Populate corresponding h-share.
    if 'hcode' in info:
      hmp = GetMarketPrice(info['hcode'])
      adv_data['ah-ratio'] = mp / (EX_RATE['hkd-cny'] * hmp)
      h_adv_data = dict(adv_data)
      h_adv_data['mp'] = hmp
      for key in h_adv_data:
        if key.find('p/') != -1:
          h_adv_data[key] /= adv_data['ah-ratio']
        elif key.find('/p') != -1:
          h_adv_data[key] *= adv_data['ah-ratio']
      h_adv_data['ah-ratio'] = 1.0 / adv_data['ah-ratio']
      FINANCAIL_DATA_ADVANCE[info['hcode']] = h_adv_data
    if 'start-date' in data and 'interest-rate' in data and 'old-rate' in data:
      data['sbv'] = adv_data['sbv'] = 1.0 + (datetime.date.today() - data['start-date']).days / 365.0 * data['old-rate']
      adv_data['sdv/p'] = data['interest-rate'] / (mp - (adv_data['sbv'] - 1.0))

def PopulateMacroData():
  try:
    MACRO_DATA['ah-premium'] = GetValueFromUrl('http://markets.ft.com/research/Markets/Tearsheets/Summary?s=HSCAHPI:HKG',
                                               ['HANG SENG CHINA AH PREMIUM INDEX',
                                                'HSCAHPI:HKG',
                                                '<td class="text first">',
                                                '>'], '<', float, True) / 100.0 - 1.0
  except Exception, e:
    MACRO_DATA['ah-premium'] = 0.1
    sys.stderr.write('Failed to get ah premium with exception [%s]\n'%(str(e)))
  MACRO_DATA['risk-free-rate'] = 0.07
  sys.stderr.write('macro data = %s\n'%(str(MACRO_DATA)))
  

