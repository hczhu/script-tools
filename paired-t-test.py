#!/usr/bin/python
import math
def pttest(X,Y):
  px=1.0*sum(X)/len(X)
  py=1.0*sum(Y)/len(Y)
  X1=[]
  for i in range(len(X)): X1.append(X[i]-px)
  Y1=[]
  for i in range(len(Y)): Y1.append(Y[i]-py)
  A=0.0
  for i in range(len(X1)): A+=(X1[i]-Y1[i])**2
  print 'A=',A
