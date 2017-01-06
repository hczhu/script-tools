#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
sys.path.append('..')

import os
import os.path
import datetime
import time
import threading
import SocketServer
import json
import re
import logging
import urllib2
import dateutil.parser
from logging.handlers import TimedRotatingFileHandler

LOGGER = None
WORKING_DIR = os.path.expanduser("~") + '/seekingcheap'
ENDING_STR = '##$$##$$##'

def CrawlUrl(url, encoding = ''):
    try:
        LOGGER.info('Crawling url: %s\n'%(url))
        request = urllib2.Request(url)
        content = urllib2.urlopen(request).read()
        if encoding != '':
          content = content.decode(encoding).encode('utf-8')
        LOGGER.info('Crawled content: %s'%(content))
        return content
    except Exception, e:
        LOGGER.info('Exception ' + str(e) +'\n')
        LOGGER.info('Failed to open url: ' + url + '\n')
        return ''

def InitLogger(path):
    FORMAT = '%(asctime)s %(filename)s:%(lineno)s %(levelname)s: %(message)s'
    # logging.basicConfig(format=FORMAT, stream=None)
    # logging.info('Got a logger.')
    global LOGGER
    LOGGER = logging.getLogger("Rotating Log")
    LOGGER.setLevel(logging.INFO)
    handler = TimedRotatingFileHandler(path,
                                       when="h",
                                       interval=24,
                                       backupCount=3)
    handler.setFormatter(logging.Formatter(FORMAT))
    LOGGER.addHandler(handler)
    LOGGER.info('Got a logger.')
    assert LOGGER is not None

def Recv(obj):
    data = ''
    while True:
        piece = obj.recv(64)
        if piece == '': break
        data += piece
        if data.find(ENDING_STR) != -1:
            assert data.find(ENDING_STR) + len(ENDING_STR) == len(data)
            data = data[0:-len(ENDING_STR)]
            break
    return data

def GetStockRealtimeInfo(ticker):
    prefixes = [
        'sz',
        'sh',
        'hk',
        'gb_',
    ]
    url_prefix = 'http://hq.sinajs.cn/list='
    url = url_prefix + ','.join([prefix + ticker for prefix in prefixes])
    content = CrawlUrl(url, encoding = 'gbk')
    pat = re.compile('hq_str_([^=]+)' + ticker + '="([^"]+)";')
    mt = pat.search(content)
    price, change, name = 0, 0, ''
    if mt is None: return {}
    market = mt.groups()[0]
    values = mt.groups()[1].split(',')
    if 'gb_' == market:
        price, change, name = float(values[1]), round(float(values[2]), 1), values[0]
    elif 'hk' == market:
        price, change, name = float(values[6]), round(float(values[8]), 1), values[1]
    else:
        price = float(values[3])
        prev_price = float(values[2])
        change = round(100.0 * (price - prev_price) / prev_price, 1)
        name = values[0]
    return {'price': price, 'change': change, 'name': name}

class TokenRefresher(object):
    url_temp = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=%s&secret=%s'
    def __init__(self, token_file_path):
        self.token_file = token_file_path
        with open(token_file_path, 'r') as token_file:
            content = token_file.read()
            LOGGER.info('Read token file content: %s'%(content))
            self.tokens = json.loads(content)
        self.tokens = {token['appID'] : token for token in self.tokens}
        LOGGER.info('Got tokens: %s'%(str(self.tokens)))
        self.Refresh()
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True                            # Daemonize thread
        thread.start()                                  # Start the execution

    def Refresh(self):
        while True:
            try:
                refreshed_tokens = []
                for token in self.tokens.values():
                    if 'access_token' in token and 'expires_in' in token and \
                            dateutil.parser.parse(token['expires_in']) < datetime.datetime.now():
                        ret = CrawlUrl(self.url_temp%(token['appID'], token['appsecret']))
                        LOGGER.info('Got response: %s'%(ret))
                        ret = json.loads(ret)
                        token['access_token'] = ret['access_token']
                        expires_in = datetime.timedelta(seconds = ret['expires_in'] - 300) + datetime.datetime.now()
                        token['expires_in'] = expires_in.isoformat()
                    refreshed_tokens += [token]
                with open(self.token_file, 'w') as token_file:
                    token_file.write(json.dumps(refreshed_tokens, indent=4))
                refreshed_tokens = {token['appID'] : token for token in refreshed_tokens}
                self.tokens = refreshed_tokens
                LOGGER.info('Refreshed tokens: %s'%(str(self.tokens)))
                break
            except Exception as ins:
                LOGGER.error('Failed to refresh a token with exception: %s'%(str(ins)))
                time.sleep(10)
                continue

    def GetToken(self, appid):
        if appid in self.tokens:
            return self.tokens[appid].get('access_token', '')
        LOGGER.error('Unknow appid: %s'%(appid))
        return ''

    def run(self):
        while True:
            soonest_time = min([dateutil.parser.parse(token['expires_in']) for token in self.tokens.values()])
            kMinGatInSeconds = 10
            sleep_seconds = max(kMinGatInSeconds, (soonest_time - datetime.datetime.now()).total_seconds() + kMinGatInSeconds)
            LOGGER.info('Soonest time: %s and will sleep %f seconds.'%(soonest_time.isoformat(), sleep_seconds))
            time.sleep(sleep_seconds)
            self.Refresh()

class StockPriceRefresher(object):
    def __init__(self, price_file_dir):
        pass
    def GetStockPrices(self, tickers):
        res = {}
        for ticker in tickers:
            info = GetStockRealtimeInfo(ticker)
            if 'price' in info and 'change' in info and 'name' in info:
              res[ticker] = info
        return json.dumps(res)

class SeekingcheapHandler(SocketServer.StreamRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """
    def __init__(self, request, client_address, server):
        LOGGER.info('Got request from %s: %s'%(str(client_address), str(request)))
        self.tokenRefresher = server.tokenRefresher
        self.stockPriceRefresher = server.stockPriceRefresher
        self.nameToFunc = {
            'GetAccessToken': lambda json_data: json.dumps({
                'access_token': self.tokenRefresher.GetToken(json_data['appID'])
            }),
            'StockPrices': lambda json_data: self.stockPriceRefresher.GetStockPrices(
                    json_data['tickers']),
        }
        LOGGER.info('nameToFunc: %s'%(str(self.nameToFunc)))
        SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)
        return

    def handle(self):
        while True:
            # self.request is the TCP socket connected to the client
            json_data = Recv(self.request)
            if json_data == '': break
            # print "{} wrote:".format(self.client_address[0])
            # print self.data
            LOGGER.info('Got data from socket: %s'%(json_data))
            json_data = json.loads(json_data)
            res = ''
            if 'function' in json_data and json_data['function'] in self.nameToFunc:
                res = self.nameToFunc[json_data['function']](json_data)
            else:
                LOGGER.error('Unknow function name: %s'%(json_data.get('function', '')))
            LOGGER.info('Sending data: %s'%(res))
            self.request.sendall(res + ENDING_STR)

class SeekingcheapServer(SocketServer.ThreadingTCPServer):
    def __init__(self, server_address, RequestHandlerClass, tokenRefresher, stockPriceRefresher):
        SocketServer.ThreadingTCPServer.__init__(self, 
                                                 server_address, 
                                                 RequestHandlerClass)
        self.tokenRefresher = tokenRefresher
        self.stockPriceRefresher = stockPriceRefresher

def RunServer(port=9527):
    InitLogger(os.path.join(WORKING_DIR, 'logs/server.log'))
    HOST = "localhost"

    tokenRefresher = TokenRefresher(os.path.join(os.path.expanduser("~"), 'seekingcheap/tokens.json'))

    stockPriceRefresher = StockPriceRefresher(os.path.join(os.path.expanduser("~"), 'stock-price'))

    server = SeekingcheapServer((HOST, port), SeekingcheapHandler, tokenRefresher, stockPriceRefresher)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()

def SetupDeamon(output_file):
    # decouple from parent environment
    os.chdir("/") 
    os.setsid() 
    os.umask(0) 
    out_log = file(output_file, 'a+')
    err_log = file(output_file, 'a+', 0)
    dev_null = file('/dev/null', 'r')
    os.dup2(out_log.fileno(), sys.stdout.fileno())
    os.dup2(err_log.fileno(), sys.stderr.fileno())
    os.dup2(dev_null.fileno(), sys.stdin.fileno())

if __name__ == "__main__":
    fpid = os.fork()
    if fpid == 0:
        print 'Running child process...'
        SetupDeamon(os.path.join(WORKING_DIR, 'logs/deamon.log'))
        print 'Finisehd setting up deasom.'
        # Running as daemon now. PID is fpid
        RunServer()
    else:
        with open(os.path.join(WORKING_DIR, 'server.pid'), 'w') as pid_file:
            pid_file.write(str(fpid))
