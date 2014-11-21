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
  'USD-USD': 1.0,
  'USD-RMB': 6.11,
  'USD-HKD': 7.75,
  'USD-YEN': 116,
}

CURRENCY = 'USD'

def InitExRate():
  all_currencies = [pr.split('-')[1] for pr in EX_RATE.keys()]
  for pr in EX_RATE.keys():
    currencies = pr.split('-')
    assert(len(currencies) == 2)
    EX_RATE[currencies[1] + '-' + currencies[0]] = 1.0 / EX_RATE[pr]
  for a in all_currencies:
    for b in all_currencies:
      EX_RATE[a + '-' + b] = EX_RATE[a + '-' + CURRENCY] * EX_RATE[CURRENCY + '-' + b]

CROSS_SHARE = {
  # The amount of Alibaba stocks Yahoo holds
  'Yahoo-Alibaba': 384 * 10**6,
}

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
  'RMB': 'RMB',
  'USD': 'USD',
  'HKD': 'HKD',
}

NAME_TO_CODE = {
}

AH_PAIR = {
  '601808': '02883',
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
  '000666': '00350',
  '600028': '00386',
  '000002': '02202',
}

STOCK_CURRENCY = {
  ':DeNA': 'YEN',
}

TOTAL_CAPITAL = defaultdict(int)

TOTAL_INVESTMENT = {
  'RMB': 0, 'USD': 0, 'HKD': 0, 'YEN': 0,
}
NET_ASSET_BY_CURRENCY = defaultdict(int)

TOTAL_TRANSACTION_FEE = defaultdict(float)

TOTAL_MARKET_VALUE = defaultdict(int) 

HOLDING_PERCENT = defaultdict(float)

HOLDING_SHARES = defaultdict(int)

NET_ASSET = 0.0

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
