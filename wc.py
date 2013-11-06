#!/usr/bin/python
import sys
cnt=0
gap=1000
if len(sys.argv)>1:
  try:
    gap=int(sys.argv[1])
    if gap<=0: raise ''
  except:
    print 'Bad argument:'+sys.argv[1]
    sys.exit(1)
char=0
while True:
  line=sys.stdin.readline()
  if line=='': break
  cnt+=1
  if 0==(cnt%gap): print str(cnt)
  char+=len(line)
print cnt,char
