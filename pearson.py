#!/usr/bin/python
import sys
import math
def Pearson(x,y):
  _x=1.0*sum(x)/len(x)
  _y=1.0*sum(y)/len(y)
  res=0.0
  dx,dy=0,0
  for i in range(len(x)):
    res+=(x[i]-_x)*(y[i]-_y)
    dx+=(x[i]-_x)*(x[i]-_x)
    dy+=(y[i]-_y)*(y[i]-_y)
  dx/=len(x)
  dy/=len(y)
  res/=len(x)*math.sqrt(dx)*math.sqrt(dy)
  
  return res
X=[]
Y=[]
for line in sys.stdin:
  tok=line.strip().split(' ')
  if len(tok)<2:
    sys.stderr.write('bad line:'+line)
    continue
  X.append(float(tok[0]))
  Y.append(float(tok[1]))
print Pearson(X,Y)
