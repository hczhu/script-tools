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

#----------------------Template-----------------------------

HTML_TEMPLATE = """
<!--
You are free to copy and use this sample in accordance with the terms of the
Apache license (http://www.apache.org/licenses/LICENSE-2.0.html)
-->

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
    <title>
      Google Visualization API Sample
    </title>
    <script type="text/javascript" src="https://www.google.com/jsapi"></script>
    <script type="text/javascript">
      google.load('visualization', '1', {packages: ['corechart']});
    </script>
    <script type="text/javascript">
      function drawVisualization() {
        %s
      }
      google.setOnLoadCallback(drawVisualization);
    </script>
  </head>
  <body style="font-family: Arial;border: 0 none;">
    %s
  </body>
</html>
"""

FUNCTION_TEMPLATE = """
        {
          // Create and populate the data table.
          var data = new google.visualization.DataTable();
          data.addColumn('date', 'Date'); // Implicit series 1 data col.
          data.addColumn('number', '%s'); // Implicit domain label col.
          data.addColumn({type:'string', role:'annotation'}); // annotation role col.
          data.addColumn({type:'string', role:'annotationText'}); // annotationText col.
          data.addRows([
              %s
              ]); 
          // Create and draw the visualization.
          new google.visualization.LineChart(document.getElementById('%s')).draw(
              data,
              {
               curveType: "function",
               lineWidth: 2,
               pointSize: 5,
               legend: { position: 'bottom' },
               vAxis: {
                        minValue: %f,
                        maxValue: %f,
                        title: 'Price(%s)',
                      },
               explorer: {
                           actions: 'dragToZoom',
                           axis: 'horizontal',
                         }
              });
      }
"""

DIV_TEMPLATE = """
<div id="%s" style="width: 90%%, height: 600px;"></div>

"""

# -------------- End of template --------------------------

EX_RATE = {
}
 
CURRENCIES = ['usd', 'cny', 'hkd', 'jpy']

CURRENCY = 'usd'

MIN_MP = 0.001

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
    'currency': 'cny',
    'support-currencies': ['cny'],
    'investment': 0.0,
    'market-value': 0.0,
    'free-cash': 0.0,
    'sma-discount': 0.0,
    'sma': 0.0,
    'sma-ratio': 0.0,
    'min-sma-ratio': 0.0,
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
  'ib': {
    'account': 'us-ib',
    'currency': 'usd',
    'support-currencies': ['usd', 'jpy', 'hkd'],
    'investment': 0.0,
    'market-value': 0.0,
    'free-cash': 0.0,
    'sma-discount': 0.8,
    'sma': 0.0,
    'sma-ratio': 0.0,
    'min-sma-ratio': 0.2,
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
    'account': 'us-schwab',
    'currency': 'usd',
    'support-currencies': ['usd'],
    'investment': 0.0,
    'market-value': 0.0,
    'free-cash': 0.0,
    'sma-discount': 0.0,
    'sma': 0.0,
    'sma-ratio': 0.0,
    'min-sma-ratio': 0.0,
    'cash-flow': [],
    'dividend': 0,
    'interest-loss': 0,
    'margin-interest': 0,
    'txn-fee': 0,
    'holding-shares': collections.defaultdict(int),
    'buying-power': 0,
    'holding-percent': collections.defaultdict(float),
    'holding-percent-all': collections.defaultdict(float),
    'holding-value': collections.defaultdict(float),
  },
}

MIN_TXN_PERCENT = 0.0095

CATEGORIZED_STOCKS = collections.defaultdict(list)

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
