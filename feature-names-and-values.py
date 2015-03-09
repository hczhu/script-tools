#!/usr/bin/python

import sys

feature_names = []
with open(sys.argv[1], 'r') as feature_file:
  feature_names = feature_file.readline().strip('#\n\r').split(' ')

for line in sys.stdin:
  line = line.strip('\n\r')
  for idx in range(len(feature_names)):
    line = line.replace(feature_names[idx], str(idx))
  print line

