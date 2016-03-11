#!/usr/bin/python
# -*- coding: utf-8 -*-

import socket
import sys
import json
import logging
from server import ENDING_STR
from server import Recv

class SeekingcheapClient():
    def __init__(self, logger):
        self.logger = logger
        # Create a TCP/IP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Connect the socket to the port where the server is listening
        server_address = ('localhost', 9527)
        logger.info('connecting to %s port %s' % server_address)
        self.sock.connect(server_address)

    def SendAndRecv(self, json_data):
        try:
            self.logger.info('Sending data: %s'%(json.dumps(json_data)))
            self.sock.sendall(json.dumps(json_data) + ENDING_STR)
            all_data = Recv(self.sock)
            self.logger.info('Received data: %s'%(all_data))
            return json.loads(all_data)
        except Exception as ins:
            self.logger.error('Exception: %s'%(ins))
            return json.loads('{}')

    def GetAccessToken(self, appID):
        json_data = {
            'function': 'GetAccessToken',
            'appID': appID,
        }
        json_response = self.SendAndRecv(json_data)
        return json_response

    def GetStockRealtimeInfo(self, tickers):
        json_data = {
            'function': 'StockPrices',
            'tickers': tickers,
        }
        json_response = self.SendAndRecv(json_data)
        return json_response

    def __del__(self):
        self.sock.close()

if __name__ == '__main__':
    FORMAT = '%(asctime)s %(filename)s:%(lineno)s %(levelname)s:%(message)s'
    logging.basicConfig(format=FORMAT, stream = sys.stderr, level=logging.INFO)
    logging.info('Got a logger.')
    clt = SeekingcheapClient(logging)
    print 'token for haha:', json.dumps(clt.GetAccessToken('haha'))
    print 'stock price:', json.dumps(clt.GetStockRealtimeInfo(['600036']))
    print 'stock price:', clt.GetStockRealtimeInfo(['600000', 'momo', 'hehe'])
    print clt.GetAccessToken('wxb84af52eb82fb589')
