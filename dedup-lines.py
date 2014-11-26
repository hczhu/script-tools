#!/usr/bin/python
import sys
import collections

line_to_freq = collections.defaultdict(int)

for line in sys.stdin:
  line_to_freq[line.strip()] += 1

all_lines = [(line, line_to_freq[line]) for line in line_to_freq.keys()]

all_lines.sort(key = lambda record: record[1], reverse = True)

for record in all_lines:
  print record[0], record[1]
