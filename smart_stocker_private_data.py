#!/usr/bin/python
# -*- coding: utf-8 -*-

import collections
import gdata.docs
import gdata.docs.service
import gdata.spreadsheet.service
import sys
import datetime
import time
import os.path
import re
import dateutil.parser

from table_printer import *
from smart_stocker_global import *

def LoginMyGoogle(email_file, password_file):
  # Connect to Google
  gd_client = gdata.spreadsheet.service.SpreadsheetsService()
  gd_client.email = file(email_file).readline().strip()
  gd_client.password = file(password_file).readline().strip()
  gd_client.source = 'smart-stocker'
  try:
    gd_client.ProgrammaticLogin()
    return gd_client
  except Exception, e:
    sys.stderr.write('Failed to login google account. Exception ' + str(e) +'\n')
  return None
    
def GetTable(gd_client, table_key, worksheet_key = 'od6'):
  if gd_client is None:
    return []
  try:
    feeds = gd_client.GetListFeed(table_key, worksheet_key)
    title= feeds.title.text
    entries = feeds.entry
    rows = []
    for row in entries:
      rows.append({key : row.custom[key].text for key in row.custom.keys()})
      for key in rows[-1].keys():
        if rows[-1][key] is not None:
          rows[-1][key] = rows[-1][key].encode('utf-8')
    return rows
  except Exception, e:
    sys.stderr.write('Failed to read worksheet [%s] with exception [%s]\n'%(title, str(e)))
  return []

def GetTransectionRecords(gd_client):
  table_key, worksheet_key = '0Akv9eeSdKMP0dHBzeVIzWTY1VUlQcFVKOWFBZkdDeWc', 'od6'
  return GetTable(gd_client, table_key, worksheet_key)

def GetFinancialValue(value_str):
  integer_re = '0|([1-9][0-9]*)'
  float_re = '(%s)|((%s)?\.[0-9]+)'%(integer_re, integer_re)
  type_str = ''
  try:
    if re.match('[1-9][0-9]{0,2}(,[0-9]{3})*$', value_str) is not None:
      type_str = 'deciml'
      return float(value_str.replace(',', ''))
    elif re.match('(%s)$'%(float_re), value_str) is not None:
      type_str = 'float'
      return float(value_str)
    elif re.match('(%s)%%$'%(float_re), value_str) is not None:
      type_str = 'percent'
      return float(value_str[0:-1]) / 100.0
    elif re.match('[0-9]{1,2}/[0-9]{1,2}/20[0-9]{2,2}%$', value_str) is not None:
      type_str = 'date'
      return dateutil.parser.parse(value_str).date()
    else:
      type_str = 'string'
      return value_str
  except Exception, e:
    raise Exception('Failed to parse financial value [%s] by type [%s] with exception %s'%(value_str, type_str, str(e)))

def LoginMyGoogleWithFiles():
  home = os.path.expanduser("~")
  return LoginMyGoogle(home + '/.smart-stocker-google-email.txt',
                       home + '/.smart-stocker-google-password.txt')

def GetStockPool(client):
  ws_key = '1Ita0nLCH5zpt6FgpZwOshZFXwIcNeOFvJ3ObGze2UBs'
  ws_id = 'ofub021'
  try:
    sys.stderr.write('Reading stock pool worksheet.\n')
    feeds = client.GetListFeed(ws_key, ws_id).entry
    for row in feeds:
      info = {key : row.custom[key].text for key in row.custom.keys()}
      assert 'code' in info and info['code'] is not None
      for key in info.keys():
        if info[key] is None: del info[key]
        else: info[key] = info[key].encode('utf-8')
      STOCK_INFO[info['code']] = info
  except Exception, e:
    sys.stderr.write('Failed to read stock pool worksheet. Exception ' + str(e) +'\n')
  GetClassA(client)
  all_code = STOCK_INFO.keys()
  for code in all_code:
    info = STOCK_INFO[code]
    CODE_TO_NAME[code] = info['name']
    NAME_TO_CODE[info['name']] = code
    if 'hcode' in info:
      hcode = info['hcode']
      CODE_TO_NAME[hcode] = info['name'] + 'H'
      NAME_TO_CODE[CODE_TO_NAME[hcode]] = hcode
      STOCK_INFO[hcode] = {
        'name': CODE_TO_NAME[hcode],
        'currency': 'hkd',
        'acode': code,
        'market': 'hk',
      }
    if 'cb' in info:
      cb = info['cb']
      CODE_TO_NAME[cb] = info['name'] + '转债'
      NAME_TO_CODE[CODE_TO_NAME[cb]] = cb
      STOCK_INFO[cb] = {
        'name': CODE_TO_NAME[cb],
        'currency': info['currency'],
        'market': info['market'],
      }
 
def GetClassA(client):
  table_key = '1ER4HZD-_UUZF7ph5RkgPu8JftY9jwFVJtpd2tUwz_ac'
  sys.stderr.write('Reading class A table.\n')
  table = GetTable(client, table_key)
  for row in table:
    code = row['code']
    STOCK_INFO[code] = row
    for key in STOCK_INFO[code].keys():
      STOCK_INFO[code][key] = GetFinancialValue(STOCK_INFO[code][key])

def GetFinancialData(client):
  ws_key = '14pJTivMAHd-Gqpc9xboV4Kl7WbK51TrOc9QzgXBFRgw'
  worksheets = client.GetWorksheetsFeed(ws_key).entry
  for ws in worksheets:
    sys.stderr.write('Reading worksheet: %s\n'%(ws.title.text))
    try:
      name = ws.title.text.strip()
      if name not in NAME_TO_CODE:
        raise Exception('name: [%s] not in stock pool'%(name))
      code = NAME_TO_CODE[name]
      financial_data = FINANCAIL_DATA_BASE[code]
      financial_data['name'] = name
      ws_id = ws.id.text.split('/')[-1]
      time.sleep(1)
      feeds = client.GetListFeed(ws_key, ws_id).entry
      for row in feeds:
        if row.title is None: continue
        financial_key = row.title.text
        if financial_key not in FINANCIAL_KEYS: continue
        values = row.content.text.split(', ')
        financial_value = GetFinancialValue(values[0].split(': ')[1])
        if financial_key == 'cross-share':
          assert len(values) == 2
          if 'cross-share' not in financial_data:
            financial_data['cross-share'] = []
          financial_data['cross-share'] += [(financial_value, NAME_TO_CODE[values[1].split(': ')[1]])]
        else:
          financial_data[financial_key] = financial_value
      sys.stderr.write('Basic financial data for %s:%s\n'%(name, str(financial_data)))
    except Exception, e:
      sys.stderr.write('Failed to get data from worksheet: %s with exception [%s]\n'%(ws.title.text, str(e)))

def PrintData(names):
  tableMap = []
  header = [col for col in (FINANCIAL_KEYS - set(['name']))]
  header += ['name']
  for code in FINANCAIL_DATA_BASE.keys():
    data = FINANCAIL_DATA_BASE[code]
    if any([data['name'].find(name) != -1 for name in names]):
      tableMap.append(data)
  PrintTableMap(header, tableMap)

if __name__ == "__main__":
  client = LoginMyGoogleWithFiles()
  GetStockPool(client)
  GetFinancialData(client)
  PrintData(','.join(sys.argv[1:]).split(','))
 
