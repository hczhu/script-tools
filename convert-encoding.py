#!/usr/bin/python
import sys
if len(sys.argv)<3:
  print 'Usage: ./convert_encoding.py [source encoding(utf8)] [destination encoding(gbk)]'
  sys.exit(0)
while True:
  line=sys.stdin.readline()
  if line=='': break
  try:
    line=unicode(line,sys.argv[1])
    sys.stdout.write(line.encode(sys.argv[2]));
  except:
    sys.stderr.write('bad line:'+line+'\n')
