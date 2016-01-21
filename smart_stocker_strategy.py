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

from smart_stocker_global import *
from smart_stocker_public_data import *

#--------------Beginning of strategy functions-----

def InBetween(value_range, x):
  return (x - value_range[0]) * (x - value_range[1]) <= 0.0

def FinancialValue(name, key):
  return FINANCAIL_DATA_ADVANCE[NAME_TO_CODE[name]][key]

def GiveTip(op, code, money):
  return '%s %s(%s) %d units @%.3f cash %.0f %s'%(op, CODE_TO_NAME[code], code,
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
  sys.stderr.write('No enough buying power for currency: %s\n'%(currency))
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

def KeepGroupPercentIf(names, percent, backup = [], hold_conditions = {}, buy_conditions = {},
                       stock_eval = lambda code: 1.0, eval_delta = 0.1):
  codes = [NAME_TO_CODE[name] for name in names]
  hold_cond = {
    NAME_TO_CODE[name]: hold_conditions[name] if name in hold_conditions else lambda code: True for name in names
  }
  buy_cond = {
    NAME_TO_CODE[name]: buy_conditions[name] if name in buy_conditions else lambda code: True for name in names
  }
  currency_to_account = {
    'hkd': ['ib'],
    'cny': ['a'],
    'usd': ['ib', 'schwab'],
  }
  for code in codes:
    if not hold_cond[code](code):
      return 'Clear %s(%s)'%(CODE_TO_NAME[code], code)
  holding_percent = {code : ACCOUNT_INFO['ALL']['holding-percent-all'][code] for code in codes}
  codes.sort(key = stock_eval)
  sum_percent = sum(holding_percent.values())
  if sum_percent + MIN_TXN_PERCENT <= percent:
    for code in codes:
      cash, op = GetCashAndOp(ACCOUNT_INFO.keys(), STOCK_INFO[code]['currency'], percent - sum_percent, backup)
      if cash > 0 and buy_cond[code](code):
        return GiveTip('Buy', code, cash)
  codes.reverse()
  if sum_percent >= percent + MIN_TXN_PERCENT:
    for code in codes:
      if holding_percent[code] > MIN_TXN_PERCENT:
        cash = EX_RATE[CURRENCY + '-' + STOCK_INFO[code]['currency']] * min(sum_percent - percent, holding_percent[code]) * ACCOUNT_INFO['ALL']['net']
        return GiveTip('Sell', code, cash)
  NET = ACCOUNT_INFO['ALL']['net']
  for a in range(len(codes)):
    worse = codes[a]
    if holding_percent[worse] <= 0: continue
    for b in range(len(codes) - 1, a, -1):
      better = codes[b] 
      worse_currency = STOCK_INFO[worse]['currency']
      better_currency = STOCK_INFO[better]['currency']
      valuation_ratio = stock_eval(worse) / stock_eval(better)
      swap_percent = holding_percent[worse]
      swap_cash = swap_percent * NET
      op = ''
      if worse_currency != better_currency:
        avail_cash, op = GetCashAndOp('ib', better_currency, swap_percent, backup)
        swap_cash = EX_RATE[better_currency + '-' + CURRENCY] * avail_cash
      sys.stderr.write('%s ==> %s valuation ratio = %.2f threhold = %.2f\n'%(CODE_TO_NAME[worse], CODE_TO_NAME[better], valuation_ratio, 1 + eval_delta))
      if valuation_ratio < 1 + eval_delta: continue
      if swap_cash < MIN_TXN_PERCENT * NET: continue
      return GiveTip('Sell', worse, swap_cash * EX_RATE[CURRENCY + '-' + worse_currency]) +\
               ' ==>\n    ' + op + '\n    ' +\
             GiveTip('Buy', better, swap_cash * EX_RATE[CURRENCY + '-' + better_currency]) +\
             ' due to valuation ratio = %.3f'%(valuation_ratio)
  return ''

def KeepPercentIf(name, percent, backup = [], hold_condition = lambda code: True, buy_condition = lambda code: True):
  delta = MIN_TXN_PERCENT
  code = NAME_TO_CODE[name]
  currency = STOCK_INFO[code]['currency']
  percent = percent if hold_condition(code) else 0
  holding_percent = ACCOUNT_INFO['ALL']['holding-percent-all'][code]
  if holding_percent > 0 and not hold_condition(code):
    return GiveTip('Clear', code, holding_percent * ACCOUNT_INFO['ALL']['net'] * EX_RATE[CURRENCY + '-' + currency])
  if holding_percent - percent > delta and not buy_condition(code):
    return GiveTip('Sell %d%% of '%(100 * (holding_percent - percent)), code,
        (holding_percent - percent) * ACCOUNT_INFO['ALL']['net'] * EX_RATE[CURRENCY + '-' + currency])
  cash, op = GetCashAndOp(ACCOUNT_INFO.keys(), currency, percent - holding_percent, backup)
  if percent - holding_percent > delta and cash > 0 and buy_condition(code) and GetMarketPriceChange(code) < 1.0:
    return op + GiveTip(' ==> Buy', code, cash)
  return '' 

def ScoreBanks(banks):
  key = 'valuation'
  scores ={}
  for bank in banks:
    finance = FINANCAIL_DATA_BASE[bank]
    scores[bank] = finance[key] if key in finance else 100.0
  banks.sort(key = lambda code: scores[code])
  for bank in banks:
    sys.stderr.write('%s: %f\n'%(CODE_TO_NAME[bank], scores[bank]))
  return banks, scores

def KeepBanks():
  min_txn_percent = max(0.02, MIN_TXN_PERCENT)
  swap_percent_delta = 0.005
  max_swap_percent = 0.1
  normal_valuation_delta = 0.15
  a2h_discount = max(normal_valuation_delta, 0.4 * MACRO_DATA['ah-premium'])
  h2a_discount = normal_valuation_delta
  same_h2a_discount = 0.05
  same_a2h_discount = 0.05
  overflow_valuation_delta = 0.02
  group_max_percent = [
    (['农业银行', '建设银行', '工商银行', '中国银行'],  0.5),
    (['招商银行', '兴业银行', '浦发银行', '民生银行'],  0.6),
    (['中信银行', '平安银行', '交通银行'], 0.4),
  ]
  all_banks = []
  for pr in group_max_percent:
    group, percent = pr[0], pr[1]
    for idx in range(len(group)):
      name = group[idx]
      code = NAME_TO_CODE[name]
      all_banks += [code]
      if 'hcode' in STOCK_INFO[code]:
        all_banks += [STOCK_INFO[code]['hcode']]
        group += [CODE_TO_NAME[STOCK_INFO[code]['hcode']]]

  holding_asset_percent = {
    bank: ACCOUNT_INFO['ALL']['holding-percent-all'][bank] for bank in all_banks
  }

  def GetPercent(code):
    percent = holding_asset_percent[code]
    for key in ['hcode', 'acode']:
      if key in STOCK_INFO[code]:
        percent += holding_asset_percent[STOCK_INFO[code][key]]
    return percent

  budget_percent = {}
  for pr in group_max_percent:
    group, percent = pr[0], pr[1]
    hold_percent_sum = 0.0
    for name in group:
      code = NAME_TO_CODE[name]
      hold_percent_sum += holding_asset_percent[code]
    sys.stderr.write('Bank group: %s percent %.1f%% max %.1f%%\n'%(', '.join(group), hold_percent_sum * 100, percent * 100))
    for name in group:
      code = NAME_TO_CODE[name]
      budget_percent[code] = percent - hold_percent_sum

  currentPercent = sum(map(lambda code: holding_asset_percent[code], all_banks))
  sys.stderr.write('bank holding percents: %s\n'%(str(holding_asset_percent)))
  sys.stderr.write('total bank market value = %.0f\n'%(currentPercent * ACCOUNT_INFO['ALL']['net']))
  banks = all_banks

  if len(banks) == 0:
    sys.stderr.write('No banks to consider!')
    return ''

  banks, valuation = ScoreBanks(banks) 

  NET = ACCOUNT_INFO['ALL']['net']
  
  banks.reverse()
  def OverflowSell(reduce_percent, overflow_valuation_delta = normal_valuation_delta, except_bank = None, candidates = None):
    if reduce_percent < MIN_TXN_PERCENT: return ''
    sys.stderr.write('Sell overflow %f\n'%(reduce_percent))
    worst = filter(lambda code: holding_asset_percent[code] > 0 and code != except_bank and (candidates is None or code in candidates), banks)[0]
    banks_to_sell = filter(lambda code: valuation[worst] / valuation[code] < 1 + overflow_valuation_delta and holding_asset_percent[code] > 0 and except_bank != code and (candidates is None or code in candidates), banks)
    sys.stderr.write('Banks to sell: %s \n'%(', '.join([CODE_TO_NAME[code] for code in banks_to_sell])))
    percent_sum = sum([holding_asset_percent[code] for code in banks_to_sell])
    ret = ''
    for code in banks_to_sell:
      currency = STOCK_INFO[code]['currency']
      sub_percent = min(1.0, reduce_percent / percent_sum) * holding_asset_percent[code]
      ret += GiveTip('Sell', code, sub_percent * NET * EX_RATE[CURRENCY + '-' + currency]) + '\n    '
    return ret
 
  for pr in group_max_percent:
    group, max_percent = pr[0], pr[1]
    percent = sum([holding_asset_percent[NAME_TO_CODE[name]] for name in group])
    if percent + MIN_TXN_PERCENT > max_percent:
      sell = OverflowSell(percent - max_percent, candidates = set([NAME_TO_CODE[name] for name in group]))
      if sell != '': return sell
    
  valuation_delta = 100
  
  swap_pairs = [] 
  for a in range(len(banks)):
    worse = banks[a]
    for b in range(len(banks) - 1, a, -1):
      better = banks[b]
      swap_pairs += [(worse, better, valuation[worse] / valuation[better])]
  swap_pairs.sort(key = lambda triple: triple[2], reverse = True)

  for bank in banks:
    if 'hcode' in STOCK_INFO[bank] and STOCK_INFO[bank]['hcode'] in valuation:
      swap_pairs = [(bank, STOCK_INFO[bank]['hcode'], 1.0),
                    (STOCK_INFO[bank]['hcode'], bank, 1.0)] + swap_pairs
  for pr in swap_pairs:
    worse = pr[0]
    better = pr[1]
    if holding_asset_percent[worse] == 0: continue
    worse_currency = STOCK_INFO[worse]['currency']
    better_currency = STOCK_INFO[better]['currency']

    valuation_delta = normal_valuation_delta
    sell_candidates = None
    if 'hcode' in STOCK_INFO[better] and STOCK_INFO[better]['hcode'] == worse:
      valuation_delta = same_h2a_discount
      sell_candidates = set([worse])
    elif 'hcode' in STOCK_INFO[worse] and STOCK_INFO[worse]['hcode'] == better:
      valuation_delta = same_a2h_discount
      sell_candidates = set([worse])

    valuation_ratio = valuation[worse] / valuation[better]
    swap_percent = min(holding_asset_percent[worse], budget_percent[better])
    sys.stderr.write('%s ==> %s swap percent = %.3f\n'%(CODE_TO_NAME[worse], CODE_TO_NAME[better], swap_percent))
    swap_percent = min(swap_percent, max_swap_percent)

    if budget_percent[worse] < 0:
      valuation_delta = overflow_valuation_delta
      swap_percent = min(swap_percent, -budget_percent[worse])
      sell_candidates = set([worse])

    swap_cash = swap_percent * NET
    sys.stderr.write('%s ==> %s delta = %.3f valuation ratio %.2f > threshold %.2f swap percent = %.2f\n'%(
                     CODE_TO_NAME[worse], CODE_TO_NAME[better], valuation_delta, valuation_ratio, 1 + valuation_delta, swap_percent))
    if valuation_ratio < (1 + valuation_delta): continue
    if swap_percent < swap_percent_delta: continue
    op = ''
    swap_percent = swap_cash / ACCOUNT_INFO['ALL']['net']
    if swap_percent < MIN_TXN_PERCENT: continue
    return OverflowSell(swap_percent, 0.02, better, sell_candidates) + op + '    ' +\
           GiveTip('Buy', better, swap_cash * EX_RATE[CURRENCY + '-' + better_currency]) +\
           ' due to valuation ratio = %.3f'%(valuation_ratio)
  return ''

def FenJiClassA():
  codes = GetClassA()
  sys.stderr.write('Got %s class A candidates.\n'%(len(codes)))
  rate_sum, count= 0, 0
  for code in codes:
    if FINANCAIL_DATA_BASE[code]['下折距离'.decode('utf-8')] > 0.15:
      rate_sum += FINANCAIL_DATA_BASE[code]['sdv/p']
      count += 1
  average_sdv_p = rate_sum / max(1, count)
  sys.stderr.write('Average rate: %.2f%% for class A.\n'%(average_sdv_p * 100))

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
  lower_PB = 0.91
  cash = GetCashAndOp(['ib', 'schwab'], STOCK_INFO[codeY]['currency'], 0.03)[0]
  sys.stderr.write('Cash for Yahoo %d %s PB %f < bound %f holding percent = %f\n'%(cash, STOCK_INFO[codeY]['currency'], PB, lower_PB, holding_percent[codeY]))
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

def CategorizedStocks():
  allMsg = []
  valuation_key = 'valuation'
  max_increase = 0.01
  for cate, stocks in CATEGORIZED_STOCKS.items():
    sys.stderr.write('Going through category: %s\n'%(cate))
    cate_msg = []
    holding_percent = 0
    for code in stocks:
      holding_percent += ACCOUNT_INFO['ALL']['holding-percent'].get(code, 0)
      finance = FINANCAIL_DATA_BASE[code] 
      is_numeric_value = lambda name: isinstance(finance.get(name, ''), float) or isinstance(finance.get(name, ''), int)
      if not is_numeric_value(valuation_key): continue
      valuation = finance[valuation_key]
      sys.stderr.write('Processing %s(%s): %s\n'%(CODE_TO_NAME[code], code, str(finance)))
      if len(filter(is_numeric_value, ['hold', 'buy', 'max-percent'])) < 3: continue
      hold, buy, percent = finance['hold'], finance['buy'], finance['max-percent']
      msg = KeepPercentIf(CODE_TO_NAME[code], percent,
          hold_condition = lambda code: valuation < hold,
          buy_condition = lambda code: valuation < buy)
      if msg != '': cate_msg += [msg + ' due to valuation=%.3f'%(valuation)]
    if len(cate_msg) > 0:
      allMsg += ['\n'.join(['* ' + cate + ': ' + str(int(holding_percent * 100)) + '%'] + cate_msg)]
  return '\n'.join(allMsg)
    
STRATEGY_FUNCS = {
  # '银行股': lambda: KeepBanks(),
  # '分级A': FenJiClassA,
  '分主题': CategorizedStocks,
}
