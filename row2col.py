#!/usr/bin/python
import sys
row=[]
delim = ''
if len(sys.argv) > 1:
  delim = sys.argv[1]
while True:
  line=sys.stdin.readline()
  line=line.strip()
  if line=="":
    break;
  if len(delim) > 0: line = line.split(delim)
  else: line=line.split()
  while len(row) < len(line):
    row.append([])
  for i in range(len(line)):
    row[i].append(line[i])
for i in range(len(row)):
  for j in range(len(row[i])):
    if j > 0:
      sys.stdout.write("\t")
    sys.stdout.write(row[i][j])
  sys.stdout.write("\n")
