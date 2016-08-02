#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import datetime
import collections
import urllib
import traceback
import copy
import re

from smart_stocker_global import *
import logging

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
            logging.info('Getting url: %s\n', url)
            URL_CONTENT_CACHE[url] = urllib2.urlopen(request).read()
        content = URL_CONTENT_CACHE[url]
        idx = content.find(company)
        while idx >= 0:
            content = content[idx + len(company):]
            res += 1
            idx = content.find(company)
    return res

def CrawlUrl(url, throw_exp = False, encoding = ''):
    try:
        if url not in URL_CONTENT_CACHE:
            logging.info('Crawling url: %s\n'%(url))
            request = urllib2.Request(url)
            URL_CONTENT_CACHE[url] = urllib2.urlopen(request).read()
            if encoding != '':
              URL_CONTENT_CACHE[url] = URL_CONTENT_CACHE[url].decode(encoding).encode('utf-8')
        return URL_CONTENT_CACHE[url]
    except Exception, e:
        logging.info('Exception ' + str(e) +'\n')
        logging.info('Failed to open url: ' + url + '\n')
        if throw_exp: raise
        return ''

def GetValueFromUrl(url, feature_str, end_str, func, throw_exp = True, reg_exp = '-?[0-9.,]+%?', default_value = None, encoding = ''):
    try:
        content = CrawlUrl(url, throw_exp, encoding)
        for fs in feature_str:
            pos = content.find(fs)
            if pos == -1:
                raise Exception('feature str [%s] not found.'%(fs))
            content = content[len(fs) + pos:]
        if reg_exp is None:
            pos = content.find(end_str)
            if pos < 0: raise Exception('end str [%s] not found'%(end_str))
            return content[0:pos]
        else:
            pat = re.compile(reg_exp)
            match = pat.search(content) 
            if match is None: raise Exception('reg exp [%s] not found'%(reg_exp))
            return func(match.group(0))
    except Exception, e:
        logging.info('Exception ' + str(e) +'\n')
        logging.info('Failed to open url: ' + url + '\n')
        if throw_exp: raise
        return (default_value if default_value is not None else func('0.0'))

def GetJapanStockPriceAndChange(code):
    url = 'http://jp.reuters.com/investing/quotes/quote?symbol=%s.T'%(str(code))
    try:
        return [GetValueFromUrl(url, ['<div id="priceQuote">', '<span class="valueContent">'],
                                                        '</span>', lambda s: float(s.replace(',', '')), reg_exp = '[0-9.,]+'), 0.0]
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

NAV_FUNC = {
    '02822': lambda: GetValueFromUrl('http://www.csop.mdgms.com/iopv/nav.html?l=tc',
                                                                      ['即日估計每基金單位資產淨值', 'nIopvPriceHKD', '>'], '<', float, False, default_value = 1.0),
}

def GetCurrency(code):
    if code in STOCK_INFO:
        return STOCK_INFO[code]['currency']
    if code.find('@') != -1:
        code = re.split('[-@]', code)[0]
    return STOCK_INFO[code]['currency'] if code in STOCK_INFO else 'unknown'

def GetXueqiuUrlPrefix(code):
    market2prefix = {
        'sz': ['sz'],
        'sh': ['sh'],
        'hk': [''],
        'us': [''],
    }
    return market2prefix[STOCK_INFO[code]['market']]

def GetXueqiuInfo(code, market):
    url_prefix = 'http://xueqiu.com/S/'
    market2prefix = {
        'sz': ['sz'],
        'sh': ['sh'],
        'hk': [''],
        'us': [''],
    }
    url_prefix = 'http://xueqiu.com/S/'
    price_feature_str = ['<div class="currentInfo"><strong data-current="']
    price_end_str = '"'
    change_feature_str = ['<span class="quote-percentage">', '(']
    change_end_str = '%)'
    cap_feature_str = ['市值：<span>']
    cap_end_str = '<'
    book_value_str = ['单位净值', '<span>']
    book_value_end_str = '<'
    ttmpe_begin_str= ['LYR', 'TTM', '/']
    ttmpe_end_str= '<'
    
    for pr in (market2prefix[market] if market in market2prefix else GetXueqiuUrlPrefix(code)):
        url = url_prefix + pr + code
        try:
            price = GetValueFromUrl(url, price_feature_str, price_end_str, float)
            change = GetValueFromUrl(url, change_feature_str, change_end_str, float)
            cap = GetValueFromUrl(url, cap_feature_str, cap_end_str,
                                                        lambda s: float(s.replace('亿', '')) * 10**8, False)
            book_value = GetValueFromUrl(url, book_value_str, book_value_end_str, float, False)
            ttmpe = GetValueFromUrl(url, ttmpe_begin_str, ttmpe_end_str, float, False)
            return {
                'price': price,
                'change': change,
                'cap': cap,
                'bv': book_value,
                'pe-ttm': ttmpe,
            }
        except:
            continue
    return {}

def GetNAVFromHeXun(code):
    return GetValueFromUrl('http://jingzhi.funds.hexun.com/%s.shtml'%(code),
                                                  ['最新净值', '<font>'],
                                                  '<', float, False,
                                                  default_value = .01, encoding = 'gbk')

def GetNAVFromEasyMoney(code):
    return GetValueFromUrl('http://fund.eastmoney.com/%s.html'%(code),
                                                  ['按照基金持仓和指数走势估算', '单位净值', '<span class=', '<span class=', '>'],
                                                  '<', float, False,
                                                  default_value = .01, encoding = 'gbk')

def GetEasyMoneyInfo(code, market):
    url = 'http://quote.eastmoney.com/%s.html'%(market+code)
    try:
        return {
            'dynamic-pe': GetValueFromUrl(
                                            url,
                                            ['PE(', ')', '<', '>'],
                                            '<', float, False),
        }
    except:
        return {}
    return {}

def GetSinaUrlPrefix(code):
    market2prefix = {
        'sz': 'sz',
        'sh': 'sh',
        'hk': 'hk',
        'us': 'gb_',
    }
    if 'market' in STOCK_INFO[code]:
        return market2prefix[STOCK_INFO[code]['market']]
    raise BaseExecption('Unknow market for code: %s'%(code))

def PrefetchSinaStockList(codes):
    logging.info('Prefetching %d stocks.'%(len(codes)))
    url_prefix = 'http://hq.sinajs.cn/list='
    url = url_prefix + ','.join([GetSinaUrlPrefix(code) + code.lower() for code in codes])
    content = CrawlUrl(url, True)
    stocks = content.split('\n')
    for code in codes:
        url = url_prefix + GetSinaUrlPrefix(code) + code.lower()
        token = 'hq_str_' + GetSinaUrlPrefix(code) + code.lower()
        for stock in stocks:
            if stock.find(token) != -1:
                URL_CONTENT_CACHE[url]  = stock
                break

def GetMarketPriceFromSina(code):
    url_prefix = 'http://hq.sinajs.cn/list='
    price_end_str = '"'
    for pr in [GetSinaUrlPrefix(code)]:
        suffix = pr + code.lower()
        url = url_prefix + suffix
        try:
            logging.info('Getting value from url: %s\n'%(url))
            values = GetValueFromUrl(url, 'hq_str_%s="'%(suffix), '"', str, reg_exp = '[^"]+')
            values = values.split(',')
            logging.info('Get string for %s: %s from url: %s\n'%(code, str(values), url))
            if len(values) == 0: continue
            price, change, cap, book_value = 0, 0, 0, 1.0
            if suffix.find('gb_') == 0:
                price, change, cap = float(values[1]), myround(float(values[2]), 1), float(values[12])
            elif suffix.find('hk') == 0:
                price, change = float(values[6]), myround(float(values[8]), 1)
                if price < 0.02:
                    price, change = float(values[3]), 0
                    # logging.info('new price: %f %s %s %s', price, values[2], values[3], values[4])
            else:
                price = float(values[3])
                prev_price = float(values[2])
                change = myround(100.0 * (price - prev_price) / prev_price, 1)
            data = [price, change, cap, book_value]
            logging.info('Got market data for %s = %s\n'%(code, str(data)))
            return data
        except Exception, e:
            logging.info('Exception: %s\n'%(str(e)))
            time.sleep(3)
            continue
    return [0.0, 0.0, 0.0, 0.0]

def GetMarketPrice(code):
    if code.find('@') != -1:
        tokens = re.split('[-@]', code)
        strike = float(tokens[2])
        mp = GetMarketPrice(tokens[0])
        return max(0.01, strike - mp) if tokens[1].lower() == 'put' else max(0.01, mp - strike)
    code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
    logging.info('Getting market price for ' + code + '\n')
    if code in MARKET_PRICE_CACHE:
        return MARKET_PRICE_CACHE[code][0]
    func = lambda: GetMarketPriceFromSina(code)
    if code in MARKET_PRICE_FUNC:
        func = MARKET_PRICE_FUNC[code] 
    try:
        logging.info('Getting market price for %s\n'%(code))
        data = func()
        data[0] = max(data[0], MIN_MP)
        MARKET_PRICE_CACHE[code] = data
        return data[0]
    except:
        logging.info('Failed to get market price for %s.\n'%(code))
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
    target_url = 'http://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml'
    rate = {}  
    for cur in CURRENCIES:
        rate[cur] = GetValueFromUrl(target_url,
                                                                ["<Cube currency='%s'"%(cur.upper()), "rate='"],
                                                                "'", float, throw_exp = True)
    for a in CURRENCIES:
        for b in CURRENCIES:
            EX_RATE[a + '-' + b] = rate[b] / rate[a]
    logging.info('%s\n'%(str(EX_RATE)))

def PopulateFinancialData():
    for code in FINANCAIL_DATA_BASE.keys():
        logging.info('Populating data for %s(%s)\nbasic data: %s\n'%(CODE_TO_NAME[code], code, str(FINANCAIL_DATA_BASE[code])))
        info = STOCK_INFO[code]
        data = FINANCAIL_DATA_BASE[code]
        adv_data = FINANCAIL_DATA_ADVANCE[code]
        if 'class-b' in info:
            for key in ['sdv/p', 'ddv/p']:
                if key in info:
                    adv_data[key] = max(0.0, info[key])
            continue
        mp = GetMarketPrice(code)
        if mp < 0 and 'hcode' in info:
            # A股涨停，按H股价格计算
            mp = GetMarketPrice(info['hcode']) * EX_RATE['hkd-cny']
            MARKET_PRICE_CACHE[code] = (mp, 0)
            logging.info('Using h stock market price for %s\n'%(CODE_TO_NAME[code]))
        FINANCAIL_DATA_ADVANCE[code]['mp'] = mp
        if code in NAV_FUNC:
            adv_data['sbv'] = data['sbv'] = NAV_FUNC[code]()
        extra_key = set(['roe3'])
        for key in FINANCIAL_KEYS:
            if key.find('p/') != -1 and key[2:] in data and isinstance(data[key[2:]], float) and data[key[2:]] > 0:
                adv_data[key] = mp / data[key[2:]]
            elif key.find('/p') != -1 and key[0:-2] in data and isinstance(data[key[0:-2]], float):
                adv_data[key] = data[key[0:-2]] / mp
            elif key in extra_key and key in data:
                adv_data[key] = data[key]
        logging.info('Populated adv financial data for %s(%s): %s\n'%(CODE_TO_NAME[code], code, str(adv_data)))
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

def PopulateMacroData():
    try:
        MACRO_DATA['ah-premium'] = GetValueFromUrl('http://markets.ft.com/research/Markets/Tearsheets/Summary?s=HSCAHPI:HKG',
                                                                                              ['HANG SENG CHINA AH PREMIUM INDEX</span>',
                                                                                                'HSCAHPI:HKG</span>',
                                                                                                '<td class="text first">', '>'],
                                                                                              '<', float, True) / 100.0 - 1.0
    except Exception, e:
        MACRO_DATA['ah-premium'] = 0.1
        logging.info('Failed to get ah premium with exception [%s]\n'%(str(e)))
    MACRO_DATA['risk-free-rate'] = 0.07
    MACRO_DATA['official-rate'] = 0.025
    logging.info('macro data = %s\n'%(str(MACRO_DATA)))

