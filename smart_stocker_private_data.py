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
    
def GetTransectionRecords(gd_client):
  if gd_client is None:
    return []
  try:
    feeds = gd_client.GetListFeed('0Akv9eeSdKMP0dHBzeVIzWTY1VUlQcFVKOWFBZkdDeWc', 'od6').entry
    rows = []
    for row in feeds:
      rows.append({key : row.custom[key].text.encode('utf-8') for key in row.custom.keys()})  
    return rows
  except Exception, e:
    sys.stderr.write('Failed to read transaction sheet. Exception ' + str(e) +'\n')
  return []

def LoginMyGoogleWithFiles():
 home = os.path.expanduser("~")
 return LoginMyGoogle(home + '/.smart-stocker-google-email.txt',
                      home + '/.smart-stocker-google-password.txt')

def GetStockPool(client):
  ws_key = '1Ita0nLCH5zpt6FgpZwOshZFXwIcNeOFvJ3ObGze2UBs'
  ws_id = 'ofub021'
  try:
    sys.stderr.write('Reading stock pull worksheet.\n')
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
  all_code = STOCK_INFO.keys()
  for code in all_code:
    info = STOCK_INFO[code]
    CODE_TO_NAME[code] = info['name']
    NAME_TO_CODE[info['name']] = code
    if 'hcode' in info:
      hcode = info['hcode']
      AH_PAIR[hcode] = code
      AH_PAIR[code] = hcode
      CODE_TO_NAME[hcode] = info['name'] + 'H'
      NAME_TO_CODE[CODE_TO_NAME[hcode]] = hcode
      STOCK_INFO[hcode] = {
        'name': CODE_TO_NAME[hcode],
        'currency': 'hkd',
      }
    if 'cb' in info:
      cb = info['cb']
      CODE_TO_NAME[cb] = info['name'] + '转债'
      NAME_TO_CODE[CODE_TO_NAME[cb]] = cb
      STOCK_INFO[cb] = {
        'name': CODE_TO_NAME[cb],
        'currency': info['currency']
      }
 
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
        if len(values) > 0 and values[0].find(': ') != -1:
          financial_data[financial_key] = float(values[0].split(': ')[1].replace(',', ''))
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
  
