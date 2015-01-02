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

table = GetTable(client, table_key)

weights = []
key_values = collections.defaultdict(list)

for company in table:
  info = GetEasyMoneyInfo(company['code'], company['market'])
  weights.append(company['weight'])
  for key in info.keys():
    key_values[key].append(info[key])
  sys.stderr.write('%s: %s\n%s\n'%(company['name'], str(company), str(info)))
  time.sleep(3)

weights = numpy.array(weights)
key_values = {
  key: sum(weights) / sum(weight / numpy.array(key_values[key])) for key in key_values.keys()
}

print key_values
