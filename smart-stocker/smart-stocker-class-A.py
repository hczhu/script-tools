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
            default_value = ''), GetValueFromUrl(
            'http://www.jisilu.cn/data/sfnew/detail/%s'%(a_code),
            feature_str = ['<thead>', '仓位', '</tr>'] + ['<td'] * 6 + ['>'],
            end_str = '<',
            func = GetFinancialValue,
            throw_exp = True,
            default_value = 1.0)
        
def GetRealNAV(code, stock_percent = 1.0):
  inflated_nav =  GetValueFromUrl(
    'http://www.howbuy.com/fund/ajax/gmfund/valuation/valuationnav.htm?jjdm=%s'%(code),
    ['<span class=', '>'], '<', float, throw_exp = True, default_value = -100.0)
  inflated_increase = GetValueFromUrl(
    'http://www.howbuy.com/fund/ajax/gmfund/valuation/valuationnav.htm?jjdm=%s'%(code),
    ['<span class='] * 2 + ['>'] , '<', float, throw_exp = True, default_value = -100.0)
  sys.stderr.write('realtime estimated nav = %.3f index increase = %.4f stock percent = %.3f\n'%(inflated_nav, inflated_increase, stock_percent))
  return inflated_nav - inflated_increase * (1 - stock_percent)

if __name__ == "__main__":
  client = LoginMyGoogleWithFiles()
  ws = client.open_by_key('1ER4HZD-_UUZF7ph5RkgPu8JftY9jwFVJtpd2tUwz_ac').get_worksheet(0)
  table, _ = ParseWorkSheetHorizontal(ws, global_transformer = GetFinancialValue, transformers = {'code' : lambda x: x, 'class-b': lambda x: x, 'parent-code': lambda x: x})
  row_idx = 1
  price_column = 'B'
  nav_column = 'C'
  parent_nav_column = 'D'
  parent_code_column = 'E'
  parent_stock_hold_percent = 'F'
  premium_column = 'G'
  for row in table:
    sys.stderr.write('------------------------\n')
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
      parent_code, parent_percent = row['parent-code'], row['parent-percent']
      if len(sys.argv) == 1:
        parent_code, parent_percent = GetParentCode(code)
        ws.update_acell(parent_code_column + str(row_idx), parent_code)
        ws.update_acell(parent_stock_hold_percent + str(row_idx), parent_percent)
      sys.stderr.write('Got parent %s for %s with percent %.3f\n'%(parent_code, code, parent_percent))
      parent_nav = GetRealNAV(parent_code, parent_percent)
      time.sleep(0)
      a_nav = GetRealNAV(code)
      time.sleep(0)
      ws.update_acell(nav_column + str(row_idx), str(a_nav))
      ws.update_acell(parent_nav_column + str(row_idx), str(parent_nav))
      STOCK_INFO[b_code] = row

      pr = GetMarketPrice(code)
      print '%s(%s - %s) nav: %.4f parent %.4f price = %.4f\n'%(row['name'], code, row['class-b'], a_nav, parent_nav, pr)
      if pr <= 0.4:
        sys.stderr.write('Failed to get price for %s(%s)\n'%(code, row['name'])) 
        continue
      ws.update_acell(price_column + str(row_idx), str(pr))
      b_price = GetMarketPrice(b_code)
      if b_price > 0.01:
        premium = (pr + b_price) / (2 * parent_nav) - 1
        ws.update_acell(premium_column + str(row_idx), str(premium))
    except Exception, e:
      sys.stderr.write('Failed to fill %s(%s) [%s]\n'%(row['name'], code, str(e)))
    
