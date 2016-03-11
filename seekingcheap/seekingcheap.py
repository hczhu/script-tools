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
import os
import os.path
import cgi
import urlparse
import hashlib
import cgitb

from smart_stocker_public_data import *
import HTML
import html
import logging
from xml.dom import minidom

def InitLogger():
    FORMAT = '%(asctime)s %(filename)s:%(lineno)s %(levelname)s:%(message)s'
    logging.basicConfig(format=FORMAT, stream = sys.stderr, level=logging.INFO)
    logging.info('Got a logger.')
    # cgitb.enable()

def Validate(url_params):
    url_params['token'] = 'seekingcheap'
    strings = [url_params[key] for key in ['token', 'timestamp', 'nonce']]    
    strings.sort()
    if hashlib.sha1(''.join(strings)).hexdigest() != url_params['signature']:
        logging.error('Failed to validate the request.')
        sys.exit(1)
    return url_params.get('echostr', '')

def ParsePostData(post_data):
    xmldoc = minidom.parseString(post_data)
    keys = [
        'ToUserName',
        'FromUserName',
        'CreateTime',
        'MsgType',
        'Content',
        'MsgId',
    ]
    form = {}
    for key in keys:
        itemlist = xmldoc.getElementsByTagName(key)
        if len(itemlist) == 0: continue
        form[key] = itemlist[0].childNodes[0].nodeValue
    logging.info('Parsed post data: %s'%(str(form)))
    return form

def main():
    InitLogger()
    url = os.environ["REQUEST_URI"] 
    logging.info('Got request url: %s'%(url))
    parsed = urlparse.urlparse(url)
    url_params = {k: v[0] for k,v in urlparse.parse_qs(parsed.query).items()}
    logging.info('Got url params: %s'%(str(url_params)))
    sys.stdout.write(Validate(url_params))

    post_data = cgi.FieldStorage().value
    logging.info('Got post data: %s'%(post_data))
    ParsePostData(post_data)
    
if __name__ == "__main__":
    main()
