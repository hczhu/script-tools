#!/usr/bin/python

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function

import json
from optparse import OptionParser

from sklearn.datasets import load_svmlight_file

import numpy as np

import sys

def create_options():
    parser = OptionParser()
    parser.add_option(
        "-i", "--input_file",
        dest="input_file",
        help="input file in any format",
        metavar="FILE")
    parser.add_option(
        "-o", "--output_file",
        dest="output_file",
        help="output file in any format",
        metavar="FILE")
    parser.add_option(
        "--input_format",
        dest="input_format",
        choices=["svmlight", "arff"],
        default="svmlight"),
    parser.add_option(
        "--output_format",
        dest="output_format",
        choices=["svmlight", "arff"],
        default="arff"),

    option, args = parser.parse_args()
    return option

def loadSvmlight(input_filename):
  feature_names = []
  with open(input_filename) as input_file:
    feature_names = input_file.readline().strip()
    if feature_names[0] != '#':
      print('Expecting feature names in the first line starting with a #')
      return None, None, None
    feature_names = feature_names[1:].split(' ')
  X, Y = load_svmlight_file(input_filename) 
  if len(feature_names) < X.shape[1]:
    print('feature names are not enough {0} < {1}'.format(len(feature_names), X.shape[1]))
  X.set_shape((X.shape[0], len(feature_names)))
  X = X.todense()
  X = [x.tolist()[0] for x in X]
  return X, Y, feature_names

def dumpArff(X, Y, feature_names, output_filename):
  with open(output_filename, 'w') as output_file:
    output_file.write('@relation whatever\n')
    for name in feature_names:
      output_file.write('@attribute {0} real\n'.format(name))
    output_file.write('@attribute label integer\n@data\n')
    for i in range(len(X)):
      output_file.write('{0},{1}\n'.format(','.join(['{0}'.format(x) for x in X[i]]), Y[i]))

def main():
  options = create_options()
  X, Y, feature_names = loadSvmlight(options.input_file)
  if X is None:
    print('Failed to load svmlight file {0}'.format(options.input_file))  
    return 1
  dumpArff(X, Y, feature_names, options.output_file)
  return 0

if __name__ == '__main__':
    main()
