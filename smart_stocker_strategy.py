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

def GiveTip(op, code, money):
  return '%s %s(%s) %d units @%.3f'%(op, CODE_TO_NAME[code], code,
                                     int(money / FINANCAIL_DATA_ADVANCE[code]['mp']),
                                     FINANCAIL_DATA_ADVANCE[code]['mp'])

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
    code: FINANCAIL_DATA_ADVANCE[code]['p/dbv'] / (1.0 + FINANCAIL_DATA_ADVANCE[code]['sdv/p'])
    for code in banks
  }
  banks.sort(key = lambda code: scores[code])
  for bank in banks:
    sys.stderr.write('%s: %f\n'%(CODE_TO_NAME[bank], scores[bank]))
  return banks, scores

def FilterBanks(banks):
  return filter(lambda code: FINANCAIL_DATA_ADVANCE[code]['p/sbv'] < 1.5 and
                FINANCAIL_DATA_ADVANCE['sdv/p'] > 0.03, banks)

def GetPercent(code):
  percent = HOLDING_PERCENT[code]
  for key in ['hcode', 'acode']:
    if key in STOCK_INFO[code]:
      percent += HOLDING_PERCENT[STOCK_INFO[code][key]]
  return percent

def GetBuyingPower(code):
  currency = STOCK_INFO[code]['currency']
  cap_cur = 'cny' if currency == 'cny' else 'usd'
  capital = CAPITAL_INFO[cap_cur]
  return (capital['SMA-ratio'] / 100.0 - MIN_SMA_RATIO[cap_cur]) * capital['market-value'] * EX_RATE[cap_cur + '-' + CURRENCY]

def KeepBanks():
  targetPercent = 0.8
  min_divd = 0.04
  valuation_delta = 0.05
  bank_percent = {
    '建设银行': 0.3,
    '建设银行H': 0.3,
    '招商银行': 0.3,
    '招商银行H': 0.3,
    '中国银行': 0.25,
    '中国银行H': 0.25,
    '浦发银行': 0.15,
    '兴业银行': 0.15,
  }
  bank_percent = {NAME_TO_CODE[name] : bank_percent[name] for name in bank_percent.keys()}
  all_banks = bank_percent.keys()
  currentPercent = sum(map(lambda code: HOLDING_PERCENT[code], all_banks))
  banks = FilterBanks(all_banks)
  drop_banks = set(all_banks) - set(banks)
  for bank in drop_banks:
    currency = STOCK_INFO[bank]['currency']
    if HOLDING_PERCENT[bank] > 0.005:
        return 'Clear %s(%s)'%(CODE_TO_NAME[bank], bank)

  banks, valuation = ScoreBanks(banks) 

  for code in banks:
    if 'ah-ratio' in FINANCAIL_DATA_ADVANCE[code] and FINANCAIL_DATA_ADVANCE[code]['ah-ratio'] > 1.05:
      continue
    add_percent = min(targetPercent - currentPercent, bank_percent[code] - GetPercent(code))
    if add_percent < 0.01: continue
    currency = STOCK_INFO[code]['currency']
    buying_power = GetBuyingPower(code)
    if buying_power < 0.01 * CAPITAL_INFO['all']['net']: continue
    buy_cash = min(buying_power, CAPITAL_INFO['all']['net'] * add_percent) * EX_RATE[CURRENCY + '-' + currency]
    return GiveTip('Buy', code, buy_cash)

  banks.reverse()
  for code in banks:
    currency = STOCK_INFO[code]['currency']
    sub_percent = min(currentPercent - targetPercent, HOLDING_PERCENT[code])
    if sub_percent < 0.01: continue
    return GiveTip('Sell', code, sub_percent * CAPITAL_INFO['all']['net'] * EX_RATE[CURRENCY + '-' + currency])

  for worse in banks:
    for better in banks:
      if 'ah-ratio' in FINANCAIL_DATA_ADVANCE[better] and FINANCAIL_DATA_ADVANCE[better]['ah-ratio'] > 1.05:
        continue
      if valuation[worse] / valuation[better] < valuation_delta: continue
      swap_percent = min(HOLDING_PERCENT[worse], bank_percent[better] - GetPercent(better))
      worse_currency = STOCK_INFO[worse]['currency']
      better_currency = STOCK_INFO[better]['currency']
      if worse_currency != better_currency:
        buying_power = GetBuyingPower(better_currency)
        swap_percent = min(swap_percent, buying_power / CAPITAL_INFO['all']['net'])
      if swap_percent < 0.01: continue
      swap_cash = swap_percent * CAPITAL_INFO['all']['net']
      return GiveTip('Sell', worse, swap_cash * EX_RATE[CURRENCY + '-' + worse_currency]) +\
              ' ==> ' +\
              GiveTip('Buy', better, swap_cash, EX_RATE[CURRENCY + '-' + better_currency])
  return ''

def ZhongxinBank():
  code = NAME_TO_CODE['中信银行H']
  data = FINANCAIL_DATA_ADVANCE[code]
  currency = STOCK_INFO[code]['currency']
  target_percent = 0.15
  if HOLDING_PERCENT[code] < target_percent and data['ah-ratio'] < 0.8:
    buying_power = GetBuyingPower(code)
    add_percent = min(target_percent - HOLDING_PERCENT[code], 1.0 * buying_power / CAPITAL_INFO['all']['net'])
    if add_percent > 0.01:
      return GiveTip('Buy', code, add_percent * CAPITAL_INFO['all']['net'] * EX_RATE[CURRENCY + '-' + currency])
  if data['ah-ratio'] > 0.9:
    return 'Clear %s(%s)'%(CODE_TO_NAME[code], code)
  return

STRATEGY_FUNCS = [
  KeepBanks,
  ZhongxinBank,
]
