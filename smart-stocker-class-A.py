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
import os.path
import numpy

from table_printer import *
from smart_stocker_private_data import *
from smart_stocker_public_data import *
from smart_stocker_global import *

import gspread

def GetParentCode(a_code):
  return GetValueFromUrl(
            'http://www.jisilu.cn/data/sfnew/detail/%s'%(a_code),
            feature_str = ['<title>股票分级 - '],
            end_str = ' ',
            func = lambda s: s,
            throw_exp = True,
            default_value = '')

def GetRealNAV(code):
  return GetValueFromUrl(
    'http://www.howbuy.com/fund/ajax/gmfund/valuation/valuationnav.htm?jjdm=%s'%(code),
    ['<span class=', '>'], '<', float, throw_exp = True, default_value = -100.0)

if __name__ == "__main__":
  client = LoginMyGoogleWithFiles()
  ws = client.open_by_key('1ER4HZD-_UUZF7ph5RkgPu8JftY9jwFVJtpd2tUwz_ac').get_worksheet(0)
  table = ParseWorkSheetHorizontal(ws, global_transformer = GetFinancialValue, transformers = {'code' : lambda x: x, 'class-b': lambda x: x, 'parent-code': lambda x: x})
  row_idx = 1
  price_column = 'B'
  nav_column = 'C'
  parent_nav_column = 'D'
  parent_code_column = 'E'
  premium_column = 'F'
  for row in table:
    row_idx += 1
    code = row['code']
    if code == '': continue
    if 'class-b' not in row:
      sys.stderr.write('No class-b code for class-a %s(%s)\n'%(code, row['name']))
      continue

    b_code = row['class-b']
    global STOCK_INFO  
    STOCK_INFO[code] = row
    try:
      pr = GetMarketPrice(code)
      if pr <= 0.4:
        sys.stderr.write('Failed to get price for %s(%s)\n'%(code, row['name'])) 
        continue
      ws.update_acell(price_column + str(row_idx), str(pr))
      parent_code = row['parent-code']
      if parent_code == '':
        sys.stderr.write('existing parent %s for %s\n'%(parent_code, code))
        parent_code = GetParentCode(code)
        sys.stderr.write('Got parent %s for %s\n'%(parent_code, code))
        ws.update_acell(parent_code_column + str(row_idx), parent_code)
      parent_nav = GetRealNAV(parent_code)
      time.sleep(0)
      a_nav = GetRealNAV(code)
      time.sleep(0)
      print '%s(%s - %s) nav: %.4f parent %.4f price = %.4f\n'%(row['name'], code, row['class-b'], a_nav, parent_nav, pr)
      ws.update_acell(nav_column + str(row_idx), str(a_nav))
      ws.update_acell(parent_nav_column + str(row_idx), str(parent_nav))
      STOCK_INFO[b_code] = row
      b_price = GetMarketPrice(b_code)
      if b_price > 0.01:
        premium = (pr + b_price) / (2*parent_nav) - 1
        ws.update_acell(premium_column + str(row_idx), str(premium))
    except Exception, e:
      sys.stderr.write('Failed to fill %s(%s) [%s]\n'%(row['name'], code, str(e)))
    
