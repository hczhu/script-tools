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

STRATEGY_FUNCS = [
]
