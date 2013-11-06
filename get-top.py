#!/usr/bin/python
#from operator import itemgetter, attrgetter
import sys,getopt

# -f n : sort by the n-th field
# -n: sort by int value increasingly
# -v: reverse the order
# -d: deliminater

def greater(a,b): return a>b
def less(a,b): return a<b

Reverse=False
Select=-1
delim='\t'
topN=1
cmp=greater
try:
  opts,args=getopt.getopt(sys.argv[1:],'vf:d:')
except getopt.GetoptError,err:
  print str(err)
  sys.exit(2)
#print sys.argv[1:],opts,args
for o,a in opts:
    if o in ('-v'): cmp=less
    elif o in ('-f'): Select=int(a)
    elif o in ('-d'): delim=a
if len(args)>0: topN=int(args[0])
all_top=[]

line_cnt=0
for line in sys.stdin:
  if len(line)==1: continue
  line_cnt+=1
  if 0 == line_cnt%100000:
    sys.stderr.write('line #'+str(line_cnt)+'\n')
  key=line
  if Select>0:
    token=line.strip().split(delim)
    if len(token)<Select:
      sys.stderr.write('Bad line:'+line+'\n')
      continue
    key=token[Select-1]
    if key.find('=')>=0: key=key[key.find('=')+1:]
    try: key=float(key)
    except:
      sys.stderr.write('Bad line:'+line+'\n')
      continue
  for i in range(len(all_top)):
    if cmp(key,all_top[i][0]):
      key,line,all_top[i]=all_top[i][0],all_top[i][1],[key,line]
  if len(all_top)<topN:
    all_top.append([key,line])
#print all_top
for item in all_top:
  sys.stdout.write(item[1])
