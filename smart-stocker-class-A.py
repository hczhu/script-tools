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

def GetNAV(code):
  return GetValueFromUrl(
  'http://www.cninfo.com.cn/information/fund/netvalue/%s.html'%(code),
  ['<td', '单位资产净值',
   '<tr>', '<td', '<td', '>'],
  '<', float, throw_exp = True, default_value = -100.0, encoding = 'gbk')

if __name__ == "__main__":
  client = LoginMyGoogleWithFiles()
  ws = client.open_by_key('1ER4HZD-_UUZF7ph5RkgPu8JftY9jwFVJtpd2tUwz_ac').get_worksheet(0)
  table = ParseWorkSheetHorizontal(ws, global_transformer = GetFinancialValue, transformers = {'code' : lambda x: x, 'class-b': lambda x: x})
  row_idx = 1
  nav_column = 'D'
  parent_nav_column = 'C'
  price_column = 'B'
  for row in table:
    row_idx += 1
    code = row['code']
    if code == '': continue
    if 'class-b' not in row:
      sys.stderr.write('No class-b code for class-a %s(%s)\n'%(code, row['name']))
      continue

    global STOCK_INFO  
    STOCK_INFO[code] = row
    pr = GetMarketPrice(code)
    if pr <= 0.4:
      sys.stderr.write('Failed to get price for %s(%s)\n'%(code, row['name'])) 
      continue
    ws.update_acell(price_column + str(row_idx), str(pr))
    if len(sys.argv) > 1:
      try:
        a_nav = GetNAV(code)
        time.sleep(5)
        b_nav = GetNAV(row['class-b'])
        time.sleep(5)
      except:
        sys.stderr.write('Failed to get NAV for %s(%s)\n'%(code, row['name'])) 
        continue
      print '%s(%s - %s) nav: %.4f B: %.4f parent %.4f price = %.4f\n'%(row['name'], code, row['class-b'], a_nav, b_nav, (a_nav + b_nav) / 2, pr)
      ws.update_acell(nav_column + str(row_idx), str(a_nav))
      ws.update_acell(parent_nav_column + str(row_idx), str((a_nav + b_nav) / 2))
    
