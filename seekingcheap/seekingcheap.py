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
import client

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

def HandleMessage(form):
    assert form['MsgType'] == 'text'
    clt = client.SeekingcheapClient(logging)
    stocks_info = clt.GetStockRealtimeInfo([form['Content'].strip().lower()])
    response = []
    for _, info in stocks_info.items():
        response.append('%s: %.2f %.1f%%'%(info['name'], info['price'], info['change']))
    if len(response) == 0:
        sys.stdout.write('success')
        return
    response = '\n'.join(response)
    logging.info('Will response with: %s'%(response))
    template_str = """<xml>
<ToUserName><![CDATA[%s]]></ToUserName>
<FromUserName><![CDATA[%s]]></FromUserName>
<CreateTime>%s</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[%s]]></Content>
</xml>"""
    weixin_response = template_str%(
        form['FromUserName'],
        form['ToUserName'],
        form['CreateTime'],
        response,
    )
    # weixin_response = weixin_response.decode('utf-8')
    logging.info('Will response with: %s'%(weixin_response))
    # logging.info('Stdout encoding: %s'%(sys.stdout.encoding))
    sys.stdout.write(weixin_response)

def main():
    reload(sys)
    sys.setdefaultencoding('utf-8')
    InitLogger()
    url = os.environ["REQUEST_URI"] 
    logging.info('Got request url: %s'%(url))
    parsed = urlparse.urlparse(url)
    url_params = {k: v[0] for k,v in urlparse.parse_qs(parsed.query).items()}
    logging.info('Got url params: %s'%(str(url_params)))
    sys.stdout.write(Validate(url_params))

    post_data = cgi.FieldStorage().value
    logging.info('Got post data: %s'%(post_data))
    form = ParsePostData(post_data)
    if form['MsgType'] == 'text':
        HandleMessage(form)
    else:
        sys.stdout.write('success')
    
if __name__ == "__main__":
    main()
