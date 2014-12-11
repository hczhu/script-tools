#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import datetime
import collections
import urllib2
import traceback
import copy
import re

from smart_stocker_global import *
from smart_stocker_public_data import *

#--------------Beginning of strategy functions-----

def InBetween(value_range, x):
  return (x - value_range[0]) * (x - value_range[1]) <= 0.0

def FinancialValue(name, key):
  return FINANCAIL_DATA_ADVANCE[NAME_TO_CODE[name]][key]

def GiveTip(op, code, money):
  return '%s %s(%s) %d units @%.3f cash %.0f%s'%(op, CODE_TO_NAME[code], code,
                                     int(money / FINANCAIL_DATA_ADVANCE[code]['mp']),
                                     FINANCAIL_DATA_ADVANCE[code]['mp'], money, STOCK_INFO[code]['currency'])

def GetCashAndOp(backup, currency, max_percent):
  if max_percent < 0.01: return (0, '')
  buying_power = ASSET_INFO['buying-power-' + currency] 
  cash_percent = min(max_percent, buying_power['net-percent'])
  if cash_percent > 0.01:
    return (cash_percent * CAPITAL_INFO['all']['net'] * EX_RATE[CURRENCY + '-' + currency], '')
  backup = filter(lambda code: code in ASSET_INFO, [NAME_TO_CODE[name] for name in backup])
  if len(backup) == 0: return (0, '')
  backup.sort(key = lambda code: (1 if currency == ASSET_INFO[code]['currency'] else 0,
                                  ASSET_INFO[code]['net-percent']), reverse = True)
  backup_code = backup[0]
  backup_name = CODE_TO_NAME[backup_code]
  if ASSET_INFO[backup_code]['net-percent'] < 0.01: return (0, '')
  cash_percent = min(max_percent, ASSET_INFO[backup_code]['net-percent'])
  cash = CAPITAL_INFO['all']['net'] * cash_percent
  return (cash * EX_RATE[CURRENCY + '-' + currency], 
          GiveTip('Sell', backup_code, cash * EX_RATE[CURRENCY + '-' + STOCK_INFO[backup_code]['currency']]))

def KeepPercentIf(name, percent, backup = [], hold_condition = None, buy_condition = None):
  delta = 0.01
  code = NAME_TO_CODE[name]
  currency = STOCK_INFO[code]['currency']
  percent = percent if hold_condition is None or hold_condition() else 0
  holding_asset_percent = ASSET_INFO[code]['net-percent'] if code in ASSET_INFO else 0
  if holding_asset_percent - percent > delta:
    return GiveTip('Sell', code,
        (holding_asset_percent - percent) * CAPITAL_INFO['all']['net'] * EX_RATE[CURRENCY + '-' + currency])
  cash, op = GetCashAndOp(backup, currency, percent - holding_asset_percent)
  if percent - holding_asset_percent > delta and cash > 0 and (buy_condition is None or buy_condition()):
    return op + GiveTip(' ==> Buy', code, cash)
  return '' 

def YahooAndAlibaba():
  kUnit = 100
  ratio = 1.0 * CROSS_SHARE['Yahoo-Alibaba'] / SHARES['Yahoo'] * 0.72
  mp = GetMarketPrice('Yahoo') - ratio * GetMarketPrice('Alibaba')
  YahooJapanPerShare = 2.3 * 10**12 * EX_RATE['jpy-uSD'] * 0.35 * 0.72 / SHARES['Yahoo']
  net_money = 7209 * 10**6 / SHARES['Yahoo']
  PB = mp / (YahooJapanPerShare + net_money)
  imbalance = HOLDING_SHARES['Yahoo'] * ratio + HOLDING_SHARES['Alibaba']
  if imbalance / ratio < -50:
    print 'Buy Yahoo %d unit @%.2f for portfolio parity.' % (-imbalance / ratio, GetMarketPrice('Yahoo'))
  elif imbalance > 10:
    print 'Sell Alibaba %d units @%.2f for portfolio parity.' % (imbalance, GetMarketPrice('Alibaba'))

  best_tax_rate = 0.2
  upper_PB = GetMarketPrice('Yahoo') *SHARES['Yahoo'] / (
               GetMarketPrice('Yahoo') / GetPB0('Yahoo', GetMarketPrice('Yahoo')) * SHARES['Yahoo'] +
               CROSS_SHARE['Yahoo-Alibaba'] * GetMarketPrice('Alibaba') * (0.38 - best_tax_rate))
  if holding_percent['Yahoo'] + holding_percent['Alibaba'] < 0.15 and (PB < 1.4 or upper_PB < 0.95):
    return 'Long Yahoo @%.2f %d units short Alibaba @%.2f %.0f units with PB = %.2f upper_PB = %.2f' % (
        GetMarketPrice('Yahoo'), kUnit,
        GetMarketPrice('Alibaba'), kUnit * ratio,
        PB, upper_PB
        )
  if PB > 2.0:
    return 'Sell Yahoo @%.2f %d units Buy Alibaba @%.2f %.0f units with upper PB = %.2f' % (
        GetMarketPrice('Yahoo'), HOLDING_SHARES['Yahoo'],
        GetMarketPrice('Alibaba'), HOLDING_SHARES['Alibaba'],
        upper_PB)

  return ''

def ScoreBanks(banks):
  scores = {
    code: FINANCAIL_DATA_ADVANCE[code]['p/dbv'] / (1.0 + FINANCAIL_DATA_ADVANCE[code]['sdv/p']) for code in banks
  }
  banks.sort(key = lambda code: scores[code])
  for bank in banks:
    sys.stderr.write('%s: %f\n'%(CODE_TO_NAME[bank], scores[bank]))
  return banks, scores

def FilterBanks(banks):
  return filter(lambda code: FINANCAIL_DATA_ADVANCE[code]['p/sbv'] < 2.0, banks)

def GetPercent(code,holding_asset_percent):
  percent = holding_asset_percent[code]
  for key in ['hcode', 'acode']:
    if key in STOCK_INFO[code]:
      percent += holding_asset_percent[STOCK_INFO[code][key]]
  return percent

def NoBuyBanks(banks):
  return filter(lambda code: FINANCAIL_DATA_ADVANCE[code]['p/sbv'] > 1.05,
                banks)

def KeepBanks():
  targetPercent = 0.93
  normal_valuation_delta = 0.08
  a2h_discount = max(MACRO_DATA['ah-premium'], normal_valuation_delta)
  h2a_discount = 0.05
  bank_percent = {
    '建设银行': 0.4,
    '建设银行H': 0.4,
    '招商银行': 0.4,
    '招商银行H': 0.4,
    '中国银行': 0.25,
    '中国银行H': 0.25,
    '浦发银行': 0.15,
    '兴业银行': 0.15,
  }
  backup = ['券商A', '中信银行H', '南方A50ETF']
  bank_percent = {NAME_TO_CODE[name] : bank_percent[name] for name in bank_percent.keys()}
  all_banks = bank_percent.keys()
  holding_asset_percent = {
    bank: ASSET_INFO[bank]['net-percent'] if bank in ASSET_INFO else 0 for bank in all_banks
  }
  currentPercent = sum(map(lambda code: holding_asset_percent[code], all_banks))
  sys.stderr.write('total bank percent = %.3f\n'%(currentPercent))
  banks = FilterBanks(all_banks)

  drop_banks = set(all_banks) - set(banks)
  sys.stderr.write('Drop banks: %s \n'%(', '.join([CODE_TO_NAME[code] for code in drop_banks])))
  for bank in drop_banks:
    currency = STOCK_INFO[bank]['currency']
    if holding_asset_percent[bank] > 0.0:
      return 'Clear %s(%s)'%(CODE_TO_NAME[bank], bank)
  
  no_buy_banks = set(NoBuyBanks(banks))
  sys.stderr.write('No buy banks: %s \n'%(', '.join([CODE_TO_NAME[code] for code in no_buy_banks])))

  banks, valuation = ScoreBanks(banks) 

  for code in banks:
    if code in no_buy_banks: continue
    currency = STOCK_INFO[code]['currency']
    add_percent = min(targetPercent - currentPercent, bank_percent[code] - GetPercent(code, holding_asset_percent))
    cash, op = GetCashAndOp(backup, currency, add_percent)
    if cash > 0:
      return op + GiveTip(' ==> Buy', code, cash)

  banks.reverse()
  for code in banks:
    currency = STOCK_INFO[code]['currency']
    sub_percent = min(currentPercent - targetPercent, holding_asset_percent[code])
    if sub_percent > 0.01:
      return GiveTip('Sell', code, sub_percent * CAPITAL_INFO['all']['net'] * EX_RATE[CURRENCY + '-' + currency])
  
  valuation_delta = 100
  for a in range(len(banks)):
    worse = banks[a]
    worse_currency = STOCK_INFO[worse]['currency']
    if worse not in ASSET_INFO: continue
    for b in range(len(banks) - 1, a, -1):
      better = banks[b]
      better_currency = STOCK_INFO[better]['currency']
      valuation_delta = normal_valuation_delta
      if STOCK_INFO[worse]['currency'] == 'cny' and STOCK_INFO[better]['currency'] == 'hkd':
        valuation_delta = a2h_discount
      elif STOCK_INFO[worse]['currency'] == 'hkd' and STOCK_INFO[better]['currency'] == 'cny':
        valuation_delta = h2a_discount
      sys.stderr.write('%s ==> %s delta = %.3f valuation ratio = %.2f\n'%(
                       CODE_TO_NAME[worse], CODE_TO_NAME[better], valuation_delta,
                       valuation[worse] / valuation[better]))
      if valuation[worse] / valuation[better] < (1 + valuation_delta): continue
      swap_percent = min(holding_asset_percent[worse], bank_percent[better] - GetPercent(better, holding_asset_percent))
      if worse_currency != better_currency:
        swap_percent = min(swap_percent, ASSET_INFO['buying-power-' + better_currency]['net-percent'])
      swap_cash = swap_percent * CAPITAL_INFO['all']['net']
      if swap_percent > 0.01:
        return GiveTip('Sell', worse, swap_cash * EX_RATE[CURRENCY + '-' + worse_currency]) +\
                 ' ==> ' +\
               GiveTip('Buy', better, swap_cash * EX_RATE[CURRENCY + '-' + better_currency])
  return ''

def QuanShangA():
  code = NAME_TO_CODE['券商A']
  data = FINANCAIL_DATA_ADVANCE[code]
  currency = STOCK_INFO[code]['currency']
  if data['sdv/p'] * 100 > 8.0:
    money = 100000
    return GiveTip('Sell', NAME_TO_CODE['招商银行'], money) +\
             GiveTip(' ==> Buy(sdv/p = %.3f)'%(data['sdv/p']), code, money) +\
             GiveTip(' Buy', NAME_TO_CODE['招商银行H'], money * EX_RATE['cny-hkd'])
  return ''

STRATEGY_FUNCS = [
  QuanShangA,
  KeepBanks,
  lambda: KeepPercentIf('中信银行H', 0.1,
                        hold_condition = 
                          lambda: 1.0 - FinancialValue('中信银行H', 'ah-ratio') > 1.5 * (
                                    1.0 - FinancialValue('建设银行H', 'ah-ratio')),
                        buy_condition = 
                          lambda: 1.0 - FinancialValue('中信银行H', 'ah-ratio') > max(
                            2.0 * MACRO_DATA['ah-premium'], 1.0 - FinancialValue('建设银行H', 'ah-ratio'))),

  lambda: KeepPercentIf('南方A50ETF', 0.2,
                        backup = ['中信银行H'],
                        hold_condition = lambda: FinancialValue('南方A50ETF', 'p/ttme') < 1.0 / MACRO_DATA['risk-free-rate'],
                        buy_condition = lambda: FinancialValue('南方A50ETF', 'p/ttme') < 10
                       ),

  lambda: KeepPercentIf('上证红利ETF', 0.15,
                        backup = ['券商A'],
                        hold_condition = lambda: FinancialValue('上证红利ETF', 'p/ttme') < 0.9 / MACRO_DATA['risk-free-rate'],
                        buy_condition = lambda: FinancialValue('上证红利ETF', 'p/ttme') < 9
                       ),

  lambda: KeepPercentIf('Yandex', 0.08,
                        hold_condition = lambda: FinancialValue('Yandex', 'p/dbv') < 1.3,
                        buy_condition = lambda: FinancialValue('Yandex', 'p/dbv') < 1.0
                       ),
]
