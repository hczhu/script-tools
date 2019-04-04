#!/bin/python

from tabulate import tabulate

import sys

grids = []

columns = sys.stdin.readline().strip().split(",")
for line in sys.stdin:
    grids.append(line.strip().split(","))

print(tabulate(grids, columns, tablefmt="grid"))
