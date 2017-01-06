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

client = LoginMyGoogleWithFiles()
table_key = sys.argv[1]

table = collections.defaultdict(dict)

worksheets = client.GetWorksheetsFeed(table_key).entry
for ws in worksheets:
  sys.stderr.write('Reading worksheet for combination: %s\n'%(ws.title.text))
  name = ws.title.text.strip()
  ws_id = ws.id.text.split('/')[-1]
  one_table = GetTable(client, table_key, ws_id)
  for row in one_table:
    code = row['code']
    table[code] = dict(table[code].items() + row.items())

weights = []
key_values = collections.defaultdict(list)

for code in table.keys():
  company = table[code]
  sys.stderr.write('%s: %s\n'%(company['name'], str(company)))
  info = GetEasyMoneyInfo(company['code'], company['market'])
  weights.append(float(company['weight']))
  for key in info.keys():
    key_values[key].append(info[key])
  sys.stderr.write('%s: %s\n%s\n'%(company['name'], str(company), str(info)))
  time.sleep(3)

weights = numpy.array(weights)
key_values = {
  key: sum(weights) / sum(weights / numpy.array(key_values[key])) for key in key_values.keys()
}

print key_values
