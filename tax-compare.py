#!/usr/bin/python

import sys
import math


def compareTax(oldBuckets, newBuckets):
    upper = max(oldBuckets[-1][0], newBuckets[-1][0])
    oldBuckets.append((upper * 2, oldBuckets[-1][1]))
    newBuckets.append((upper * 2, newBuckets[-1][1]))
    oldBuckets.append((upper * 4, oldBuckets[-1][1]))
    newBuckets.append((upper * 4, newBuckets[-1][1]))
    old, new = 0, 0
    oldRate, newRate = 0.0, 0.0
    diff = 0.0
    prevCut = 0.0
    while old < len(oldBuckets) - 1 or new < len(newBuckets) - 1:
        cut = min(oldBuckets[old][0], newBuckets[new][0])
        diff += (cut - prevCut) * (oldRate - newRate)
        print('{:.0f} {:.0f}'.format(cut, diff))
        if abs(cut - oldBuckets[old][0]) < 0.01:
            oldRate = oldBuckets[old][1]
            old += 1
        if abs(cut - newBuckets[new][0]) < 0.01:
            newRate = newBuckets[new][1]
            new += 1
        prevCut = cut

def readBuckets(f):
    buckets = []
    with open(f) as fb:
        for line in fb:
            buckets.append(map(float, line.strip().split()))
    return buckets

if __name__ == "__main__":
    oldBuckets = readBuckets(sys.argv[1])
    newBuckets = readBuckets(sys.argv[2])
    compareTax(oldBuckets, newBuckets)
