#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import datetime
import dateutil
import collections
import urllib2
import traceback
import copy
import re
import logging

from smart_stocker_global import *
from smart_stocker_public_data import *

#--------------Beginning of strategy functions-----

def InBetween(value_range, x):
  return (x - value_range[0]) * (x - value_range[1]) <= 0.0

def FinancialValue(name, key):
  return FINANCAIL_DATA_ADVANCE[NAME_TO_CODE[name]][key]

def GiveTip(op, code, money):
  return '%s %s(%s %.1f%%) %d units @%.3f cash %.0f %s'%(op, CODE_TO_NAME[code], code, GetMarketPriceChange(code),
                                     int(money / GetMarketPrice(code)),
                                     GetMarketPrice(code), money, STOCK_INFO[code]['currency'])

def GetCashAndOp(accounts, currency, max_percent, backup = []):
  NET = ACCOUNT_INFO['ALL']['net']
  if max_percent < MIN_TXN_PERCENT: return (0, '')
  backup = set([NAME_TO_CODE[code] if code in NAME_TO_CODE else code for code in backup])
  for account in accounts:
    account_info = ACCOUNT_INFO[account]
    ex_rate = EX_RATE[ACCOUNT_INFO['ALL']['currency'] + '-' + currency]
    if currency in account_info['support-currencies'] and account_info['buying-power-percent-all'] > MIN_TXN_PERCENT:
      return (ex_rate * NET * min(account_info['buying-power-percent-all'], max_percent), '')
    holding_percent = account_info['holding-percent-all']
    for ticker, percent in holding_percent.items():
      if ticker in backup and percent > MIN_TXN_PERCENT and currency == STOCK_INFO[ticker]['currency']:
        percent = min(percent, max_percent)
        return (ex_rate * NET * percent, GiveTip('Sell', ticker, EX_RATE[CURRENCY + '-' + STOCK_INFO[ticker]['currency']] * NET * percent))
  logging.info('No enough buying power for currency: %s\n'%(currency))
  return (0, '')

def GetClassA(keep_percent = 0.0, sorter = lambda code: ACCOUNT_INFO['ALL']['holding-percent-all'][code] if code in ACCOUNT_INFO['ALL']['holding-percent-all'] else 0):
  codes = []
  for code in STOCK_INFO.keys():
    if 'class-b'  in STOCK_INFO[code]:
      codes.append(code)
  holding_percent = {code : ACCOUNT_INFO['ALL']['holding-percent-all'][code] if code in ACCOUNT_INFO['ALL']['holding-percent-all'] else 0 for code in codes}
  codes.sort(key = sorter)
  while keep_percent > 0.0 and len(codes) > 0:
    keep_percent -= holding_percent[codes[0]]
    codes = codes[1:]
  return codes

def GetCashEquivalence(keep_percent = 0.0):
  codes = GetClassA(keep_percent)
  map(lambda code: CODE_TO_NAME[code], codes)
  return codes

def BuyOrPass(name, valuation, buy_valuation, fixed_money = None):
  code = NAME_TO_CODE[name]
  holding_percent = ACCOUNT_INFO['ALL']['holding-percent-all'][code]
  currency = STOCK_INFO[code]['currency']
  if fixed_money is not None:
    percent = fixed_money * EX_RATE[currency + '-' + CURRENCY] / ACCOUNT_INFO['ALL']['net']
    if holding_percent > percent and valuation > buy_valuation:
        return GiveTip('Sell %d%% of '%(100 * (holding_percent - percent)),
                        code,
                        (holding_percent - percent) * ACCOUNT_INFO['ALL']['net'] * EX_RATE[CURRENCY + '-' + currency])

  if valuation < buy_valuation:
        buy_percent = MAX_TXN_PERCENT if fixed_money is None else fixed_money * EX_RATE[currency + '-' + CURRENCY] / ACCOUNT_INFO['ALL']['net'] - holding_percent
        if buy_percent > MIN_TXN_PERCENT:
            return GiveTip(' Buy ', code, buy_percent * ACCOUNT_INFO['ALL']['net'] * EX_RATE[CURRENCY + '-' + currency])
  return ''

def FenJiClassA():
  codes = GetClassA()
  logging.info('Got %s class A candidates.\n'%(len(codes)))
  rate_sum, count= 0, 0
  for code in codes:
    if FINANCAIL_DATA_BASE[code]['下折距离'.decode('utf-8')] > 0.15:
      rate_sum += FINANCAIL_DATA_BASE[code]['sdv/p']
      count += 1
  average_sdv_p = rate_sum / max(1, count)
  logging.info('Average rate: %.2f%% for class A.\n'%(average_sdv_p * 100))

  arbitrage = filter(lambda code: code in CODE_TO_NAME and CODE_TO_NAME[code].find('银-行') != -1, codes)
  if len(arbitrage) > 0:
    arbitrage.sort(key = lambda code: FINANCAIL_DATA_BASE[code]['premium'])
    wanted_premium = -0.04
    best = arbitrage[0]
    if FINANCAIL_DATA_BASE[best]['premium'] < wanted_premium:
      return 'Arbitrage on %s(%s) due to premium = %.3f'%(CODE_TO_NAME[best], best, FINANCAIL_DATA_BASE[best]['premium'])
  
  holding_market_value = {
    code : EX_RATE[CURRENCY + '-' + STOCK_INFO[code]['currency']] * ACCOUNT_INFO['ALL']['holding-value'][code] for code in codes
  }
  score_key = 'score'
  candidates = codes
  candidates.sort(key = lambda code: FINANCAIL_DATA_BASE[code]['sdv/p'])
  if len(candidates) == 0: return ''
  delta = 0.03
  for code in candidates:
    if holding_market_value[code] <= 0: continue
    if FINANCAIL_DATA_BASE[code]['sdv/p'] < average_sdv_p:
      print 'Clear %s(%s) @%.3f due to sdv/p = %.3f < average %.3f'%(
        CODE_TO_NAME[code], code, GetMarketPrice(code),
        FINANCAIL_DATA_BASE[code]['sdv/p'], average_sdv_p)

  for a in range(len(candidates)):
    better = candidates[a]
    for b in range(len(candidates) - 1, a, -1):
      worse = candidates[b]
      if FINANCAIL_DATA_BASE[worse][score_key] / FINANCAIL_DATA_BASE[better][score_key] > 1 + delta \
        and holding_market_value[worse] > 0:
        print '%s(%s) @%.3f [%.3f] ==> %s(%s) @%.3f [%.3f]'%(
                CODE_TO_NAME[worse], worse, GetMarketPrice(worse), FINANCAIL_DATA_BASE[worse][score_key],
                CODE_TO_NAME[better], better, GetMarketPrice(better), FINANCAIL_DATA_BASE[better][score_key])
  return ''

def KeepCnyCapital():
  target = 500000
  if ACCOUNT_INFO['a']['net'] < target:
    print 'Need %d cny to reach %d cny asset'%(target - ACCOUNT_INFO['a']['net'], target)
  return ''

def BuyETFDiscount(name):
  code = NAME_TO_CODE[name]
  if FINANCAIL_DATA_ADVANCE[code]['p/sbv'] < 0.97:
    return GiveTip('Buy', code, 200000)
  return ''

def YahooAndAlibaba():
  codeY = NAME_TO_CODE['Yahoo']
  codeA = NAME_TO_CODE['Alibaba']
  value = FINANCAIL_DATA_BASE[codeY]['sbv']
  financial_date = FINANCAIL_DATA_BASE[codeY]
  
  kUnit = 100
  ratio = 0
  for name, amount in financial_date['cross-share'].items():
    code = NAME_TO_CODE[name]
    price = GetMarketPrice(name)
    per_share = amount * (1.0 - financial_date['tax-rate']) / financial_date['shares']
    added_value = price * EX_RATE[STOCK_INFO[code]['currency'] + '-' + STOCK_INFO[codeY]['currency']] * per_share
    if code == codeA:
      ratio = per_share
    else:
      added_value *= 0.9
    value += added_value
  mp = GetMarketPrice(codeY)
  PB = mp / value
  logging.info('%.2f shares of Alibaba per Yahoo share nav = %.2f PB = %.2f.\n'%(ratio, value, PB))
  holding_shares = ACCOUNT_INFO['ALL']['holding-shares']
  imbalance = holding_shares['Yahoo'] * ratio + holding_shares['Alibaba']
  if imbalance / ratio < -50:
    print 'Buy Yahoo %d unit @%.2f for portfolio parity.' % (-imbalance / ratio, GetMarketPrice('Yahoo'))
  elif imbalance > 10:
    print 'Sell Alibaba %d units @%.2f for portfolio parity.' % (imbalance, GetMarketPrice('Alibaba'))

  holding_percent = {
    code: ACCOUNT_INFO['ALL']['holding-percent-all'][code] for code in map(lambda name : NAME_TO_CODE[name], ['Alibaba', 'Yahoo'])
  }
  lower_PB = 0.91
  cash = GetCashAndOp(['ib', 'schwab'], STOCK_INFO[codeY]['currency'], 0.03)[0]
  logging.info('Cash for Yahoo %d %s PB %f < bound %f holding percent = %f\n'%(cash, STOCK_INFO[codeY]['currency'], PB, lower_PB, holding_percent[codeY]))
  if PB < lower_PB and cash > 0 and holding_percent[codeY] < 0.2:
    kUnit = min(cash / GetMarketPrice('Yahoo'), 100)
    return 'Long Yahoo @%.2f %d units short Alibaba @%.2f %.0f units with PB = %.2f' % (
        GetMarketPrice('Yahoo'), kUnit,
        GetMarketPrice('Alibaba'), kUnit * ratio,
        PB)
  upper_PB = 1.05
  if PB > upper_PB and holding_shares['Yahoo'] > 0:
    return 'Sell Yahoo @%.2f %d units Buy Alibaba @%.2f %.0f units with PB = %.2f' % (
        GetMarketPrice('Yahoo'), holding_shares['Yahoo'],
        GetMarketPrice('Alibaba'), holding_shares['Alibaba'],
        PB)

  return ''

def BalanceAHBanks():
  total_money_in_CURRENCT = 356000
  percent_sum = 1.0 * total_money_in_CURRENCT / ACCOUNT_INFO['ALL']['net']
  max_A_percent =0.8 * percent_sum
  base_ah_premium = 0.05
  max_ah_premium = 0.30
  target_A_percent = max_A_percent / (max_ah_premium - base_ah_premium) * (max_ah_premium - MACRO_DATA['ah-premium'])
  target_A_percent = min(max_A_percent, target_A_percent)
  target_A_percent = max(0, target_A_percent)
  target_bank_percent = percent_sum - target_A_percent
  logging.info('Target bank percent = %.2f A50 percent = %.2f\n'%(target_bank_percent, target_A_percent))
  res = KeepGroupPercentIf(['南方A50ETF'], target_A_percent,
                             hold_conditions = {
                               '南方A50ETF': lambda code: FINANCAIL_DATA_ADVANCE[code]['p/ttme'] < 1.0 / (MACRO_DATA['risk-free-rate'] * 1.2),
                             },
                             buy_conditions = {
                               '南方A50ETF': lambda code: FINANCAIL_DATA_ADVANCE[code]['p/ttme'] < 9 and FINANCAIL_DATA_ADVANCE[code]['p/sbv'] < 1.005,
                             },
                             sort_key = lambda code: FINANCAIL_DATA_ADVANCE[code]['p/ttme']
                       )
  if res != '': res += ' '
  res += KeepBanks(target_bank_percent)
  return res

def CategorizedStocks():
  allMsg = []
  valuation_key = 'valuation'
  max_increase = 0.01
  for cate, stocks in CATEGORIZED_STOCKS.items():
    logging.info('Going through category: %s\n'%(cate))
    cate_msg = []
    holding_percent = 0
    for code, strategy in stocks.items():
      holding_percent += ACCOUNT_INFO['ALL']['holding-percent'].get(code, 0)
      is_numeric_value = lambda name: isinstance(strategy.get(name, ''), float) or isinstance(strategy.get(name, ''), int)
      if not is_numeric_value(valuation_key): continue
      valuation = strategy[valuation_key]
      logging.info('Processing %s(%s): %s\n'%(CODE_TO_NAME[code], code, str(strategy)))
      if len(filter(is_numeric_value, ['buy'])) < 1: continue
      buy_valuation = strategy['buy']
      msg = BuyOrPass(CODE_TO_NAME[code], valuation, buy_valuation,
          fixed_money = int(strategy['fixed']) if ('fixed' in strategy and strategy['fixed'] != '') else None)
      if msg != '': cate_msg += ['    ' + msg + ' due to valuation=%.3f'%(abs(valuation))]
    if len(cate_msg) > 0 or holding_percent > 0:
      allMsg += ['\n'.join([cate + ': ' + str(int(holding_percent * 100)) + '%'] + cate_msg)]
  return '\n'.join(allMsg)

def StockBalance():
  allMsg = []
  if ACCOUNT_INFO['ALL']['cash-ratio'] / 100.0 < MIN_CASH_RATIO:
    allMsg.append('Cash ratio is too low: %.0f%%'%(ACCOUNT_INFO['ALL']['cash-ratio']))
  return '\n'.join(allMsg)
    
STRATEGY_FUNCS = {
  # '银行股': lambda: KeepBanks(),
  # '分级A': FenJiClassA,
  '分主题': CategorizedStocks,
  '再平衡': StockBalance,
}
