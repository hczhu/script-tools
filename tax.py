#!/usr/bin/python

import sys
import math

old_tax_rate = [
    [0,500,5],
    [500,2000, 10],
    [2000,5000,15],
    [5000,20000,20],
    [20000,40000, 25],
    [40000,60000, 30],
    [60000,80000, 35],
    [80000,100000,40],
    [100000, 1000000000000,45]
]
old_start = 2000
new_tax_rate = [
    [0,1500,3],
    [1500,4500,10],
    [4500,9000,20],
    [9000,35000,25],
    [35000,55000,30],
    [55000,80000,35],
    [80000,1000000000000,45]
]
new_start = 3500
other_rate = [
[12,1513], #gongjijin
[8,1008], #yanglao 12603*0.08
[2,255],  #yiliao
[1, 25],  #shiye
]

def Calculate(tax_rate, money, start):
  others = 0.0
  for item in other_rate:
    others += min(0.01*item[0]*money, float(item[1]))
  money -= others
  tax=0.0
  for item in tax_rate:
    ll = max(item[0], 0)
    rr = min(item[1], money - start)
    if ll < rr:
      tax += 0.01 * item[2] * (rr-ll)
  money -= tax
  return [money, tax, others]

while True:
  line = sys.stdin.readline()
  if line == '': break
  money = int(line.strip())
  net_income,tax,others=Calculate(new_tax_rate, money, new_start)
  print 'Net income = %f\nTax = %f\nothers = %f'%(net_income, tax, others)
