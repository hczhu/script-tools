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
from smart_stocker_public_data import *

import json
import gspread
import oauth2client
from oauth2client.client import SignedJwtAssertionCredentials

def GetFinancialValue(value_str):
  integer_re = '-?(0|([1-9][0-9]*))'
  float_re = '-?((%s)|((%s)?\.[0-9]+))'%(integer_re, integer_re)
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
    elif re.match('[0-9]{1,2}/[0-9]{1,2}/20[0-9]{2,2}$', value_str) is not None:
      type_str = 'date'
      return dateutil.parser.parse(value_str).date()
    else:
      type_str = 'string'
      return value_str
  except Exception, e:
    raise Exception('Failed to parse financial value [%s] by type [%s] with exception %s'%(value_str, type_str, str(e)))

def LoginMyGoogle(google_account_filename):
  json_key = json.load(open(google_account_filename))
  scope = ['https://spreadsheets.google.com/feeds']
  
  credentials = SignedJwtAssertionCredentials(json_key['client_email'], json_key['private_key'], scope)
  return gspread.authorize(credentials)

def LoginMyGoogleWithFiles():
  home = os.path.expanduser("~")
  return LoginMyGoogle(home + '/.smart-stocker-google-api.json')
    
def ParseWorkSheetHorizontal(worksheet, header = 0, skip_rows = [], global_transformer = lambda x: x, transformers = {}):
  matrix = worksheet.get_all_values()
  row_count = len(matrix)
  skip_row_set = set([row if row >= 0 else row_count + row for row in skip_rows])
  skip_row_set |= set([header])
  GetTransformer = lambda key: transformers[key] if key in transformers else global_transformer
  keys = [value.strip().lower() for value in matrix[header]]
  key_to_column = { matrix[header][idx]: chr(idx + ord('A')) for idx in range(len(matrix[header]))}
  records = []
  for idx in range(row_count):
    if idx in skip_row_set: continue
    record = dict(zip(keys, matrix[idx]))
    for key, value in record.items():
      record[key] = GetTransformer(key)(value.strip().encode('utf-8'))
    records.append(record)
  return records, key_to_column

def ParseWorkSheetVertical(worksheet, global_transformer = lambda x: x, transformers = {}):
  GetTransformer = lambda key: transformers[key] if key in transformers else global_transformer
  matrix = worksheet.get_all_values()
  record = collections.defaultdict(list)

  for row in matrix:
    record[row[0].lower()] += filter(lambda x: x != '', map(lambda x: x.encode('utf-8'), row[1:]))

  record = {key : map(GetTransformer(key), value) for key, value in record.items()}
  record = {key : value[0] if len(value) == 1 else value for key, value in record.items()}
  return record

def MergeAllHorizontalWorkSheets(gd_client, ss_key, primary_key, value_transformer = lambda x: x):
  records = collections.defaultdict(dict)
  worksheets = gd_client.open_by_key(ss_key).worksheets()
  for ws in worksheets:
    sys.stderr.write('Merging worksheet %s\n'%(ws.title.encode('utf-8')))
    rows, _ = ParseWorkSheetHorizontal(ws, global_transformer = value_transformer)
    for row in rows:
      if primary_key not in row: continue
      for key, value in row.items():
        records[row[primary_key]][key] = value
  return records

def GetTransectionRecords(gd_client):
  ss_key = '1oxtcfl2V4ff3eUMW4954IChpx9eFAoB83QMrZERPSgA'
  return ParseWorkSheetHorizontal(gd_client.open_by_key(ss_key).get_worksheet(0))[0]

def GetCategorizedStocks(gd_client):
  ss_key = '1VNmr6UVL1zA07fKWUgHc64eXYEArdg4GzkcEiLCria4'
  worksheets = gd_client.open_by_key(ss_key).worksheets()
  for ws in worksheets:
    category = ws.title.encode('utf-8')
    sys.stderr.write('Processing category: %s\n'%(category))
    records, key_to_column = ParseWorkSheetHorizontal(ws, global_transformer = GetFinancialValue, transformers = {'code' : lambda x: x})
    row_idx = 1
    for row in records:
      row_idx += 1
      if 'name' in row:
        if 'code' not in row:
          if row['name'] not in NAME_TO_CODE: continue
          row['code'] =  NAME_TO_CODE[row['name']]
        code, name = row['code'], row['name']
        if code == '' or name == '': continue
        sys.stderr.write('Got categorized stock %s(%s)\n'%(name, code))
        MergeDictTo(row, FINANCAIL_DATA_BASE[code])
        MergeDictTo(row, STOCK_INFO[code])
        NAME_TO_CODE[name], CODE_TO_NAME[code] = code, name
        CATEGORIZED_STOCKS[category] += [code]
        STOCK_INFO[code]['category'] = category
        if 'price' in row:
          pr = GetMarketPrice(code) 
          # HK stock
          if 'acode' in STOCK_INFO[code]: pr *= EX_RATE['hkd-cny']
          ws.update_acell(key_to_column['price'] + str(row_idx), str(pr))
        if 'holding-percent' in row:
          ws.update_acell(key_to_column['holding-percent'] + str(row_idx), str(ACCOUNT_INFO['ALL']['holding-percent'].get(code, 0)))
      
def GetStockPool(gd_client):
  ss_key = '1Ita0nLCH5zpt6FgpZwOshZFXwIcNeOFvJ3ObGze2UBs'
  stocks = MergeAllHorizontalWorkSheets(gd_client, ss_key, 'code')
  GetClassA(gd_client)
  for code in stocks.keys():
    info = stocks[code]
    for key, value in info.items():
      if value == '': del info[key]
    STOCK_INFO[code] = info
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
  ws = client.open_by_key('1ER4HZD-_UUZF7ph5RkgPu8JftY9jwFVJtpd2tUwz_ac').get_worksheet(0)
  table, _ = ParseWorkSheetHorizontal(ws, global_transformer = GetFinancialValue, transformers = {'code' : lambda x: x})
  for row in table:
    code = row['code']
    if code == '': continue
    FINANCAIL_DATA_BASE[code] = STOCK_INFO[code] = row
    CODE_TO_NAME[code] = row['name']
    NAME_TO_CODE[row['name']] = code

def GetBankData(client):
  sys.stderr.write('Reading bank data.\n')
  bank_data = MergeAllHorizontalWorkSheets(client, '1xw6xPiyE6zOmbHmNo9L2HCPknidj4vPdwU9PubZZtCs', 'name', GetFinancialValue)
  sys.stderr.write('Got bank data:\n%s\n'%(str(bank_data)))
  for name, value in bank_data.items():
    if name not in NAME_TO_CODE:
      sys.stderr.write('unknown stock name: %s\n'%(name))
      continue
    sys.stderr.write('Added financial data for %s(%s)\n'%(name, NAME_TO_CODE[name]))
    MergeDictTo(value, FINANCAIL_DATA_BASE[NAME_TO_CODE[name]])

def GetFinancialData(client):
  ss_key = '14pJTivMAHd-Gqpc9xboV4Kl7WbK51TrOc9QzgXBFRgw'
  worksheets = client.open_by_key(ss_key).worksheets()
  for ws in worksheets:
    sys.stderr.write('Reading worksheet: %s\n'%(ws.title.encode('utf-8')))
    name = ws.title.strip().encode('utf-8')
    if name not in NAME_TO_CODE:
      raise Exception('name: [%s] not in stock pool'%(name))
    code = NAME_TO_CODE[name]
    FINANCAIL_DATA_BASE[code] = ParseWorkSheetVertical(ws, GetFinancialValue)
    FINANCAIL_DATA_BASE[code]['name'] = name
    if 'cross-share' in FINANCAIL_DATA_BASE[code]:
      cross_share =  FINANCAIL_DATA_BASE[code]['cross-share'];
      FINANCAIL_DATA_BASE[code]['cross-share'] = {cross_share[idx + 1] : cross_share[idx] for idx in range(0, len(cross_share), 2)} 

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
  GetTransectionRecords(client)
  GetFinancialData(client)
  GetBankData(client)
  PrintData(','.join(sys.argv[1:]).split(','))
 
