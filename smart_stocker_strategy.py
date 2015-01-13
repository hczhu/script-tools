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
  backup.sort(key = lambda code: (0 if currency == ASSET_INFO[code]['currency'] else 1,
                                  ASSET_INFO[code]['net-percent']))
  backup_code = backup[0]
  backup_name = CODE_TO_NAME[backup_code]
  if ASSET_INFO[backup_code]['net-percent'] < 0.01: return (0, '')
  cash_percent = min(max_percent, ASSET_INFO[backup_code]['net-percent'])
  cash = CAPITAL_INFO['all']['net'] * cash_percent
  return (cash * EX_RATE[CURRENCY + '-' + currency], 
          GiveTip('Sell', backup_code, cash * EX_RATE[CURRENCY + '-' + STOCK_INFO[backup_code]['currency']]))

def GetClassA():
  codes = []
  for code in STOCK_INFO.keys():
    if 'class-b'  in STOCK_INFO[code]:
      codes.append(code)
  return codes

def GetCashEquivalence():
  codes = GetClassA()
  map(lambda code: CODE_TO_NAME[code], codes)
  return codes

def KeepGroupPercentIf(names, percent, backup = [], hold_conditions = {}, buy_conditions = {},
                       sort_key = lambda code: -ASSET_INFO['buying-power-'+STOCK_INFO[code]['currency']]['net-percent']):
  codes = [NAME_TO_CODE[name] for name in names]
  hold_cond = {
    NAME_TO_CODE[name]: hold_conditions[name] if name in hold_conditions else lambda: True for name in names
  }
  buy_cond = {
    NAME_TO_CODE[name]: buy_conditions[name] if name in buy_conditions else lambda: True for name in names
  }
  for code in codes:
    if not hold_cond[code]():
      return 'Clear %s(%s)'%(CODE_TO_NAME[code], code)
  holding_percent = {
    code : ASSET_INFO[code]['net-percent'] if code in ASSET_INFO else 0 for code in codes
  }
  codes.sort(key = sort_key)
  sum_percent = sum(holding_percent.values())
  if sum_percent + 0.01 < percent:
    for code in codes:
      cash, op = GetCashAndOp([], STOCK_INFO[code]['currency'], percent - sum_percent)
      if cash > 0 and buy_cond[code]():
        return GiveTip('Buy', code, cash)
  codes.reverse()
  if sum_percent > percent + 0.01:
    for code in codes:
      if holding_percent[code] > 0.01:
        cash, op = GetCashAndOp([CODE_TO_NAME[code]], STOCK_INFO[code]['currency'], min(sum_percent - percent, holding_percent[code]))
        return GiveTip('Sell', code, cash)
  return ''

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
  return filter(lambda code: FINANCAIL_DATA_ADVANCE[code]['p/sbv'] < 1.8, banks)

def GetPercent(code,holding_asset_percent):
  percent = holding_asset_percent[code]
  for key in ['hcode', 'acode']:
    if key in STOCK_INFO[code]:
      percent += holding_asset_percent[STOCK_INFO[code][key]]
  return percent

def NoBuyBanks(banks):
  return filter(lambda code: FINANCAIL_DATA_ADVANCE[code]['p/sbv'] > 1.2,
                banks)

def KeepBanks():
  percent_delta = 0.04
  swap_percent_delta = 0.02
  targetPercent = 0.89
  normal_valuation_delta = 0.08
  a2h_discount = max(0.8 * MACRO_DATA['ah-premium'], normal_valuation_delta)
  h2a_discount = 0.08
  max_bank_percent = {
    '建设银行': 0.5,
    '建设银行H': 0.5,
    '招商银行': 0.55,
    '招商银行H': 0.55,
    '中国银行': 0.3,
    '中国银行H': 0.3,
    '浦发银行': 0.2,
    '兴业银行': 0.2,
  }
  backup = [
    '中信银行H',
    '中海油服H',
    '上证红利ETF',
    '南方A50ETF',
  ] + GetCashEquivalence()
  max_bank_percent = {NAME_TO_CODE[name] : max_bank_percent[name] for name in max_bank_percent.keys()}
  all_banks = max_bank_percent.keys()
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
    add_percent = min(targetPercent - currentPercent, max_bank_percent[code] - GetPercent(code, holding_asset_percent))
    cash, op = GetCashAndOp(backup, currency, add_percent)
    if add_percent > percent_delta and cash > 0:
      return op + GiveTip(' ==> Buy', code, cash)

  banks.reverse()
  for code in banks:
    currency = STOCK_INFO[code]['currency']
    sub_percent = min(currentPercent - targetPercent, holding_asset_percent[code])
    if sub_percent > percent_delta:
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
      if holding_asset_percent[worse] > max_bank_percent[worse]: valuation_delta = 0.02
      sys.stderr.write('%s ==> %s delta = %.3f valuation ratio = %.2f\n'%(
                       CODE_TO_NAME[worse], CODE_TO_NAME[better], valuation_delta,
                       valuation[worse] / valuation[better]))
      if valuation[worse] / valuation[better] < (1 + valuation_delta): continue
      swap_percent = min(holding_asset_percent[worse], max_bank_percent[better] - GetPercent(better, holding_asset_percent))
      if worse_currency != better_currency:
        swap_percent = min(swap_percent, ASSET_INFO['buying-power-' + better_currency]['net-percent'])
      swap_cash = swap_percent * CAPITAL_INFO['all']['net']
      if swap_percent > swap_percent_delta:
        return GiveTip('Sell', worse, swap_cash * EX_RATE[CURRENCY + '-' + worse_currency]) +\
                 ' ==> ' +\
               GiveTip('Buy', better, swap_cash * EX_RATE[CURRENCY + '-' + better_currency])
  return ''

def FenJiClassA():
  codes = GetClassA()

  holding_market_value = {
    code : ASSET_INFO[code]['market-value'] if code in ASSET_INFO else 0 \
      for code in codes
  }

  want_rate = 7.1 / 100
  sell_rate = 6.5 / 100
  for code in codes:
    sbv = FINANCAIL_DATA_ADVANCE[code]['sbv']
    rate = FINANCAIL_DATA_BASE[code]['next-rate']
    price = sbv - 1.0 + rate / want_rate
    print 'Buy %s(%s) @%.3f down %.2f%%'%(CODE_TO_NAME[code], code, price, (GetMarketPrice(code) - price) / max(0.10, GetMarketPrice(code)) * 100)

  codes.sort(key = lambda code: FINANCAIL_DATA_ADVANCE[code]['sdv/p']) 
  for code in codes:
    adv_data = FINANCAIL_DATA_ADVANCE[code]
    if adv_data['sdv/p'] < sell_rate and holding_market_value[code] > 0:
      return GiveTip('Sell', code, holding_market_value[code]) + ' due to interest rate drops to %.4f'%(adv_data['sdv/p'])

  best = codes[-1]
  for worse in range(len(codes)):
    if FINANCAIL_DATA_ADVANCE[best]['sdv/p'] / FINANCAIL_DATA_ADVANCE[codes[worse]]['sdv/p'] > 1.05 and \
        holding_market_value[codes[worse]] > 0:
      return GiveTip('Sell', codes[worse], holding_market_value[codes[worse]]) + \
                ' due to interest rate drops to %.4f'%(FINANCAIL_DATA_ADVANCE[codes[worse]]['sdv/p'])
  return ''

STRATEGY_FUNCS = [
  FenJiClassA,
  KeepBanks,

  lambda: KeepGroupPercentIf(['南方A50ETF'], 0.2,
                             hold_conditions = {
                               '南方A50ETF': lambda: FinancialValue('南方A50ETF', 'p/ttme') < 1.0 / MACRO_DATA['risk-free-rate'],
                               '上证红利ETF': lambda: FinancialValue('上证红利ETF', 'p/ttme') < 0.9 / MACRO_DATA['risk-free-rate'],
                               '上证50ETF': lambda: FinancialValue('上证50ETF', 'p/ttme') < 1.0 / MACRO_DATA['risk-free-rate'],
                             },
                             buy_conditions = {
                               '南方A50ETF': lambda: FinancialValue('南方A50ETF', 'p/ttme') < 10,
                               '上证红利ETF': lambda: FinancialValue('上证红利ETF', 'p/ttme') < 9,
                               '上证50ETF': lambda: FinancialValue('上证50ETF', 'p/ttme') < 10,
                             },
                             sort_key = lambda code: FINANCAIL_DATA_ADVANCE[code]['p/ttme']
                       ),

  lambda: KeepPercentIf('Yandex', 0.08,
                        hold_condition = lambda: FinancialValue('Yandex', 'p/dbv') < 1.3,
                        buy_condition = lambda: FinancialValue('Yandex', 'p/dbv') < 1.0
                       ),

  lambda: KeepPercentIf('Weibo', 0.15,
                        hold_condition = lambda: FinancialValue('Weibo', 'p/dbv') < 1.5,
                        buy_condition = lambda: FinancialValue('Weibo', 'p/dbv') < 1.0
                       ),
  lambda: KeepPercentIf('中海油服H', 0.8,
                        hold_condition = lambda: FinancialValue('中海油服H', 'ah-ratio') < 0.8,
                        buy_condition = lambda: FinancialValue('中海油服H', 'ah-ratio') < 0.6
                       ),
]
