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

def GetNAV(code):
  return GetValueFromUrl('http://jingzhi.funds.hexun.com/%s.shtml'%(code),
                  ['最新净值', '<font>'], '<', float, False, default_value = 100.0)

client = LoginMyGoogleWithFiles()
table_key = sys.argv[1] if len(sys.argv) > 1 else '1ER4HZD-_UUZF7ph5RkgPu8JftY9jwFVJtpd2tUwz_ac'

table = GetTable(client, table_key)

for row in table:
  code = row['code']
  nav = row['nav'] = GetNAV(code)
  last_rate = GetFinancialValue(row['last-rate'])
  last_date = datetime.date.today() - datetime.timedelta(
                days = int((nav - 1.0) / last_rate * 365))
  row['last-date'] = last_date.strftime('%m/%d/%Y')


header = list(set(table[0].keys()) - set(['name'])) + ['name']

print '\n'.join([row['last-date'] for row in table])

PrintTableMap(header, table)
