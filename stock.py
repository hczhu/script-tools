#!/usr/bin/python
import sys
from datetime import timedelta
from datetime import date
from collections import defaultdict

def CalOneStock(R, records):
  capital_cost = 0.0
  net_profit = 0.0
  investment = 0.0
  remain_stock = 0
  prev_date = date(2000, 1, 1)
  records.sort()
  for cell in records:
    trans_date = date(int(cell[0][0:4]), int(cell[0][4:6]), int(cell[0][6:8]))
    value = float(cell[14])
    remain_stock = int(cell[8])
    if investment > 0.0:
      diff_days = (trans_date - prev_date).days
      capital_cost  += investment * R / 365 * diff_days
    investment -= value
    #assert investment >= 0.0
    net_profit += value
    prev_date = trans_date

  if investment > 0.0:
    capital_cost  += investment * R / 365 *(date.today() - prev_date).days

  return (net_profit, capital_cost, remain_stock)
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
    row = '|'
    for i in range(len(cells)):
      row += (' ' * (col_len[i] - len(str(cells[i]).decode('utf-8')))) + str(cells[i]) + '|'
    if first: first = False
    else: print line
    print row
  print header

R=0.04
if len(sys.argv) > 1:
  R = float(sys.argv[1]) / 100.0

all_records = defaultdict(list)
for line in sys.stdin:
  cells = line.strip().split(',')
  if len(cells) < 15:
    cells = line.strip().split('\t')
  all_records[cells[4]].append(cells)
sys.stderr.write('There are ' + str(len(all_records)) + ' records.\n')

stat_records = []
table_header = ['Net cash flow', 'Capital cost',
                'Holding shares', 'Cost per share', 'Cost per share(CC)', 'Stock name']
stat_records.append(table_header)
summation = [0.0] * (len(table_header) - 1)
summation.append('Summary')
for key in all_records.keys():
  (net_profit, capital_cost, remain_stock) = CalOneStock(R, all_records[key])
  investment = -net_profit
  CPS, CPSCC = 0, 0
  if remain_stock > 0 :
    CPS = round(investment / remain_stock, 3)
    CPSCC = round((investment + capital_cost) / remain_stock, 3)
  record = ([round(net_profit, 0), round(capital_cost, 0), remain_stock, CPS, CPSCC, key])
  stat_records.append(record)
  summation[0] += record[0]
  summation[1] += record[1]
stat_records.append(summation)
PrintTable(stat_records)

