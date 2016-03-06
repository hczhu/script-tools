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
import logging
import urllib2
import dateutil.parser
from logging.handlers import TimedRotatingFileHandler

LOGGER = None

def CrawlUrl(url, encoding = ''):
    try:
        LOGGER.info('Crawling url: %s\n'%(url))
        request = urllib2.Request(url)
        content = urllib2.urlopen(request).read()
        if encoding != '':
          content = decode(encoding).encode('utf-8')
        return content
    except Exception, e:
        LOGGER.info('Exception ' + str(e) +'\n')
        LOGGER.info('Failed to open url: ' + url + '\n')
        return ''

def InitLogger(path):
    FORMAT = '%(asctime)s %(filename)s:%(lineno)s %(levelname)s:%(message)s'
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

class TokenRefresher(object):
    url_temp = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=%s&secret=%s'
    def __init__(self, token_file_path):
        self.token_file = token_file_path
        with open(token_file_path, 'r') as token_file:
            content = token_file.read()
            LOGGER.info('Read token file contnet: %s'%(content))
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
                    if 'access_token' not in token or 'expires_in' not in token:
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
            time.sleep((min([dateutil.parser.parse(token['expires_in']) for token in self.tokens.values()])
                    - datetime.datetime.now()).total_seconds())
            self.Refresh()

class SeekingcheapHandler(SocketServer.BaseRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        # self.request is the TCP socket connected to the client
        self.data = self.request.recv(1024).strip()
        print "{} wrote:".format(self.client_address[0])
        print self.data
        LOGGER.info('Got data from http: %s'%(str(self.data)))
        # just send back the same data, but upper-cased
        self.request.sendall(self.data.upper())

if __name__ == "__main__":
    InitLogger(os.path.expanduser("~") + '/seekingcheap/server.log')
    HOST, PORT = "localhost", 9527

    tokenRefresher = TokenRefresher(os.path.expanduser("~") + '/seekingcheap/tokens.json')
    # Create the server, binding to localhost on port 9999
    server = SocketServer.TCPServer((HOST, PORT), SeekingcheapHandler)

    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
