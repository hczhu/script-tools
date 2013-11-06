#!/usr/bin/python
import sys
if len(sys.argv)<3:
    print 'Usage:'+sys.argv[0]+' [file1] [file2]'
    sys.exit()
all={}
for line in file(sys.argv[1]):
    all[line.strip()]=1

for line in file(sys.argv[2]):
    if line.strip() not in all:
        sys.stdout.write(line)
