#!/usr/bin/python
import sys
import math
all=[]
for line in sys.stdin:
  try:
    all.append(float(line))
  except:
    continue
dev=0.0
av=sum(all)/len(all)
for item in all:
  dev+=(item-av)**2
print 'sum=%f\taverage=%f\tdev=%f\tsqrt(dev)=%f'%(sum(all),sum(all)/len(all),dev/len(all),math.sqrt(dev/len(all)))
