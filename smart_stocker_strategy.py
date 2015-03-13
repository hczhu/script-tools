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
  return '%s %s(%s) %d units @%.3f cash %.0f %s'%(op, CODE_TO_NAME[code], code,
                                     int(money / FINANCAIL_DATA_ADVANCE[code]['mp']),
                                     FINANCAIL_DATA_ADVANCE[code]['mp'], money, STOCK_INFO[code]['currency'])

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
  sys.stderr.write('No enough buying power for currency: %s\n'%(currency))
  return (0, '')

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
                       sort_key = lambda code: ACCOUNT_INFO['ALL']['holding-percent-all'][code]):
  codes = [NAME_TO_CODE[name] for name in names]
  hold_cond = {
    NAME_TO_CODE[name]: hold_conditions[name] if name in hold_conditions else lambda code: True for name in names
  }
  buy_cond = {
    NAME_TO_CODE[name]: buy_conditions[name] if name in buy_conditions else lambda code: True for name in names
  }
  for code in codes:
    if not hold_cond[code](code):
      return 'Clear %s(%s)'%(CODE_TO_NAME[code], code)
  holding_percent = {code : ACCOUNT_INFO['ALL']['holding-percent-all'][code] for code in codes}
  codes.sort(key = sort_key)
  sum_percent = sum(holding_percent.values())
  if sum_percent + MIN_TXN_PERCENT < percent:
    for code in codes:
      cash, op = GetCashAndOp(ACCOUNT_INFO.keys(), STOCK_INFO[code]['currency'], percent - sum_percent)
      if cash > 0 and buy_cond[code](code):
        return GiveTip('Buy', code, cash)
  codes.reverse()
  if sum_percent > percent + MIN_TXN_PERCENT:
    for code in codes:
      if holding_percent[code] > MIN_TXN_PERCENT:
        cash = EX_RATE[CURRENCY + '-' + STOCK_INFO[code]['currency']] * min(sum_percent - percent, holding_percent[code]) * ACCOUNT_INFO['ALL']['net']
        return GiveTip('Sell', code, cash)
  return ''

def KeepPercentIf(name, percent, backup = [], hold_condition = lambda code: True, buy_condition = lambda code: True):
  delta = MIN_TXN_PERCENT
  code = NAME_TO_CODE[name]
  currency = STOCK_INFO[code]['currency']
  percent = percent if hold_condition(code) else 0
  holding_percent = ACCOUNT_INFO['ALL']['holding-percent-all'][code]
  if holding_percent - percent > delta:
    return GiveTip('Sell', code,
        (holding_percent - percent) * ACCOUNT_INFO['ALL']['net'] * EX_RATE[CURRENCY + '-' + currency])
  cash, op = GetCashAndOp(ACCOUNT_INFO.keys(), currency, percent - holding_percent, backup)
  if percent - holding_percent > delta and cash > 0 and buy_condition(code):
    return op + GiveTip(' ==> Buy', code, cash)
  return '' 

def ScoreBanks(banks):
  scores = {
    code: GetMarketPrice(code) / ((GetMarketPrice(code) / FINANCAIL_DATA_ADVANCE[code]['p/ttme'] +
                                   GetMarketPrice(code) / FINANCAIL_DATA_ADVANCE[code]['p/dbv']) *
                                   (1.0 + FINANCAIL_DATA_ADVANCE[code]['sdv/p'])) for code in banks
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

def KeepBanks(targetPercent):
  min_txn_percent = max(0.3, MIN_TXN_PERCENT)
  swap_percent_delta = 0.03
  max_swap_percent = 0.05
  normal_valuation_delta = 0.05
  a2h_discount = min(0.5 * MACRO_DATA['ah-premium'], 0.1)
  h2a_discount = 0.03
  overflow_valuation_delta = -0.01
  max_bank_percent = {
    '建设银行': 0.3,
    '建设银行H': 0.3,
    '招商银行': 0.4,
    '招商银行H': 0.4,
    '中国银行': 0.2,
    '中国银行H': 0.2,
    '浦发银行': 0.2,
    '兴业银行': 0.25,
    '交通银行': 0.15,
    '交通银行H': 0.15,
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
    bank: ACCOUNT_INFO['ALL']['holding-percent-all'][bank] for bank in all_banks
  }
  currentPercent = sum(map(lambda code: holding_asset_percent[code], all_banks))
  sys.stderr.write('bank holding percents: %s\n'%(str(holding_asset_percent)))
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

  currency_to_account = {
    'hkd': ['ib'],
    'cny': ['a'],
  }
  NET = ACCOUNT_INFO['ALL']['net']

  for code in banks:
    if code in no_buy_banks: continue
    currency = STOCK_INFO[code]['currency']
    add_percent = min(targetPercent - currentPercent, max_bank_percent[code] - GetPercent(code, holding_asset_percent))
    cash, op = GetCashAndOp(currency_to_account[currency], currency, add_percent, backup)
    if add_percent > min_txn_percent and cash > 0:
      return op + GiveTip(' ==> Buy', code, cash)
  banks.reverse()
  for code in banks:
    currency = STOCK_INFO[code]['currency']
    sub_percent = min(currentPercent - targetPercent, holding_asset_percent[code])
    if sub_percent > min_txn_percent:
      return GiveTip('Sell', code, sub_percent * NET * EX_RATE[CURRENCY + '-' + currency])
  
  valuation_delta = 100
  
  for a in range(len(banks)):
    worse = banks[a]
    worse_currency = STOCK_INFO[worse]['currency']
    for b in range(len(banks) - 1, a, -1):
      better = banks[b]
      better_currency = STOCK_INFO[better]['currency']
      valuation_delta = normal_valuation_delta
      if STOCK_INFO[worse]['currency'] == 'cny' and STOCK_INFO[better]['currency'] == 'hkd':
        valuation_delta = a2h_discount
      elif STOCK_INFO[worse]['currency'] == 'hkd' and STOCK_INFO[better]['currency'] == 'cny':
        valuation_delta = h2a_discount
      if holding_asset_percent[worse] > max_bank_percent[worse]:
        valuation_delta = overflow_valuation_delta
      valuation_ratio = valuation[worse] / valuation[better]
      sys.stderr.write('%s ==> %s delta = %.3f valuation ratio = %.2f\n'%(
                       CODE_TO_NAME[worse], CODE_TO_NAME[better], valuation_delta, valuation_ratio))
      if valuation_ratio < (1 + valuation_delta): continue
      swap_percent = min(holding_asset_percent[worse], max_bank_percent[better] - GetPercent(better, holding_asset_percent))
      swap_percent = min(swap_percent, max_swap_percent)
      swap_cash = swap_percent * NET
      if swap_percent < swap_percent_delta: continue
      if worse_currency != better_currency:
        swap_cash = min(swap_cash, EX_RATE[better_currency + '-' + CURRENCY] * GetCashAndOp(currency_to_account[better_currency], better_currency, swap_percent)[0])
      return GiveTip('Sell', worse, swap_cash * EX_RATE[CURRENCY + '-' + worse_currency]) +\
               ' ==> ' +\
             GiveTip('Buy', better, swap_cash * EX_RATE[CURRENCY + '-' + better_currency]) +\
             ' due to valuation ratio = %.3f'%(valuation_ratio)
  return ''

def FenJiClassA():
  codes = GetClassA()
  discount_ones = [NAME_TO_CODE[name] for name in []]
  codes = filter(lambda code: code not in set(discount_ones), codes)
  
  holding_market_value = {
    code : EX_RATE[CURRENCY + '-' + STOCK_INFO[code]['currency']] * ACCOUNT_INFO['ALL']['holding-value'][code] for code in codes + discount_ones
  }

  lowest_discount = 0.99
  for code in discount_ones:
    if FINANCAIL_DATA_ADVANCE[code]['p/sbv'] > lowest_discount and holding_market_value[code] > 0:
      print 'Sell %s(%s) @%.3f due to discount = %.3f'%(code, CODE_TO_NAME[code], GetMarketPrice(code), FINANCAIL_DATA_ADVANCE[code]['p/sbv'])

  codes.sort(key = lambda code: FINANCAIL_DATA_ADVANCE[code]['sdv/p']) 
  want_rate = 7.0 / 100
  sell_rate = 6.05 / 100
  for code in codes:
    sbv = FINANCAIL_DATA_ADVANCE[code]['sbv']
    rate = FINANCAIL_DATA_BASE[code]['next-rate']
    price = sbv - 1.0 + rate / want_rate
    down_percent = (GetMarketPrice(code) - price) / max(0.10, GetMarketPrice(code)) * 100
    if down_percent < 1.0:
      print 'Buy %s(%s) @%.3f down %.2f%%'%(CODE_TO_NAME[code], code, price, down_percent)

  for code in codes:
    adv_data = FINANCAIL_DATA_ADVANCE[code]
    if adv_data['sdv/p'] < sell_rate and holding_market_value[code] > 0:
      return GiveTip('Sell', code, holding_market_value[code]) + ' due to interest rate drops to %.4f'%(adv_data['sdv/p'])

  best = codes[-1]
  for worse in range(len(codes)):
    if FINANCAIL_DATA_ADVANCE[best]['sdv/p'] / FINANCAIL_DATA_ADVANCE[codes[worse]]['sdv/p'] > 1.03 and \
        holding_market_value[codes[worse]] > 0:
      return GiveTip('Sell', codes[worse], holding_market_value[codes[worse]]) + \
                ' due to interest rate drops to %.4f'%(FINANCAIL_DATA_ADVANCE[codes[worse]]['sdv/p']) + \
             GiveTip('Buy', codes[best], holding_market_value[codes[worse]]) + ' interest rate: %.4f'%(FINANCAIL_DATA_ADVANCE[codes[best]]['sdv/p'])
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
  for cross in financial_date['cross-share']:
    name = cross[1]
    code = NAME_TO_CODE[name]
    price = GetMarketPrice(name)
    per_share = cross[0] * (1.0 - financial_date['tax-rate']) / financial_date['shares']
    added_value = price * EX_RATE[STOCK_INFO[code]['currency'] + '-' + STOCK_INFO[codeY]['currency']] * per_share
    if code == codeA:
      ratio = per_share
    else:
      added_value *= 0.9
    value += added_value
  mp = GetMarketPrice(codeY)
  PB = mp / value
  sys.stderr.write('%.2f shares of Alibaba per Yahoo share nav = %.2f PB = %.2f.\n'%(ratio, value, PB))
  holding_shares = ACCOUNT_INFO['ALL']['holding-shares']
  imbalance = holding_shares['Yahoo'] * ratio + holding_shares['Alibaba']
  if imbalance / ratio < -50:
    print 'Buy Yahoo %d unit @%.2f for portfolio parity.' % (-imbalance / ratio, GetMarketPrice('Yahoo'))
  elif imbalance > 10:
    print 'Sell Alibaba %d units @%.2f for portfolio parity.' % (imbalance, GetMarketPrice('Alibaba'))

  holding_percent = {
    code: ACCOUNT_INFO['ALL']['holding-percent-all'][code] for code in map(lambda name : NAME_TO_CODE[name], ['Alibaba', 'Yahoo'])
  }
  lower_PB = 0.95
  cash = GetCashAndOp(['ib', 'schwab'], STOCK_INFO[codeY]['currency'], 0.03)[0]
  sys.stderr.write('Cash for Yahoo %d %s PB %f < bound %f holding percent = %f\n'%(cash, STOCK_INFO[codeY]['currency'], PB, lower_PB, holding_percent[codeY]))
  if PB < lower_PB and cash > 0 and holding_percent[codeY] < 0.15:
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
  total_money_in_CURRENCT = 280000
  percent_sum = 1.0 * total_money_in_CURRENCT / ACCOUNT_INFO['ALL']['net']
  max_A_percent =0.3
  base_ah_premium = 0.15
  max_ah_premium = 0.30
  target_A_percent = max_A_percent / (max_ah_premium - base_ah_premium) * (max_ah_premium - MACRO_DATA['ah-premium'])
  target_A_percent = min(max_A_percent, target_A_percent)
  target_A_percent = max(0, target_A_percent)
  target_bank_percent = percent_sum - target_A_percent
  sys.stderr.write('Target bank percent = %.2f A50 percent = %.2f\n'%(target_bank_percent, target_A_percent))
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
  
STRATEGY_FUNCS = [
  FenJiClassA,
  lambda: BuyETFDiscount('南方A50ETF'),

  lambda: KeepPercentIf('Weibo', 0.12,
                        hold_condition = lambda code: FINANCAIL_DATA_ADVANCE[code]['p/dbv'] < 1.5,
                        buy_condition = lambda code: FINANCAIL_DATA_ADVANCE[code]['p/dbv'] < 1.0
                       ),

  lambda: KeepPercentIf('中海油服H', 0.2,
                        hold_condition = lambda code: FINANCAIL_DATA_ADVANCE[code]['ah-ratio'] < 0.7,
                        buy_condition = lambda code: FINANCAIL_DATA_ADVANCE[code]['ah-ratio'] < 0.6 and FINANCAIL_DATA_ADVANCE[code]['sdv/p'] > 0.035 \
                                                     and FINANCAIL_DATA_ADVANCE[code]['p/sbv'] < 0.7,
                       ),

  KeepCnyCapital,
  YahooAndAlibaba,
  BalanceAHBanks,
]
