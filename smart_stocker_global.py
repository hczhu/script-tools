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

CODE_TO_NAME = {
}

NAME_TO_CODE = {}

TOTAL_CAPITAL = collections.defaultdict(int)

TOTAL_INVESTMENT = {
  'cny': 0, 'usd': 0, 'hkd': 0, 'jpy': 0,
}
NET_ASSET_BY_CURRENCY = collections.defaultdict(int)

TOTAL_TRANSACTION_FEE = collections.defaultdict(float)

TOTAL_MARKET_VALUE = collections.defaultdict(int) 

HOLDING_PERCENT = collections.defaultdict(float)

HOLDING_SHARES = collections.defaultdict(int)

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
  'dye', # dynamic yearly earning
  'p/dye',
  'sdv', # static dividend yield
  'sdv/p',
  'ddv', # dynamic dividend yield
  'ddv/p',
  'ah-ratio',
  'p/sbvadv', # p/sbv after dividend.
  'p/dbvadv', # p/dbv after dividend.
  'cross-share', # hold shares of other company in the format of 'stock / per self stock, name'
  'p/cross-share', # hold shares of other company in the format of 'stock / per self stock, name'
  'tax-rate',
  'start-date', # 固定收益类本周起计息日
  'interest-rate', # 固定收益类年化利率
  'old-rate', # 固定收益类当前年化利率
])

GD_CLIENT = None

FINANCAIL_DATA_BASE = collections.defaultdict(dict)

FINANCAIL_DATA_ADVANCE = collections.defaultdict(dict)

STOCK_INFO = collections.defaultdict(dict)

CAPITAL_INFO = collections.defaultdict(dict)

MIN_SMA_RATIO = {
  'cny': 0.0,
  'usd': 0.1,
}

MACRO_DATA = {}

SMA_DISCOUNT = {
  'cny': 0.0,
  'usd': 0.5,
}

ASSET_INFO = collections.defaultdict(dict)

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
