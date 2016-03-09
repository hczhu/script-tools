#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
sys.path.append('..')

import datetime
import time
import collections
import urllib
import traceback
import copy
import re
import os.path
import cgi

from smart_stocker_public_data import *
import HTML
import html
import logging

def InitLogger():
    FORMAT = '%(asctime)s %(filename)s:%(lineno)s %(levelname)s:%(message)s'
    logging.basicConfig(format=FORMAT, stream = sys.stderr, level=logging.INFO)
    logging.info('Got a logger.')

def validate(input_params):
    return input_params.get('echostr', '')

def main():
    InitLogger()
    logging.info('Got cgi: %s'%(str(cgi)))
    input_params = cgi.FieldStorage()
    logging.info('Got params: %s'%(str(input_params)))
    # input_params = {k: input_params.getfirst(k) for k in input_params.keys() }
    logging.info('Got params: %s'%(str(input_params)))
    # logging.info('echostr: %s'%(input_params.getValue('echostr')))
    # sys.stdout.write(validate(input_params))
    # logging.info(input_params.value)
    # print('haha')
    
if __name__ == "__main__":
    main()
