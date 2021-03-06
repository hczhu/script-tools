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
        "--unnormalized_features",
        dest = "unnormalized_features",
        help = "comma separated 0-based feature index list")
    parser.add_option(
        "--feature_combinations",
        dest = "feature_combinations",
        help = "comma separated feature combination descriptions.")
    parser.add_option(
        "--balance_training_instance",
        dest = "balance_training_instance",
        help = "Whether to balance positive and negative instances.")
    parser.add_option(
        "--min_feature_coverage",
        dest = "min_feature_coverage",
        type = float,
        default = 0.001,
        help = "A feature with a coverage less than this threshold will be ignored.")
    parser.add_option(
        "--feature_id_offset",
        dest = "feature_id_offset",
        type = int,
        default = 0,
        help = "The feature id will be added by this value.")

    option, args = parser.parse_args()
    return option

# Return np.matrix
def normalize(X, method, normalize_binary, unnormalized_features):
  feature_num = X.shape[1]
  offset, scale = [0.0] * feature_num, [1.0] * feature_num
  if method is None: return X, [0.0] * feature_num, [1.0] * feature_num
  if method == 'standard':
    for idx in range(feature_num):
      if idx in unnormalized_features: continue
      if normalize_binary or np.any(map(lambda x: 0 if x == 1 else x, np.asarray(X[:, idx]).flatten())):
        offset[idx], scale[idx] = X[:, idx].mean(), X[:, idx].std()
        if scale[idx] == 0: scale[idx] = 1.0
        X[:, idx] = (X[:, idx] - offset[idx]) / scale[idx]
  elif method =='':
    pass
  return X, offset, scale

def eval_value(values, expression, add = lambda x, y: x + y, sub = lambda x, y: x - y):
  sub_expressions = []
  ret = None
  if expression.find('+') != -1:
    sub_expressions = expression.split('+')
    for exp in sub_expressions:
      val = eval_value(values, exp, add, sub)
      ret = val if ret is None else add(ret, val)
  elif expression.find('-') != -1:
    sub_expressions = expression.split('-')
    for exp in sub_expressions:
      val = eval_value(values, exp, add, sub)
      ret = val if ret is None else sub(ret, val)
  else:
    ret = values[int(expression)]
  return ret

# X is a np.matrix
def combine_features(X, feature_names, expressions):
  X = [x.tolist()[0] for x in X]
  for expr in expressions:
    feature_names += [eval_value(feature_names, expr, lambda x, y: x + '+' + y, lambda x, y: x + '-' + y)]
    for x in X:
      x += [eval_value(x, expr)]
  return np.matrix(X), feature_names

def ignore_features(X, feature_names, ignored_features_list, min_feature_coverage):
  for idx in range(len(feature_names)):
    values = np.transpose(X[:, idx].tolist())[0]
    if 1.0 * len(np.nonzero(values)[0]) / len(values) < min_feature_coverage:
      ignored_features_list += [idx]
      sys.stderr.write('Feature {0} is ignored due to low coverage.\n'.format(feature_names[idx]))
  X[:, ignored_features_list] = 0.0
  return X

def shift_feature_id(X, feature_names, id_offset):
  if id_offset > 0:
    feature_names = ['#None'] * id_offset + feature_names
    feature_num = X.shape[1]
    newX = np.zeros((X.shape[0], feature_num + id_offset))
    newX[:, range(id_offset, feature_num + id_offset)] = X[:, range(feature_num)]
    X = newX
  elif id_offset < 0:
    pass
  return X, feature_names 
  
def main():
  options = create_options()
  X, Y, feature_names = load_svmlight(options.input_file)
  if options.feature_combinations is not None and len(options.feature_combinations) > 0:
    X, feature_names = combine_features(X, feature_names, options.feature_combinations.split(','))
  unnormalized_features = set([])
  if options.unnormalized_features is not None:
    unnormalized_features = set(map(int, options.unnormalized_features.split(',')))
  X, offset, scale = normalize(X, options.normalize, options.normalize_binary, unnormalized_features)
  X = ignore_features(X, feature_names,
                      map(int, options.ignored_features.split(',')) if options.ignored_features is not None and len(options.ignored_features) > 0 else [],
                      options.min_feature_coverage)
  if options.feature_id_offset != 0:
    X, feature_names = shift_feature_id(X, feature_names, options.feature_id_offset)
  if options.output_param_file is not None:
    with open(options.output_param_file, 'w') as output_file:
      json.dump({
                  'offset': {str(i) : offset[i] for i in range(len(offset))},
                  'scale': {str(i) : scale[i] for i in range(len(scale))}
                },
                output_file, indent = 2)
  dump_svmlight(X, Y, feature_names, options.output_file)

if __name__ == '__main__':
    main()
