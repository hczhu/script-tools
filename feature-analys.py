#!/usr/bin/python

import numpy
import sys

"""
The first row contains feature names.
The first column is labels.
"""

names = sys.stdin.readline().strip().split(',')
matrix = []
for line in sys.stdin:
    features = [0.0] * (len(names) + 1)
    tokens = line.strip().split(',')
    for idx in range(len(tokens)):
        if -1 == tokens[idx].find(':'):
            features[idx] = float(tokens[idx])
        else:
            fid, value = tokens[idx].split(':')
            features[int(fid)] = float(value)
    matrix.append(features)


matrix = numpy.matrix(matrix)


