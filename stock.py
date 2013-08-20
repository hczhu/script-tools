#!/usr/bin/python
import sys
from datetime import timedelta
from datetime import date
from datetime import time
from collections import defaultdict
import urllib2

def CalOneStock(R, records):
  capital_cost = 0.0
  net_profit = 0.0
  investment = 0.0
  prev_date = date(2000, 1, 1)
  holding_cost = 0.0
  holding_shares = 0
  records.sort()
  for cell in records:
    trans_date = date(int(cell[0][0:4]), int(cell[0][4:6]), int(cell[0][6:8]))
    value = float(cell[14])
    buy_shares = int(cell[6])
    if investment > 0.0:
      diff_days = (trans_date - prev_date).days
      capital_cost  += investment * R / 365 * diff_days
    investment -= value
    #assert investment >= 0.0
    net_profit += value
    prev_date = trans_date
    if buy_shares > 0:
      assert value < 0.0
      holding_cost = (holding_cost * holding_shares - value) / (holding_shares + buy_shares)
    holding_shares += buy_shares
    assert holding_shares >= 0.0
  if investment > 0.0:
    capital_cost  += investment * R / 365 *(date.today() - prev_date).days

  return (net_profit, capital_cost, holding_shares, holding_cost)
#  print 'Net cash flow: %f\nCapital cost: %f\nInvestment: %f\n\
#  Remaining stock shares: %d\nCost per share: %f'\
#      %(net_profit,
#        capital_cost,
#        investment,
#        remain_stock,
#        (capital_cost + investment) / max(1, remain_stock))

def PrintOneLine(col_len):
  line = '|'
  for l in col_len:
    line += '-' * l + '|'
  return line

def PrintTable(records):
  col_len = [0] * len(records[0])
  for cells in records:
    for i in range(len(cells)):
      col_len[i] = max(col_len[i], len(str(cells[i]).decode('utf-8')))
  line = PrintOneLine(col_len)
  header = '+' + line[1:len(line) - 1] + '+'
  print header
  first = True
  for cells in records:
    assert len(cells) == len(records[0])
    row = '|'
    for i in range(len(cells)):
      row += (' ' * (col_len[i] - len(str(cells[i]).decode('utf-8')))) + str(cells[i]) + '|'
    if first: first = False
    else: print line
    print row
  print header

def GetMarketPrice(code):
  url_prefix = 'http://xueqiu.com/S/'
  feature_str = '<div class="currentInfo"><strong data-current="'
  st_prefix = ['SH', 'SZ']
  for pr in st_prefix:
    url = url_prefix + pr + code
    try:
      content=urllib2.urlopen(url).read()
      pos = content.find(feature_str)
      if pos < 0: continue
      pos += len(feature_str)
      end = content[pos:].find('"') + pos
      if end < 0: continue
      return float(content[pos:end])
    except:
      continue
  return 0

#print GetMarketPrice('112072')

R=0.04
if len(sys.argv) > 1:
  R = float(sys.argv[1]) / 100.0

all_records = defaultdict(list)
for line in sys.stdin:
  cells = line.strip().split(',')
  if len(cells) < 15:
    cells = line.strip().split('\t')
  all_records[cells[4] + ',' + cells[3]].append(cells)
  ctime = map(int, cells[1].split(':'))
  cells[1] = time(ctime[0], ctime[1], ctime[2]).isoformat()
sys.stderr.write('There are ' + str(len(all_records)) + ' records.\n')

stat_records = []
table_header = ['Holding shares', 'Market price', 'Market value', 'Holding CPS',
                'CPSCC(CPS)', 'Margin', 'NCF', 'CC', 'Stock name']

stat_records.append(table_header)
summation = [0.0] * (len(table_header) - 1)
summation.append('Summary')

blacked_keys = {'131810' : 1, '' : 1}

for key in all_records.keys():
  if len(key.split(',')) < 2: continue
  code = key.split(',')[1]
  if code in blacked_keys: continue;
  (net_profit, capital_cost, remain_stock, holding_cps) = CalOneStock(R, all_records[key])
  investment = -net_profit
  CPS, CPSCC = 0, 0
  if remain_stock > 0 :
    CPS = round(investment / remain_stock, 3)
    CPSCC = round((investment + capital_cost) / remain_stock, 3)
  mp = GetMarketPrice(code)
  mv = mp * remain_stock
  margin = (mp - CPSCC) / mp
  record = [remain_stock, mp, round(mv, 0),
            round(holding_cps, 3),
            str(CPSCC), #+ '(' + str(CPS) + ')',
            str(round(margin * 100, 2)) + '%',
            round(net_profit, 0), round(capital_cost, 0), key]
  stat_records.append(record)
  summation[2] += mv
  summation[5] += margin * mv
  summation[6] += record[6]
  summation[7] += record[7]
summation[5] /= summation[2]
summation[5] = str(round(summation[5] * 100, 2)) + '%'
summation[5] = str(summation[2] + summation[6] - summation[7]) + '(' + str(round((summation[2] + summation[6] - summation[7]) / -summation[6] * 100, 2)) + '%)'

stat_records.append(summation)
PrintTable(stat_records)

