#!/usr/bin/python
#from operator import itemgetter, attrgetter
import sys

# -f n : sort by the n-th field
# -n: sort by int value increasingly 
# -v: reverse the order
# -d: deliminater

Reverse=False
Numeric=False
Select=-1
delim=''
for i in range(len(sys.argv)-1):
  cmd=sys.argv[i+1]
  try:
    if cmd=='-v': Reverse=True
    elif cmd=='-n': Numeric=True
    elif cmd=='-f': 
      Select=int(sys.argv[i+2])
      if Select<=0: raise ''
    elif cmd=='-d': 
      delim=sys.argv[i+2]
  except:
    sys.stderr.write('Bad argments '+cmd+'\n')
    sys.exit(1)
all=[]
while True:
  line=sys.stdin.readline()
  if line=='': break
  if len(line)==1: continue
  key=line
  if Select>0:
    if delim=='':  token=line.strip().split('\t')
    else: token=line.strip().split(delim)

    if len(token)<Select: 
      sys.stderr.write('Bad line:'+line+'\n')
      continue
    key=token[Select-1]
    if Numeric: 
      try:
        key=float(key)
      except:
        sys.stderr.write('Bad line:'+line+'\n')
        continue
  all.append([key,line])
#all.sort(cmp)
all.sort(lambda x,y: cmp(x[0],y[0]),reverse=Reverse)
#print all
for item in all:
  sys.stdout.write(item[1])

