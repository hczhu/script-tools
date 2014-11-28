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

def GenericDynamicStrategy(name,
                           indicator,
                           buy_range,
                           hold_percent_range,
                           sell_point,
                           percent_delta = 0.03,
                           buy_condition = lambda code: True,
                           sell_condition = lambda code: True):
  code = NAME_TO_CODE[name]
  mp = GetMarketPrice(code)
  mp_base = GetMarketPriceInBase(code)
  indicator_value = FINANCIAL_FUNC[indicator](code, mp)
  if InBetween(buy_range, indicator_value):
    target_percent = (hold_percent_range[1] - hold_percent_range[0]) * (indicator_value - buy_range[0]) / (
                    buy_range[1] - buy_range[0]) + hold_percent_range[0]
    target_percent = max(hold_percent_range[0], target_percent)
    target_percent = min(hold_percent_range[1], target_percent)
    current_percent = holding_percent[code]
    percent = target_percent - current_percent
    if percent >= percent_delta and buy_condition(code):
      percent = percent_delta
      return 'Buy %s(%s) %d units @%.2f change: %.1f%% due to %s = %.3f. Target: %.1f%% current: %.1f%%'%(
          CODE_TO_NAME[code], code,
          int(NET_ASSET * percent / mp_base),
          mp,
          GetMarketPriceChange(code), indicator, indicator_value,
          target_percent * 100, current_percent * 100)
  elif InBetween([buy_range[0], indicator_value], sell_point):
    current_percent = holding_percent[code]
    percent = min(current_percent, percent_delta)
    if percent > 0.0 and sell_condition(code):
      return 'Sell %s(%s) %d units @%.2f change: %.1f%% due to %s = %.3f.'%(
          CODE_TO_NAME[code], code,
          int(NET_ASSET * percent / mp_base),
          mp,
          GetMarketPriceChange(code), indicator, indicator_value)
  elif InBetween([buy_range[0], indicator_value], buy_range[1]):
    return 'Extreme price for %s(%s) @%.2f due to %s = %.3f.'%(
      CODE_TO_NAME[code], code,
      mp, indicator, indicator_value)
  return ''

def GenericSwapStrategy(name1, name2,
                        indicator,
                        zero1, fair,
                        percent_delta = 0.05):
  code1 = NAME_TO_CODE[name1]
  code2 = NAME_TO_CODE[name2]
  mp1 = GetMarketPrice(code1)
  mp2 = GetMarketPrice(code2)
  mp_base1 = GetMarketPriceInBase(code1)
  mp_base2 = GetMarketPriceInBase(code2)
  indicator_value = indicator() if IsLambda(indicator) else \
    FINANCIAL_FUNC[indicator](code1, mp1) / FINANCIAL_FUNC[indicator](code2, mp2)
  holding1 = holding_percent[code1]
  holding2 = holding_percent[code2]
  fair_percent = (holding1 + holding2) / 2
  target1 = fair_percent * (indicator_value - zero1) / (fair - zero1)
  target2 = holding2 + holding1 - target1
  if abs(target1 - holding1) >= percent_delta:
    money = NET_ASSET * percent_delta
    if target1 > holding1:
      code1, code2 = code2, code1
      mp1, mp2 = mp2, mp1
      mp_base1, mp_base2 = mp_base2, mp_base1 
      target1, target2 = target2, target1
    return '%s(%s)(target = %.1f%%) %d units @%.2f ==> %s(%s)(target = %.1f%%) %d units @%.2f due to %s ratio = %.3f.'%(
          CODE_TO_NAME[code1], code1, target1 * 100, int(money / mp_base1), mp1,
          CODE_TO_NAME[code2], code2, target2 * 100, int(money / mp_base2), mp2,
          'Function' if IsLambda(indicator) else indicator, indicator_value)
  return ''
  
def GenericChangeAH(name, adh_lower, adh_upper):
  code = NAME_TO_CODE[name]
  codeh = AH_PAIR[code]
  adh = GetAHDiscount(code)
  if adh >= adh_upper and holding_percent[codeh] > 0.0:
    return '%s(%s) @%.3f --> %s(%s) @%.3f due to AHD = %.4f'%(
      CODE_TO_NAME[codeh], codeh, GetMarketPrice(codeh),
      CODE_TO_NAME[code], code, GetMarketPrice(code), adh)
  if adh <= adh_lower and holding_percent[code] > 0.0:
    return '%s(%s) @%.3f --> %s(%s) @%.3f due to AHD = %.4f'%(
      CODE_TO_NAME[code], code, GetMarketPrice(code),
      CODE_TO_NAME[codeh], codeh, GetMarketPrice(codeh), adh)
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
    code: FINANCAIL_DATA_ADVANCE[code]['p/dbv'] / (1.0 + FINANCAIL_DATA_ADVANCE[code]['sdv/p'])
    for code in banks
  }
  banks.sort(key = lambda code: scores[code])
  print scores
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

STRATEGY_FUNCS = [
  KeepBanks,
]
