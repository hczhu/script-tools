#!/usr/bin/python

import numpy
import sys
from table_printer import *
import math

from translate_feature_format import *

"""
The first row contains feature names.
The first column is labels.
"""

def Pearson(x,y):
    _x = 1.0*sum(x)/len(x)
    _y = 1.0*sum(y)/len(y)
    res = 0.0
    dx, dy = 0, 0
    for i in range(len(x)):
        res+=(x[i]-_x)*(y[i]-_y)
        dx+=(x[i]-_x)*(x[i]-_x)
        dy+=(y[i]-_y)*(y[i]-_y)
    dx /= len(x)
    dy /= len(y)
    denorm = len(x) * math.sqrt(dx)*math.sqrt(dy)
    res /= denorm if denorm != 0.0 else 1.0
    return res

def HellingerDistance(mean1, sigma1, mean2, sigma2):
    if sigma1 == 0.0 or sigma2 == 0.0:
        return 1.0 if mean1 != mean2 else 0.0
    return math.sqrt(1 - math.sqrt(2.0 * sigma1 * sigma2 / (sigma1 * sigma1 + sigma2 * sigma2)) *
                math.exp(-math.pow(mean1 - mean2, 2) / (4 * (sigma1 * sigma1 + sigma2 * sigma2))))

if __name__ == "__main__":
    names = sys.stdin.readline().strip()[1:].split(' ')
    origin_len = len(names)
    if len(sys.argv) > 1:
        for i in range(origin_len):
            for j in range(i + 1, origin_len):
                names += [names[j] + ' - ' + names[i]]
    matrix = []
    for line in sys.stdin:
        features = [0.0] * (len(names) + 1)
        if line.find('#') != -1:
            line = line[0:line.find('#')]
        tokens = line.strip().split(' ')
        # The first column is the label.
        # Put it at the last column of 'matrix'.
        if len(tokens) == 0: continue
        features[-1] = max(float(tokens[0]), 0)
        for idx in range(1, len(tokens)):
            if -1 == tokens[idx].find(':'):
                features[idx - 1] = float(tokens[idx])
            else:
                fid, value = tokens[idx].split(':')
                fid = int(fid)
                if fid >= origin_len:
                        sys.stderr.write('feature id %d exceed %d\n'%(fid, len(names)))
                        continue
                features[fid] = float(value)
        fid = origin_len
        if len(sys.argv) > 1:
            for i in range(origin_len):
                for j in range(i + 1, origin_len):
                    features[fid] = features[j] - features[i]
                    fid += 1
        matrix.append(features)
    matrix = numpy.matrix(matrix)

    header = ['Feature', 'Positive Mean(Std Dev)', 'Negative Mean(Std Dev)', 'Hellinger distance', 'Correlation', 'Nonzero values']

    table_content = []
    positive_index = numpy.nonzero(matrix[:, -1])[0].tolist()[0]
    negative_index = list(set(range(matrix.shape[0])) - set(positive_index))
    for idx in range(len(names)):
        line = [names[idx]]
        labels = numpy.transpose(matrix[:, -1].tolist())[0]
        values = numpy.transpose(matrix[:, idx].tolist())[0]
        positive = matrix[positive_index, [idx]][0]
        negative = matrix[negative_index, [idx]][0]
        pm, pd = positive.mean(), positive.std()
        nm, nd = negative.mean(), negative.std()
        table_content.append([
                          names[idx],
                          '%.6f(%.6f)'%(pm, pd),
                          '%.6f(%.6f)'%(nm, nd),
                          HellingerDistance(pm, pd, nm, nd),
                          Pearson(labels, values),
                          1.0 * len(numpy.nonzero(values)[0]) / len(values),
                      ])

    table_content.sort(reverse = True, key = lambda line: abs(line[4]))
    PrintTable(header, table_content)
