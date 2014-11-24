#!/usr/bin/python
# -*- coding: utf-8 -*-

from collections import defaultdict
import gdata.docs
import gdata.docs.service
import gdata.spreadsheet.service
import sys
import time
from os.path import expanduser

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
      rows.append({key : row.custom[key].text for key in row.custom.keys()})  
    return rows
  except Exception, e:
    sys.stderr.write('Failed to read transaction sheet. Exception ' + str(e) +'\n')
  return []

def LoginMyGoogleWithFiles():
 home = expanduser("~")
 return LoginMyGoogle(home + '/.smart-stocker-google-email.txt',
                      home + '/.smart-stocker-google-password.txt')
 
def GetFinancialData(client):
  ws_key = '14pJTivMAHd-Gqpc9xboV4Kl7WbK51TrOc9QzgXBFRgw'
  worksheets = client.GetWorksheetsFeed(ws_key).entry
  for ws in worksheets:
    sys.stderr.write('Reading work sheet: %s\n'%(ws.title.text))
    infos = ws.title.text.split(' ')
    assert len(infos) > 1
    financial_data = FINANCAIL_DATA[infos[1]]
    financial_data['code'] = infos[1]
    financial_data['name'] = infos[0]
    if len(infos) > 2: financial_data['hcode'] = infos[2]
    ws_id = ws.id.text.split('/')[-1]
    feeds = client.GetListFeed(ws_key, ws_id).entry
    for row in feeds:
      if row.title is None: continue
      financial_key = row.title.text
      if financial_key not in FINANCIAL_KEYS: continue
      values = row.content.text.split(', ')
      if len(values) > 0 and values[0].find(': ') != -1:
        financial_data[financial_key] = float(values[0].split(': ')[1].replace(',', ''))

def PrintData(names):
  tableMap = []
  header = [col for col in (SHOW_KEYS - set(['name']))]
  header += ['name']
  for code in FINANCAIL_DATA.keys():
    data = FINANCAIL_DATA[code]
    if any([data['name'].find(name) != -1 for name in names]):
      tableMap.append(data)
  PrintTableMap(header, tableMap)

if __name__ == "__main__":
  client = LoginMyGoogleWithFiles()
  GetFinancialData(client)
  print FINANCAIL_DATA
  PrintData(','.join(sys.argv[1:]).split(','))
  
