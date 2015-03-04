#!/usr/bin/python

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function

import json
from optparse import OptionParser
from translate_feature_format import *

from sklearn.datasets import load_svmlight_file, dump_svmlight_file

import numpy as np

import sys

def create_options():
    parser = OptionParser()
    parser.add_option(
        "--input_file",
        dest = "input_file",
        help = "input file in svmlight format",
        metavar = "FILE")
    parser.add_option(
        "--output_file",
        dest = "output_file",
        help = "output file in svmlight format",
        metavar = "FILE")
    parser.add_option(
        "--output_param_file",
        dest = "output_param_file",
        help = "output param file in json format",
        metavar = "FILE")
    parser.add_option(
        "--normalize",
        dest = "normalize",
        choices = ["standard", "min_max", None],
        default = None),
    parser.add_option(
        "--normalize_binary",
        dest = "normalize_binary",
        action = "store_true")
    parser.add_option(
        "--ignored_features",
        dest = "ignored_features",
        help = "comma separated 0-based feature index list")
    parser.add_option(
        "--feature_combinations",
        dest = "feature_combinations",
        help = "comma separated feature combination descriptions.")

    option, args = parser.parse_args()
    return option

# Return np.matrix
def normalize(X, method, normalize_binary):
  feature_num = X.shape[1]
  offset, scale = [0.0] * feature_num, [1.0] * feature_num
  if method is None: return X, [0.0] * feature_num, [1.0] * feature_num
  if method == 'standard':
    for idx in range(feature_num):
      if normalize_binary or np.any(map(lambda x: 0 if x == 1 else x, np.asarray(X[:, idx]).flatten())):
        offset[idx], scale[idx] = X[:, idx].mean(), X[:, idx].std()
        if scale[idx] == 0: scale[idx] = 1.0
        X[:, idx] = (X[:, idx] - offset[idx]) / scale[idx]
  elif method =='':
    pass
  return X, offset, scale
  
def main():
  options = create_options()
  X, Y, feature_names = load_svmlight(options.input_file)
  X, offset, scale = normalize(X, options.normalize, options.normalize_binary)
  if options.output_param_file is not None:
    with open(options.output_param_file, 'w') as output_file:
      json.dump({'offset': offset, 'scale': scale}, output_file, indent = 2)
      
  dump_svmlight(X, Y, feature_names, options.output_file)

if __name__ == '__main__':
    main()
