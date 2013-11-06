#!/usr/bin/python
import sys
output=[]
if len(sys.argv)>1:
  item=sys.argv[1].split(',')
  for i in range(len(item)):
    output.append((int)(item[i])-1)
while True:
  line=sys.stdin.readline()
  if line=='': break;
  line=line.strip()
  tok=line.split()
  bad=False
  out=''
  if len(output)==0:
    for i in range(len(tok)):
      out+='\t'+tok[i]
  else:
    for i in range(len(output)):
      if output[i]>=len(tok):
        bad=True
        break
      else: out+='\t'+tok[output[i]]
  if bad: sys.stderr.write('bad line:'+line+'\n')
  else: print '%s'%(out[1:])
