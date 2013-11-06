#!/usr/bin/python
import sys
if len(sys.argv)<3:
  print sys.argv
  print "Usage: diff file1 file2"
  quit

file1=open(sys.argv[1],'r')
file2=open(sys.argv[2],'r')
cnt=0
cut=True
if len(sys.argv)>3: cut=False
while True:
  line1=file1.readline()
  line2=file2.readline()
  if line1=="" and line2=="": break
  cnt+=1
  if line1 != line2:
    print "diff at line %d" %(cnt)
#print "%s\n%s\n%s\n%s" %(sys.argv[1],line1,sys.argv[2],line2)
    print "%s\n%s" %(line1,line2)
    if cut: break
file1.close()
file2.close()
