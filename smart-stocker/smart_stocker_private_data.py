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
import logging

from table_printer import *
from smart_stocker_global import *
from smart_stocker_public_data import *

import json
import gspread
import oauth2client
#from oauth2client.client import SignedJwtAssertionCredentials
from oauth2client.service_account import ServiceAccountCredentials

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
    except Exception as e:
        raise Exception('Failed to parse financial value [%s] by type [%s] with exception %s'%(value_str, type_str, str(e)))

def LoginMyGoogle(google_account_filename):
    logging.info('Using credential file: {}'.format(google_account_filename)) 
    # json_key = json.load(open(google_account_filename))
    scope = ['https://spreadsheets.google.com/feeds']
    
    credentials = ServiceAccountCredentials.from_json_keyfile_name(google_account_filename, scope)
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
    key_to_column = { matrix[header][idx]: idx + 1 for idx in range(len(matrix[header]))}
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
        logging.info('Merging worksheet %s\n'%(ws.title.encode('utf-8')))
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

    stock_batch = []
    all_data = []

    for ws in worksheets:
        category = ws.title.encode('utf-8')
        logging.info('Processing category: %s\n'%(category))
        records, key_to_column = ParseWorkSheetHorizontal(ws, global_transformer = GetFinancialValue, transformers = {'code' : lambda x: x})
        for row in records:
            name = row.get('name', '')
            if name == '': continue
            if 'code' not in row:
              if name not in NAME_TO_CODE: continue
              row['code'] = NAME_TO_CODE[name]
            code, name = row['code'], row['name']
            if code == '': continue
            stock_batch.append(code)
            logging.info('Got categorized stock %s(%s)\n'%(name, code))
            MergeDictTo(row, FINANCAIL_DATA_BASE[code])
            MergeDictTo(row, STOCK_INFO[code])
            NAME_TO_CODE[name], CODE_TO_NAME[code] = code, name
            CATEGORIZED_STOCKS[category][code] = row
            if 'category' not in STOCK_INFO[code]:
                STOCK_INFO[code]['category'] = category
            if 'hcode' in row:
                NAME_TO_CODE[name + 'H'] = row['hcode']
                CODE_TO_NAME[row['hcode']] = name + 'H'
                STOCK_INFO[row['hcode']].update({
                    'market': 'hk',
                    'currency': 'hkd',
                    'acode': code,
                })
        all_data += [(ws, records, key_to_column)]

    PrefetchSinaStockList(stock_batch)
    for ws, records, key_to_column in all_data:
        row_idx = 1
        cells_to_update = []
        for row in records:
            row_idx += 1
            code = row.get('code', '')
            if code == '': continue
            if 'price' in row:
                pr = GetMarketPrice(code) 
                # HK stock
                if 'acode' in STOCK_INFO[code]: pr *= EX_RATE['hkd-cny']
                cell = ws.cell(row_idx, key_to_column['price'])
                cell.value = str(pr)
                cells_to_update.append(cell)
        ws.update_cells(cells_to_update)
            
def PrintData(names):
    tableMap = []
    header = [col for col in (FINANCIAL_KEYS - set(['name']))]
    header += ['name']
    for code in FINANCAIL_DATA_BASE.keys():
        data = FINANCAIL_DATA_BASE[code]
        if any([data['name'].find(name) != -1 for name in names]):
            tableMap.append(data)
    PrintTableMap(header, tableMap)

def GetAllStocks(gd_client):
    GetCategorizedStocks(gd_client)


if __name__ == "__main__":
    client = LoginMyGoogleWithFiles()
    GetAllStocks(gd_client)
    GetTransectionRecords(client)
    PrintData(','.join(sys.argv[1:]).split(','))
