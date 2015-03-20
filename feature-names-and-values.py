#!/usr/bin/python

import sys

feature_names = []
with open(sys.argv[1], 'r') as feature_file:
  feature_names = feature_file.readline().strip('#\n\r').split(' ')

for line in sys.stdin:
  line = line.strip('\n\r')
  for idx in range(len(feature_names)):
    if len(sys.argv) == 2:
      line = line.replace(feature_names[idx], str(idx))
    else:
      line = line.replace(str(idx), feature_names[idx])
  print line

