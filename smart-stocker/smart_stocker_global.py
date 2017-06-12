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

# -------------- End of template --------------------------

EX_RATE = {
}
 
CURRENCIES = ['usd', 'cny', 'hkd', 'jpy']

CURRENCY = 'usd'

MIN_MP = 0.07

ETF_BOOK_VALUE_FUNC = {
  # 南方A50 ETF
  # http://www.csopasset.com/tchi/products/china_A50_etf.php
  '南方A50': lambda: GetValueFromUrl('http://www.csop.mdgms.com/iopv/nav.html?l=tc',
                                      ['即日估計每基金單位資產淨值', '<td id="nIopvPriceHKD">'],
                                      '</td>',
                                      float,
                                      ),
}

DV_TAX = 0.1
LOAN_RATE = 1.8 / 100.0

CODE_TO_NAME = {}

NAME_TO_CODE = {}

FINANCIAL_KEYS = set([
  'a-shares',
  'h-shares',
  'shares',
  'sbv',  # static book value
  'p/sbv',
  'dbv',  # dynamic book value
  'p/dbv',
  'ttme', # trailing twelve month earning
  'p/ttme',
  'ttme3', # Forward 3 year earning.
  'p/ttme3',
  'dye', # dynamic yearly earning
  'p/dye',
  'sdv', # static dividend yield
  'sdv/p',
  'ddv', # dynamic dividend yield
  'ddv/p',
  'ddv', # dynamic dividend yield
  'ddv/p',
  'ah-ratio',
  'cross-share', # hold shares of other company in the format of 'stock / per self stock, name'
  'tax-rate',
  'start-date', # 固定收益类本周起计息日
  'interest-rate', # 固定收益类年化利率
  'old-rate', # 固定收益类当前年化利率

  'p/dividend',  # 当期分红
  'p/dividend3',  # 未来3年平均每年分红

  'book-value',
  'p/book-value',

  'bv3',  # 3年后的book value
  'p/bv3',

  'worst-book-value',
  'p/worst-book-value',
  'roe3',
])

GD_CLIENT = None

FINANCAIL_DATA_BASE = collections.defaultdict(dict)

FINANCAIL_DATA_ADVANCE = collections.defaultdict(dict)

STOCK_INFO = collections.defaultdict(dict)

MACRO_DATA = {}

ACCOUNT_INFO = {
  'a': {
    'account': 'china-a',
    'adjust': 0,
    'currency': 'cny',
    'support-currencies': ['cny'],
    'investment': 0.0,
    'market-value': 0.0,
    'cash': 0.0,
    'margin-ratio': 1.0,
    'margin-requirement': 0.0,
    'cushion-rate': 0.0,
    'cash-flow': [],
    'dividend': 0,
    'interest-loss': 0,
    'margin-interest': 0,
    'txn-fee': 0,
    'tax': 0,
    'holding-shares': collections.defaultdict(int),
    'buying-power': 0,
    'holding-percent': collections.defaultdict(float),
    'holding-value': collections.defaultdict(float),
    'holding-percent-all': collections.defaultdict(float),
  },
  'ib': {
    'tax': 0,
    'adjust': 0,
    'account': 'us-ib',
    'currency': 'usd',
    'support-currencies': ['usd', 'jpy', 'hkd'],
    'investment': 0.0,
    'market-value': 0.0,
    'cash': 0.0,
    'margin-ratio': 0.7,
    'margin-requirement': 0.0,
    'cushion-ratio': 0.0,
    'cash-flow': [],
    'dividend': 0,
    'interest-loss': 0,
    'margin-interest': 0,
    'txn-fee': 0,
    'holding-shares': collections.defaultdict(int),
    'buying-power': 0,
    'holding-percent': collections.defaultdict(float),
    'holding-value': collections.defaultdict(float),
    'holding-percent-all': collections.defaultdict(float),
  },
  'schwab': {
    'tax': 0,
    'adjust': 0,
    'account': 'us-schwab',
    'currency': 'usd',
    'support-currencies': ['usd', 'jpy', 'hkd'],
    'investment': 0.0,
    'market-value': 0.0,
    'cash': 0.0,
    'margin-ratio': 0.7,
    'margin-requirement': 0.0,
    'cushion-ratio': 0.0,
    'cash-flow': [],
    'dividend': 0,
    'interest-loss': 0,
    'margin-interest': 0,
    'txn-fee': 0,
    'holding-shares': collections.defaultdict(int),
    'buying-power': 0,
    'holding-percent': collections.defaultdict(float),
    'holding-value': collections.defaultdict(float),
    'holding-percent-all': collections.defaultdict(float),
  },
  '401k': {
    'adjust': 0,
    'account': 'us-401k',
    'currency': 'usd',
    'support-currencies': ['usd'],
    'investment': 0.0,
    'market-value': 0.0,
    'cash': 0.0,
    'margin-ratio': 1.0,
    'margin-requirement': 0.0,
    'cushion-ratio': 0.0,
    'cash-flow': [],
    'dividend': 0,
    'interest-loss': 0,
    'margin-interest': 0,
    'txn-fee': 0,
    'holding-shares': collections.defaultdict(int),
    'buying-power': 0,
    'holding-percent': collections.defaultdict(float),
    'holding-value': collections.defaultdict(float),
    'holding-percent-all': collections.defaultdict(float),
  },
}

MIN_TXN_PERCENT = 0.01
MAX_TXN_PERCENT = 0.07

MAX_PERCENT_PER_STOCK = 0.20

MIN_CASH_RATIO = -0.1

CATEGORIZED_STOCKS = collections.defaultdict(dict)

WWW_ROOT = '/var/www'

REGEX_TO_CATE = {
  '.+A$': '分级A',
}

#----------Begining of global variables------------------

def IsLambda(v):
  return isinstance(v, type(lambda: None)) and v.__name__ == (lambda: None).__name__

def myround(x, n):
  if n == 0:
    return int(x)
  return round(x, n)

def myround(x, n):
  if n == 0:
    return int(x)
  return round(x, n)

def MergeDictTo(a, b):
  for k, v in a.items():
    if k not in b:
      b[k] = v
  return b
