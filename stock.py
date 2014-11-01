#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from datetime import timedelta
from datetime import date
from datetime import time
from collections import defaultdict
import urllib2
import traceback
import copy
import re

from table_printer import *

#----------------------Template-----------------------------

HTML_TEMPLATE = """
<!--
You are free to copy and use this sample in accordance with the terms of the
Apache license (http://www.apache.org/licenses/LICENSE-2.0.html)
-->

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
    <title>
      Google Visualization API Sample
    </title>
    <script type="text/javascript" src="https://www.google.com/jsapi"></script>
    <script type="text/javascript">
      google.load('visualization', '1', {packages: ['corechart']});
    </script>
    <script type="text/javascript">
      function drawVisualization() {
        %s
      }
      google.setOnLoadCallback(drawVisualization);
    </script>
  </head>
  <body style="font-family: Arial;border: 0 none;">
    %s
  </body>
</html>
"""

FUNCTION_TEMPLATE = """
        {
          // Create and populate the data table.
          var data = new google.visualization.DataTable();
          data.addColumn('date', 'Date'); // Implicit series 1 data col.
          data.addColumn('number', '%s'); // Implicit domain label col.
          data.addColumn({type:'string', role:'annotation'}); // annotation role col.
          data.addColumn({type:'string', role:'annotationText'}); // annotationText col.
          data.addRows([
              %s
              ]); 
          // Create and draw the visualization.
          new google.visualization.LineChart(document.getElementById('%s')).draw(
              data,
              {
               curveType: "function",
               lineWidth: 2,
               pointSize: 5,
               legend: { position: 'bottom' },
               vAxis: {
                        minValue: %f,
                        maxValue: %f,
                        title: 'Price(%s)',
                      },
               explorer: {
                           actions: 'dragToZoom',
                           axis: 'horizontal',
                         }
              });
      }
"""

DIV_TEMPLATE = """
<div id="%s" style="width: 90%%, height: 600px;"></div>

"""

#----------Beginning of manually upated financial data-------

"""
银监会数据
http://www.cbrc.gov.cn/chinese/home/docViewPage/110009.html
2013年
 不良贷款率 1%
 拨备覆盖率 300%
 存贷比 66%
 年均ROA 1.345%
 年均ROE 20.5%
 季度平均杠杆率 15
 季度净息差 2.57% 2.59% 2.63% 2.68%
 季度非利息收入占比 23.84% 23.73% 22.46% 21.15%
 季度成本收入比 29.18% 29.44% 30.21% 32.90%
 季度大型商业银行不良贷款率 0.98% 0.97% 0.98% 1.00%
 季度股份制银行不良贷款率 0.77% 0.80% 0.83% 0.86%

2014年一季度大行平均不良率为1.03，股份行平均不良率为0.92。

2014Q2数据
  \           大行    股份行
  不良率      1.05    1.00
  拨备覆盖率  272%    235%
  ROA         1.45    1.23
  
加权风险资产收益率=净利润/加权风险资产
加权风险资产：银行业各类资产风险系数--（现金 证券 贷款 固定资产 无形资产)0% 10% 20% 50% 100%
GDP每下行1个点，不良率上升0.7个点。
GDP数据 2013 - 7.7, 2012 - 7.65, 2011 - 9.30, 2010 - 10.45, 2009 - 9.21

带0后缀的财务数据是最近4个季度的数据，未带0后缀的是未来四个季度后的数据估计
"""

EX_RATE = {
  'USD-USD': 1.0,
  'USD-RMB': 6.11,
  'USD-HKD': 7.75,
  'USD-YEN': 112.32,
}

CURRENCY = 'USD'

def InitExRate():
  all_currencies = [pr.split('-')[1] for pr in EX_RATE.keys()]
  for pr in EX_RATE.keys():
    currencies = pr.split('-')
    assert(len(currencies) == 2)
    EX_RATE[currencies[1] + '-' + currencies[0]] = 1.0 / EX_RATE[pr]
  for a in all_currencies:
    for b in all_currencies:
      EX_RATE[a + '-' + b] = EX_RATE[a + '-' + CURRENCY] * EX_RATE[CURRENCY + '-' + b]

InitExRate()

# Number of total shares
SHARES = {
  # 港股 ＋ A股
  '招商银行': 4590901172 + 20628944429,

  # 港股 ＋ A股
  '中国银行': 83622276395  + 195742329935,

  '兴业银行': 19049104143,

  '民生银行': 27106044823 + 6993579408,

  '建设银行': 240417319880 + 9593657606,

  'Weibo': 2 * 10**8,
  # subtract treasury stock.
  ':DeNA': 150810033 - 21283601,
  'Yahoo': 1008 * 10**6,

  '浦发银行': 18653471415,
  '中国机械工程': 908270000 + 3217430000,
}

CROSS_SHARE = {
  # The amount of Alibaba stocks Yahoo holds
  'Yahoo-Alibaba': 384 * 10**6,
}

ETF_BOOK_VALUE_FUNC = {
  #南方A50 ETF
  # http://www.csopasset.com/tchi/products/china_A50_etf.php
  '南方A50': lambda: GetValueFromUrl('http://www.csop.mdgms.com/iopv/nav.html?l=tc',
                                      ['即日估計每基金單位資產淨值', '<td id="nIopvPriceHKD">'],
                                      '</td>',
                                      float,
                                      ),
}

# (总面值，目前转股价)
CB = {
  '中国银行': [39386761000, 2.62],
  '民生银行': [19992377000, 8.18],
}

# 最大市值估计
CAP = {
  # 阿里入股5.86亿美元，占比18%
  'Weibo': 5.86 * 10**8 / 0.18 / SHARES['Weibo'],
  # 俄罗斯GDP是中国的四分之一，估值按百度目前的58B的四分之一计算。
  # 互联网渗透率，Russia 62%, China 50%.
  # 卢布贬值50%
  'Yandex': lambda: GetMarketCap('Baidu') / GetMarketCap('Yandex') / 4 * GetMarketPrice('Yandex') * (38.0 / 50.0) * 0.5,

  # 按照阿里收购UC出资的股票部分和对UC的估值计算。
  'Alibaba': 72,

  # 回购价格 34.94
  'Yahoo': lambda: (
                    2.2 * 10**12 * 0.36 * 0.72 * EX_RATE['YEN-USD']  # Yahoo Japan
                    + CROSS_SHARE['Yahoo-Alibaba'] * GetMarketPrice('Alibaba') * 0.72 # IPO后的间接持股打折
                    + (12579507 * 10**3 + 1056992 * 10**3  # 当前现金
                       + 1.1 * 10**9  # 加回预防的股票回购计划现金
                       - 9.4 * 0.38 * 10**9  # 减去阿里IPO时套现的现金税金
                       - (4377961 + 1155168 + 146072) * 10**3 # 减去其他负债
                      ) # 净现金NCAV = Current Assets - Total Liabilities 包括卖出阿里股份
                   )
                   / SHARES['Yahoo'],
}

BVPS0 = {
  # 最近一次报告期的净资产
  # 招商银行, 2014年 Q1
  # '招商银行': 10**6 * 285936.0 / SHARES['招商银行'],
  # 雪球大牛预测2014年底
  '招商银行': 11.97,
  
  # 2014 Q3
  '中国银行': 10**6 * 10053.74 / SHARES['中国银行'],

  # 2013 H1
  '兴业银行': 223256.0 * 10**6 / SHARES['兴业银行'],

  # 2013年年报
  '民生银行': 222199.0 * 10**6 / SHARES['民生银行'],

  '建设银行': 4.79,

  'Weibo': CAP['Weibo'],

  'Yandex': CAP['Yandex'],

  'Yahoo': CAP['Yahoo'],

  # 净现金
  ':DeNA': 1.0 * (110418 - 52858) * 10**6 / SHARES[':DeNA'],

  '信诚300A': 1.046, #GetHexinFundBookValue('http://jingzhi.funds.hexun.com/150051.shtml')

  '南方A50': ETF_BOOK_VALUE_FUNC['南方A50'],
  '浦发银行': 218312.0 * 10**6 / SHARES['浦发银行'],
  '中国机械工程': EX_RATE['RMB-HKD'] * 12032874000.0 / SHARES['中国机械工程'],
  '中行转债': lambda: 100.0 * GetMarketPrice('中国银行') / CB['中国银行'][1],
  'Bank of America': 14.3,

  '工商银行': 4.06,
  '中信银行': 4.84,
}

# TTM
EPS0 = {
  '兴业银行': 41211.0 * 10**6 / SHARES['兴业银行'],
  # 根据2014H计算
  '中国银行': 1.0 * (156911 - 80721 + 89724) * 10**6 / SHARES['中国银行'],
  # 根据2014H计算
  '招商银行': 1.* (51342 - 26271 + 30459) * 10**6 / SHARES['招商银行'],
  '建设银行': 1.* (214657 + 65780 - 59580) * 10**6 / SHARES['建设银行'],

  '中国机械工程': (1077132000.0 + (1974823000 - 995680000) * 1.05) /SHARES['中国机械工程'] * EX_RATE['RMB-HKD'],
}

FORGOTTEN = {
  # 'Facebook': 0,
}

"""
根据TTM预测一年以后

银行资产增长受限于以下几个约束
1. 核心资产充足率 8.5% 9.5%
2. 存贷比 < 75%
3. M2增长 < 13%
4. 存款准备金率 < 20%

生息资产 = 客户贷款 + 债券投资 + 存放中央银行 + 存拆放同业
证券投资＝交易性金融资产+可供出售金融资产+持有至到期投资+应收款项债券投资
存拆放同业 = 存放同业款项 + 拆出资金 + (买入返售金融资产)

主要估计资产增长，净利差和资产减值。
"""

# 净利差
NIM = {
  '民生银行': 5.65 - 3.23,
  '招商银行': 5.07 - 2.7,
  '中国银行': 4.26 - 2.11,
}
# 核心资本充足率
CORE_CAP = {
  '民生银行': 8.93,
  '招商银行': 9.47,
}

"""
# 银行重点考虑一下三方面的资产减值风险
2. 房地产开发贷款：表内余额15万亿，表外10万亿。
2. 过剩产业贷款：贷款总额5万亿，包括5大行业钢铁，船舶，水泥，有色和电解铝。
   假设产能去化率11.2%（不良率），未来两年产生不良5700亿。
3. 地方融资平台：贷款总额12万亿，把不可偿付比例16%作为坏账比例的近似
"""
LOSS_RATE = 0.6
BVPS = {
  # 招商银行, 2013年年报
  '招商银行': BVPS0['招商银行'] +
              (
                48764 # 加回贷款减值准备余额
                + (78 + 64) # 加回其他减值准备
                - (2996 + 9953) # 减去商誉和无形资产
                - 1.0 * (  # 不良贷款损失率
                  18332 # 已有不良总额
                  + 24603 * 20.0 / 100 # 从关注迁移到可疑的估计
                  + 2154159 * 2.5 / 100 * 20.0 / 100   # 正常类->关注类->可疑类
                  + 126201 * 1.08 * ( # 内地公司贷款(加上增长估计)额外损失，包括以下三部分，贷款增长受限于核心资本充足率
                    0.92 / 100 * 4 # 股份行平均不良率，最坏增长400%
                  )
                  + 131061 * 1.08 * 20.0 / 100 # 房地产业贷款损失
                )
                - 117391 * 4 * 0.7 / 100 # 买入返售－信托受益权损失率按GDP下行带来的不良率计算
                # 媒体已报道的坏账:1)青岛港重复抵押
                - 600
              ) * 10**6 / SHARES['招商银行'],

  #中国银行，2013年年报 + 2014 Q1
  '中国银行': BVPS0['中国银行'] +
              (
                + 168049 + 15096 # 加回贷款减值准备余额
                - (1982 + 12819) # 减去商誉和无形资产
                - 1.0 * (  # 不良贷款损失率
                  80320 # 最近一次年报已有不良总额
                  + 189293 * 0.15 # 从关注迁移到可疑的估计
                  + 7345227 * 2 / 100 * 15.0 / 100   # 正常类->关注类->可疑类
                  + 4192155 * 1.06 * ( # 内地公司贷款(加上增长估计)额外损失，包括以下三部分
                    1.03 / 100 * 4 # 大行平均不良率，最坏增长400%
                  )
                  + 405075 * 20.0 / 100 # 房地产业贷款损失
                  + 188500 * 5.0 / 100 # 过剩产业贷款损失
                ) * 1.02 # 乘以增长率
                - 248945 * 6 * 0.7 / 100 # 买入返售－信托受益权损失率按GDP下行6个点带来的不良率计算
                # 媒体已报道的坏账:1) 违规放款 2)青岛港重复抵押 3) 四川
                - 10300 * 0.5
                - 2100
                - 2400
              ) * 10**6 / SHARES['中国银行'],

  # 2014H
  '民生银行': BVPS0['民生银行'] +
              (
                + 34146 # 加回贷款减值准备余额
                - (607106 + 188900 + 157437 + 45466) * 1.0 / 1000 # 表外资产减值
                - (1982 + 12819) # 减去商誉和无形资产
                - LOSS_RATE * (  # 不良贷款损失率
                  15818 # 最近一次年报已有不良总额
                  + 45697 + 336 # 重组贷款和逾期贷款
                  + 26540 * (28.71 + 23.72) / 200 # 从关注迁移到可疑的估计
                  + 1680465 * (1.66 + 2.4) / 200 * (28.71 + 23.72) / 200   # 正常类->关注类->可疑类
                  + 528535 * 2.0 / 100 # 减去华东地区额外贷款损失
                  + 188547 * 2.0 / 100 # 房地产业贷款损失
                  + 99969 * 1.0 / 100 # 应收款类投资损失 
                  + 123889 * 1.0 / 100 # 信用卡贷款损失
                  + 5371 * 50.0 / 100 # 贷款应收利息损失
                )
              ) * 10**6 / SHARES['民生银行'],

  # 2014H，净现金 减去应收款计提50%
  '中国机械工程': EX_RATE['RMB-HKD'] * 10**3 * 6233446.0 / SHARES['中国机械工程'],

  # 雪球大牛对2014年的预测
  '浦发银行': 13.0,
}

EPS = {
  #南方A50ETF，数据来自sse 50ETF统计页面
  # http://www.sse.com.cn/market/sseindex/indexlist/indexdetails/indexturnover/index.shtml?FUNDID=000016&productId=000016&prodType=4&indexCode=000016
  '南方A50':  9.2116 / 7.64,
  # TTM + Fy2014 Q2 guidance
  ':DeNA': (5.7 + 0.6 * (7 + 9.7 + 11.4)) * 10**9 / SHARES[':DeNA'],

  # 2014 Q1
  # 根据2014 H1，假设下半年增长率10%
  # 净利润 ＝ (拨备前利润 － 拨备) * (1 - 税率)
  '招商银行': 1.0 * (
      30459 +  # 2014 H1已经实现
      # 2014H2通过2013H2估计，拨备前利润按15%增长，资产减值按100%增长。
      ((68425 + 10218 - (34848 + 4959)) * 1.15  # 2013H2的拨备前利润
          - (10218 - 4959) * 2.5)  # 减去估计的减值损失
      * (1 - 0.24)   # 23%的所得税率
      * (1 - 0.2 / 100) # 减去少数股东收益
  ) * 10**6 / SHARES['招商银行'],
  
  # 根据2014 H1，假设下半年增长率10%
  # 净利润 ＝ (拨备前利润 － 拨备) * (1 - 税率)
  '中国银行': 1.0 * (
      89724 +  # 2014 H1已经实现
      # 2014H2通过2013H2估计，拨备前利润按5%增长，资产减值按100%增长。
      ((212777 + 23510 - (110251 + 14142)) * 1.05  # 2013H2的拨备前利润
          - (23510 - 14142) * 2.0)  # 减去估计的减值损失
      * (1 - 0.23)  # 23%的所得税率
      * (1 - 4.0 / 100) # 减去少数股东收益
  ) * 10**6 / SHARES['中国银行'],

  # 按照待已签约待生效合同种不同工程类型的比例计算未来的毛利率
  # 费用开支约为毛利的50%
  '中国机械工程': 10**6 * 15384 * 1.05 *  # 一年的工程收入
                  (
                    0.25 * 0.67 # 电力能源的毛利
                    + 0.08 * 0.33 # 其他工程低毛利
                  )
                  * (1.0 + 0.05) # 贸易毛利占比
                  * 0.5 # 减去费用
                  * (1 - 0.04) # 减去坏账
                  * (1- 0.26) # 税收
                  / SHARES['中国机械工程'] * EX_RATE['RMB-HKD'],
}

# Sales per share.
SPS = {
  # FY2013 Q4
  # TTM = latest Q + ...
  # 35.6 is the guidance for FY2014 Q2.
  ':DeNA': (35.6 + 0.7 * (35.8 + 39.8 + 41.7)) * 10**9 / SHARES[':DeNA'],
}

DV_TAX = 0.1

# 已公布分红
DVPS0 = {
  # Apple once a quarter.
  # 20140206 - 3.05
  # Tax rate 0.1
  'Apple': 3.29 * 4 / 7,

  # :DeNA once a year.
  # For FY2013
  ':DeNA': 37.0,

  # 已公布
  '中国银行': 0.196,

  # 已公布
  '招商银行': 0.62,

  '建设银行': 0.3,
  
  #'南方A50': 0.353136, # (3.63 - 1.0) / 100 * 8.4,
  # 2014年
  '南方A50': 0.28 / EX_RATE['HKD-RMB'],
  '中国机械工程': 0.19 * EX_RATE['RMB-HKD'], # 2013年股息
  # 定存利率加3%
  '信诚300A': 0.06,
}

# The portion of EPS used for dividend.
DVPS = {
  # 假定30%分红率，税率10%.
  # '招商银行': EPS['招商银行'] * 0.3,
  # '招商银行': 2.4 * 0.3,
  # 来自雪球大牛预测
  '招商银行': 2.46 * 0.3,

  # 过去四年年分红率 [0.35, 0.34, 0.36, 0.35]
  # 13年年报称以后不少于10%现金分红
  # 减去优先股股息,2014年后半年发行65亿美元(400亿人民币)，股息率6.75%
  '中国银行': (EPS['中国银行'] - 400 * 10**8 * 0.0675 / 2 / SHARES['中国银行'])  * 0.35,
  # 来自雪球大牛预测
  '建设银行': 0.93 * 0.35,

  # 来自雪球大牛预测
  '工商银行': 0.7 * 0.35,

  # 来自雪球大牛预测
  '浦发银行': 2.6 * 0.3,
}

DIVIDEND_DATE = {
  '建设银行H': date(2014, 7, 2),
  '建设银行': date(2014, 7, 10),
  '招商银行H': date(2014, 7, 3),
  '招商银行': date(2014, 7, 11),
  '中国银行H': date(2014, 6, 19),
  '中国银行': date(2014, 6, 26),
}

URL_CONTENT_CACHE = {
}

#----------End of manually upated financial data-------

#----------Beginning of crawler util functions-----------------

# appannie header: User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36

def AppannieScore(company, country = 'japan'):
  url_temp = 'http://www.appannie.com/apps/%s/top/%s/overall/%s'
  urls = [
           url_temp%('ios', country, '?device=iphone'),
           url_temp%('ios', country, '?device=ipad'),
           url_temp%('google-play', country, ''),
         ]
  res = 0
  for url in urls:
    if url not in URL_CONTENT_CACHE:
      request = urllib2.Request(url)
      request.add_header('User-Agent',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36') 
      sys.stderr.write('Getting url: %s\n', url)
      URL_CONTENT_CACHE[url] = urllib2.urlopen(request).read()
    content = URL_CONTENT_CACHE[url]
    idx = content.find(company)
    while idx >= 0:
      content = content[idx + len(company):]
      res += 1
      idx = content.find(company)
  return res
    

def GetValueFromUrl(url, feature_str, end_str, func, throw_exp = True):
  try:
    if url not in URL_CONTENT_CACHE:
      request = urllib2.Request(url)
      URL_CONTENT_CACHE[url] = urllib2.urlopen(request).read()
    content = URL_CONTENT_CACHE[url]
    for fs in feature_str:
      content = content[len(fs) + content.find(fs):]
    return func(content[0:content.find(end_str)])
  except Exception, e:
    sys.stderr.write('Exception ' + str(e) +'\n')
    sys.stderr.write('Failed to open url: ' + url + '\n')
    if throw_exp: raise
    return func('0.0')

def GetJapanStockPriceAndChange(code):
  url = 'http://jp.reuters.com/investing/quotes/quote?symbol=%s.T'%(str(code))
  try:
    return (GetValueFromUrl(url, ['<div id="priceQuote">', '<span class="valueContent">'],
                            '</span>', lambda s: float(s.replace(',', ''))),
            GetValueFromUrl(url, ['<div id="percentChange">', '<span class="valueContent"><span class="', '>'],
                            '%', lambda s: float(s.replace(',', ''))))
  except:
    return [float('inf'), 0.0]

def GetJapanStockBeta(code):
  url = 'http://jp.reuters.com/investing/quotes/quote?symbol=%s.T'%(str(code))
  try:
    return GetValueFromUrl(url,
        ['<span id="quoteBeta">'],
         '</span>', lambda s: float(s.replace(',', '')))
  except:
    return 0.0

#----------End of crawler util functions-----------------

#----------Begining of global variables------------------

MAX_PERCENT_PER_STOCK = 0.2

PERCENT_UPPER = {
  '南方A50': 0.5,
  '中国银行': 0.72,
  '建设银行': 0.4,
  '招商银行': 0.40,
}

NO_RISK_RATE = 0.05
LOAN_RATE = 0.016

STOCK_BETA = {
  '2432': GetJapanStockBeta,
}

REAL_TIME_VALUE_CACHE = {
}

REALTIME_VALUE_FUNC = {
}

CODE_TO_NAME = {
  'RMB': 'RMB',
  'USD': 'USD',
  'HKD': 'HKD',
}

NAME_TO_CODE = {
}

DA_LAN_CHOU = set([
  '中国银行',
  '建设银行',
  '招商银行',
  '工商银行',
  '中行转债',
  '南方A50',
])

WATCH_LIST_DISCONTED_H = {
}

WATCH_LIST_BANK = {
  '601988': '中国银行',
  '601939': '建设银行',
  '600036': '招商银行',
  '600000': '浦发银行',
  '601166': '兴业银行',
  'BAC': 'Bank of America',
}

WATCH_LIST_BANK_1 = {
  '601398': '工商银行',
  '600016': '民生银行',
  '600015': '华夏银行',
  '601328': '交通银行',
  '601998': '中信银行',
  '601818': '光大银行',
  '601288': '农业银行',
}

WATCH_LIST_DIVIDEND = {
  '600028': '中国石化',
  '000002': '万科',
  '000651': '格力电器',
}

WATCH_LIST_INSURANCE = {
  '601318': '中国平安',
  '601336': '新华保险',
}

WATCH_LIST_INTERNET = {
  'FB': 'Facebook',
  'GOOG': 'Google',
  'AAPL': 'Apple',
  'WB': 'Weibo',
  'YNDX': 'Yandex',
  'YHOO': 'Yahoo',
  'BABA': 'Alibaba',
  'BIDU': 'Baidu',
}

WATCH_LIST_MOBILE_GAMES = {
  '2432': ':DeNA',
}

WATCH_LIST_CB = {
  '113001': '中行转债',
}

WATCH_LIST_ETF = {
  #南方A50 ETF
  '02822': '南方A50',
  '150051': '信诚300A',
} 

WATCH_LIST_OTHER = {
  '01829': '中国机械工程',
  '00826': '天工国际',
}

AH_PAIR = {
  '600036': '03968',
  '601988': '03988',
  '600016': '01988',
  '601939': '00939',
  '601398': '01398',
  '601318': '02318',
  '601288': '01288',
  '601998': '00998',
  '601328': '03328',
  '601818': '06818',
  '601336': '01336',
  '000666': '00350',
  '600028': '00386',
  '000002': '02202',
}

CB_INFO = {
}

# In the form of '2432': [price, change, cap].
market_price_cache = {
}

market_price_func = {
  '2432': lambda: GetJapanStockPriceAndChange('2432'),
  'ni225': lambda: [0,
                    GetValueFromUrl('http://www.bloomberg.com/quote/NKY:IND',
                                    ['<meta itemprop="priceChangePercent" content="'],
                                    '"', lambda s: float(s.replace(',', '')))]
}

RZ_BASE = {
  '兴业银行': 6157420241,
  '招商银行': 3909913752,
  '中国银行': 322251548,
}

STOCK_CURRENCY = {
  ':DeNA': 'YEN',
}

total_capital = defaultdict(int)

total_capital_cost = defaultdict(int)

total_investment = {
  'RMB': 0, 'USD': 0, 'HKD': 0, 'YEN': 0,
}
net_asset = defaultdict(int)

total_transaction_fee = defaultdict(float)

total_market_value = defaultdict(int) 

holding_percent = defaultdict(float)

g_holding_shares = defaultdict(int)

NET_ASSET = 0.0

#----------Begining of global variables------------------

#--------------Beginning of logic util functions---------------
def IsLambda(v):
  return isinstance(v, type(lambda: None)) and v.__name__ == (lambda: None).__name__

def GetCurrency(code):
  if code in STOCK_CURRENCY:
    return STOCK_CURRENCY[code]
  elif code.isdigit() and code[0] == '0' and len(code) == 5:
    return 'HKD'
  elif code.isalpha():
    return 'USD'
  elif code.isdigit() and len(code) == 4:
    return 'YEN'
  return 'RMB'

def myround(x, n):
  if n == 0:
    return int(x)
  return round(x, n)

def myround(x, n):
  if n == 0:
    return int(x)
  return round(x, n)

def GetPE0(code, mp):
  return myround(mp / EPS0[code], 1) if code in EPS0 else float('inf')

def GetPE(code, mp):
  if code in EPS:
    return myround(mp / EPS[code], 1)
  return float('inf')

def GetPS(code, mp):
  if code in SPS:
    return myround(mp / SPS[code], 1)
  return float('inf')

def GetDR(code, mp):
  if code in DVPS:
    return round(DVPS[code] / mp * (1.0 - DV_TAX), 3)
  return 0.0

def GetDR0(code, mp):
  if code in DVPS0:
    return round(DVPS0[code] / mp * (1.0 - DV_TAX), 3)
  return 0.0

def GetPB1(code, mp):
  if code in BVPS1:
    return mp / BVPS1[code]
  return float('inf')

def GetBeta(code):
  return STOCK_BETA[code](code) if code in STOCK_BETA else 10

def GetPB0(code, mp):
  if code in BVPS0:
    dilution = 1.0
    if code in CB:
      trans = CB[code][1]
      if trans < BVPS0[code]:
        dilution = (1.0 + CB[code][0] * 1.0 / BVPS0[code] / SHARES[code]) / (
          1.0 + CB[code][0] / trans / SHARES[code])
    book_value = BVPS0[code]() if IsLambda(BVPS0[code]) else BVPS0[code]
    return mp / (book_value * dilution)
  return float('inf')
 
def GetPB(code, mp):
  if code in BVPS:
    dilution = 1.0
    if code in CB:
      trans = CB[code][1]
      if code in DVPS:
        trans -= DVPS[code]
      if trans < BVPS[code]:
        dilution = (1.0 + CB[code][0] * 1.0 / BVPS[code] / SHARES[code]) / (
          1.0 + CB[code][0] / trans / SHARES[code])
    return mp / (BVPS[code] * dilution)
  return float('inf')
 
def GetCAP(code, mp):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  if code in CAP:
    return CAP[code]() if IsLambda(CAP[code]) else CAP[code]
  return 0

def GetXueqiuUrlPrefix(code):
  currency = GetCurrency(code)
  if currency == 'RMB': return ['SH', 'SZ']
  return ['']

def GetXueqiuMarketPrice(code):
  url_prefix = 'http://xueqiu.com/S/'
  price_feature_str = ['<div class="currentInfo"><strong data-current="']
  price_end_str = '"'
  change_feature_str = ['<span class="quote-percentage">', '(']
  change_end_str = '%)'
  cap_feature_str = ['市值：<span>']
  cap_end_str = '<'
  book_value_str = ['单位净值', '<span>']
  book_value_end_str = '<'
  for pr in GetXueqiuUrlPrefix(code):
    url = url_prefix + pr + code
    try:
      price = GetValueFromUrl(url, price_feature_str, price_end_str, float)
      change = GetValueFromUrl(url, change_feature_str, change_end_str, float)
      cap = GetValueFromUrl(url, cap_feature_str, cap_end_str,
                            lambda s: float(s.replace('亿', '')) * 10**8, False)
      book_value = GetValueFromUrl(url, book_value_str, book_value_end_str, float, False)
      return [price, change, cap, book_value]
    except:
      continue
  return [0.01, 0.0, 0.0, 1.0]

def GetSinaUrlPrefix(code):
  currency = GetCurrency(code)
  if currency == 'RMB': return ['sh', 'sz']
  elif currency == 'HKD': return ['hk']
  elif currency == 'USD': return ['gb_']
  return ['']

def GetMarketPriceFromSina(code):
  url_prefix = 'http://hq.sinajs.cn/list='
  price_end_str = '"'
  for pr in GetSinaUrlPrefix(code) + GetSinaUrlPrefix(code):
    suffix = pr + code.lower()
    url = url_prefix + suffix
    try:
      values = GetValueFromUrl(url, 'hq_str_%s="'%(suffix), '"', str)
      if len(values) == 0: continue
      sys.stderr.write('Get string for %s: %s\n'%(code, values))
      values = values.split(',')
      if suffix.find('hk') == 0: values = values[1:]
      price, change, cap, book_value = 0, 0, 0, 1.0
      if suffix.find('gb_') == 0:
        price, change, cap = float(values[1]), myround(float(values[2]), 1), float(values[12])
      elif suffix.find('hk') == 0:
        price, change = float(values[5]), myround(float(values[7]), 1)
      else:
        price = float(values[3])
        prev_price = float(values[2])
        change = myround(100.0 * (price - prev_price) / prev_price, 1)
      data = [price, change, cap, book_value]
      sys.stderr.write('Got market data for %s = %s\n'%(code, str(data)))
      return data
    except:
      time.sleep(3)
      continue
  return [0.0, 0.0, 0.0, 0.0]

def GetXueqiuETFBookValue(code):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  return GetXueqiuMarketPrice(code)[3]

def GetMarketPrice(code):
  if code.find('@') != -1:
    tokens = re.split('[-@]', code)
    strike = float(tokens[2])
    mp = GetMarketPrice(tokens[0])
    return max(0.01, strike - mp) if tokens[1].lower() == 'put' else max(0.01, mp - strike)
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  sys.stderr.write('Getting market price for ' + code + '\n')
  if code in market_price_cache:
    return market_price_cache[code][0]
  func = lambda: GetMarketPriceFromSina(code)
  if code in market_price_func:
    func = market_price_func[code] 
  try:
    data = func()
    market_price_cache[code] = data
    return data[0]
  except:
    sys.stderr.write('Failed to get market price for %s.\n'%(code))
    return 0.0

def GetMarketCap(code):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  if code not in market_price_cache:
    GetMarketPrice(code)
  if code in market_price_cache:
    return market_price_cache[code][2]
  return 0.0

def GetMarketPriceChange(code):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  if code not in market_price_cache:
    GetMarketPrice(code)
  if code in market_price_cache:
    return market_price_cache[code][1]
  return 0.0

def GetMarketPriceInBase(code):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  mp = GetMarketPrice(code)
  currency = GetCurrency(code);
  mp *= EX_RATE[currency + '-' + CURRENCY]
  return mp

def GetIRR(market_value, cash_flow_records):
  if len(cash_flow_records) == 0:
    return 0.0
  cash_flow_records.sort()
  low, high = -1.0, 5.0
  day_loan_rate = pow(LOAN_RATE + 1, 1.0 / 365)
  now = date.today()
  while low + 0.004 < high:
    mid = (low + high) / 2
    day_rate = pow(mid + 1, 1.0 / 365)
    balance = 0
    prev_date = cash_flow_records[0][0]
    dcf = 0
    for record in cash_flow_records:
      if balance < 0:
        balance *= pow(day_loan_rate, (record[0] - prev_date).days)
      prev_date = record[0]
      if record[1] in total_investment:
        #invest money or withdraw cash
        balance -= record[2]
        dcf += record[2] * pow(day_rate, (now - record[0]).days)
      else:
        balance += record[2]
    if balance < 0:
      balance *= pow(day_loan_rate, (now - prev_date).days)
    if balance + market_value + dcf > 0:
      low = mid
    else:
      high = mid
  return low

def GetAHDiscount(code, mp = 0):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  if code not in AH_PAIR:
     return 0
  mp_base, mp_pair_base = GetMarketPriceInBase(code), GetMarketPriceInBase(AH_PAIR[code])
  return (mp_pair_base - mp_base) / mp_base

def GetRZ(code, mp = 0):
  code = NAME_TO_CODE[code] if code in NAME_TO_CODE else code
  if GetCurrency(code) != 'RMB': return 0.0
  url_pattern = 'http://data.eastmoney.com/rzrq/detail/%s,1.html'
  try:
    rz = GetValueFromUrl(url_pattern%(code),
                           [
                            '<th>融资余额(元)</th>',
                            '<td class="right">',
                           ],
                           '</td>' , lambda s: int(s.replace(',', '')))
    rq = GetValueFromUrl(url_pattern%(code),
                           [
                            '<th>融资余额(元)</th>',
                            '<td class="right">',
                            '<td class="right">',
                            '<td class="right">',
                            '<td class="right">',
                           ],
                           '</td>' , lambda s: int(s.replace(',', '')))
  except:
    return float('-1')
  return 1.0 * (rz - rq) / RZ_BASE[CODE_TO_NAME[code]] if code in CODE_TO_NAME and CODE_TO_NAME[code] in RZ_BASE else rz - rq

FINANCIAL_FUNC = {
  'P/E0': GetPE0,
  'P/E': GetPE,
  'P/B0': GetPB0,
  'P/B': GetPB,
  'P/S': GetPS,
  'CAP': GetCAP,
  'AHD': GetAHDiscount,
  'DR': GetDR,
  'DR0': GetDR0,
  'MP': lambda code, mp: GetMarketPrice(code),
}

#--------------End of logic util functions---------------

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
  
def BuyYandex():
  return GenericDynamicStrategy(
    'Yandex',
    'P/B0',
    [1.0, 0.8],
    [0.02, 0.08],
    1.2,
    buy_condition = lambda code: GetMarketPriceChange(code) <= -2);

def BuyYahoo():
  return GenericDynamicStrategy(
    'Yahoo',
    'P/B0',
    [1, 0.8],
    [0.05, 0.15],
    1.1,
    buy_condition = lambda code: GetMarketPriceChange(code) <= -1,
    sell_condition = lambda code: GetMarketPriceChange(code) >= 1);

def BuyApple():
  return GenericDynamicStrategy(
    'Apple',
    'DR0',
    [0.03, 0.04],
    [0.1, 0.3],
    0.15,
    buy_condition = lambda code: GetMarketPriceChange(code) <= 0);
  
def BuyBig4BanksH():
  codes = map(lambda name: NAME_TO_CODE[name],
              [
               '工商银行H',
               '建设银行H',
               '中国银行H',
               '招商银行H',
              ])
  for code in codes:
    dis = GetAHDiscount(code)
    changeH = GetMarketPriceChange(code)
    change = GetMarketPriceChange(AH_PAIR[code])
    if dis >= 0.001 and changeH < 0:
      return 'Buy %s(%s) %d units @%.2f AH discount=%.1f%%'%(
        CODE_TO_NAME[code], code, int(NET_ASSET * 0.02 / GetMarketPriceInBase(code)),
        GetMarketPrice(code), dis * 100.0)
  return ''

def BuyCMBH():
  return GenericDynamicStrategy(
    '招商银行H',
    'AHD',
    [-0.05, 0.05],
    [0.1, 0.2],
    -0.1,
    0.05,
    buy_condition = lambda code: GetMarketPriceChange(code) < 0 and GetDR('招商银行H', GetMarketPrice('招商银行H')) > 0.045)

def BuyCMB():
  return GenericDynamicStrategy(
    '招商银行',
    'DR',
    [0.06, 0.07],
    [0.3, 0.4],
    5.0,
    buy_condition = lambda code: GetAHDiscount(code) >= 0 and GetMarketPriceChange(code) < 0)

def BuyCCB():
  return GenericDynamicStrategy(
    '建设银行',
    'DR',
    [0.07, 0.08],
    [0.1, 0.2],
    5.0,
    buy_condition = lambda code: GetAHDiscount(code) >= 0.05)

def BuyDeNA():
  # 同类公司P/S
  # KONAMI: 1.5
  # SEGA: 1.3
  # Zynga: 1.2
  return GenericDynamicStrategy(
    ':DeNA',
    'P/S',
    [1.1, 0.8],
    [0.05, 0.12],
    2.0,
    buy_condition = lambda code: GetMarketPriceChange(code) < min(0.0,
      1.1 * GetBeta(code) * GetMarketPriceChange('ni225')));

def BuyA50():
  return GenericDynamicStrategy(
    '南方A50',
    'P/E',
    [7.5, 7],
    [0.2, 0.3],
    9.0,
    buy_condition = lambda code: GetMarketPriceChange(code) < 0.0);

def BuyBOCH():
  return GenericDynamicStrategy(
    '中国银行H',
    'DR',
    [0.065, 0.075],
    [0.1, 0.2],
    0.05,
    buy_condition = lambda code: GetPB(code, GetMarketPriceChange(code)) < 0.85 and GetMarketPriceChange(
                                 code) < 0.0 and GetAHDiscount('中国银行') >= min(GetAHDiscount(
                                   '建设银行') / 2, min(GetAHDiscount('工商银行') / 2, -0.025)),
    sell_condition = lambda code: GetMarketPriceChange(code) > 0)

def BuyBOC():
  return GenericDynamicStrategy(
    '中国银行',
    'DR',
    [0.065, 0.075],
    [0.1, 0.2],
    0.05,
    buy_condition = lambda code: GetPB(code, GetMarketPriceChange(code)) < 0.85,
    sell_condition = lambda code: GetMarketPriceChange(code) > 0)
 
def BuyWeibo():
  return GenericDynamicStrategy(
    'Weibo',
    'P/B0',
    [1, 0.8],
    [0.05, 0.1],
    # 等阿里收购微博的消息
    1.5,
    buy_condition = lambda code: GetMarketPriceChange(code) < -2);

def KeepDaLanChou():
  holding = 0
  for dalanchou in DA_LAN_CHOU:
    dalanchou = NAME_TO_CODE[dalanchou]
    holding += holding_percent[dalanchou]
    if dalanchou in AH_PAIR:
      holding += holding_percent[AH_PAIR[dalanchou]]
  target = 0.7
  if holding < target:
    return 'Buy %.1fK RMB DaLanChou in (%s)'%((target - holding) * NET_ASSET / 1000,
      ', '.join([str(x) for x in DA_LAN_CHOU]))
  return ''

def CMBHandCMB():
  return GenericChangeAH('招商银行', 0.02, 0.15)

def BOCHandBOC():
  if GetAHDiscount('中国银行') > GetAHDiscount('建设银行') or GetAHDiscount('中国银行') > GetAHDiscount('工商银行'):
    return '中国银行H(%s) premium is too high: %f'%(NAME_TO_CODE['中国银行H'], GetAHDiscount('中国银行'))
  return ''

def ReduceOverflow():
  for code in holding_percent.keys():
    if holding_percent[code] == 0.0: continue
    if code in AH_PAIR and holding_percent[AH_PAIR[code]] > 0 and GetAHDiscount(code) > 0.0: continue
    upper = PERCENT_UPPER[code] if code in PERCENT_UPPER else MAX_PERCENT_PER_STOCK
    hold = holding_percent[code] + (holding_percent[AH_PAIR[code]] if code in AH_PAIR else 0.0)
    if hold > upper:
      print 'Sell %s(%s) %d units @%.3f'%(
        CODE_TO_NAME[code], code,
        (hold - upper) * NET_ASSET / GetMarketPriceInBase(code),
        GetMarketPrice(code))
  return ''

def CMBandBOC():
  holding_percent[NAME_TO_CODE['中国银行']] += holding_percent[NAME_TO_CODE['中行转债']]
  res = GenericSwapStrategy('中国银行', '招商银行', 'DR', 1.0, 1.25, 0.05)
  holding_percent[NAME_TO_CODE['中国银行']] -= holding_percent[NAME_TO_CODE['中行转债']]
  return res

def BOCHandA50():
  return GenericSwapStrategy('中国银行H', '南方A50',
                             lambda: GetDR(NAME_TO_CODE['中国银行H'], GetMarketPrice('中国银行H')) /
                              (0.5 / GetPE('南方A50', GetMarketPrice('南方A50'))),
                             0.7, 0.95, 0.05)

def SellBOCH():
  code = NAME_TO_CODE['中国银行H']
  if GetAHDiscount(code) < -0.98:
    mp = GetMarketPriceInBase(code)
    return 'Sell 中国银行H(%s) %d units @%.3f due to AHR = %.3f'%(
      code,
      int((holding_percent[code] - 0.2) * NET_ASSET / mp),
      mp,
      GetAHDiscount(code))
  return ''

def BOCandCB():
  premium = GetPB0('中行转债', GetMarketPrice('中行转债'))
  if premium > 1.05:
    return '中行转债(%s) @%.3f ==> 中国银行(%s) @%.3f due to CB premium = %.3f' % (
      NAME_TO_CODE['中行转债'], GetMarketPrice('中行转债'),
      NAME_TO_CODE['中国银行'], GetMarketPrice('中国银行'),
      premium
    )
  if premium < 1.01:
    return '中国银行(%s) @%.3f ==> 中行转债(%s) @%.3f due to premium = %.3f' % (
      NAME_TO_CODE['中国银行'], GetMarketPrice('中国银行'),
      NAME_TO_CODE['中行转债'], GetMarketPrice('中行转债'), premium
    )
  return ''

def BuyJixieGongcheng():
  return GenericDynamicStrategy(
    '中国机械工程',
    'P/E',
    [12, 9],
    [0.5, 0.1],
    15,
    buy_condition = lambda code: GetMarketPriceChange(code) < -2);

def BuyFbPut():
  if GetMarketPrice('FB') > 80.0 and GetMarketPriceChange('FB') > 0.01:
    return 'Buy Facebook put @80.'
  return ''

def YahooAndAlibaba():
  kUnit = 100
  ratio = 1.0 * CROSS_SHARE['Yahoo-Alibaba'] / SHARES['Yahoo'] * 0.72
  mp = GetMarketPrice('Yahoo') - ratio * GetMarketPrice('Alibaba')
  YahooJapanPerShare = 2.3 * 10**12 * EX_RATE['YEN-USD'] * 0.35 * 0.72 / SHARES['Yahoo']
  net_money = 7209 * 10**6 / SHARES['Yahoo']
  PB = mp / (YahooJapanPerShare + net_money)
  imbalance = g_holding_shares['Yahoo'] * ratio + g_holding_shares['Alibaba']
  if imbalance / ratio < -50:
    print 'Buy Yahoo %d unit @%.2f for portfolio parity.' % (-imbalance / ratio, GetMarketPrice('Yahoo'))
  elif imbalance > 10:
    print 'Sell Alibaba %d units @%.2f for portfolio parity.' % (imbalance, GetMarketPrice('Alibaba'))

  best_tax_rate = 0.2
  upper_PB = GetMarketPrice('Yahoo') *SHARES['Yahoo'] / (
               GetMarketPrice('Yahoo') / GetPB0('Yahoo', GetMarketPrice('Yahoo')) * SHARES['Yahoo'] +
               CROSS_SHARE['Yahoo-Alibaba'] * GetMarketPrice('Alibaba') * (0.38 - best_tax_rate))
  if holding_percent['Yahoo'] + holding_percent['Alibaba'] < 0.15 and (PB < 1.8 and upper_PB < 0.95):
    return 'Long Yahoo @%.2f %d units short Alibaba @%.2f %.0f units with PB = %.2f upper_PB = %.2f' % (
        GetMarketPrice('Yahoo'), kUnit,
        GetMarketPrice('Alibaba'), kUnit * ratio,
        PB, upper_PB
        )
  if upper_PB > 1.0 and PB > 1.9:
    return 'Sell Yahoo @%.2f %d units Buy Alibaba @%.2f %.0f units with upper PB = %.2f' % (
        GetMarketPrice('Yahoo'), g_holding_shares['Yahoo'],
        GetMarketPrice('Alibaba'), g_holding_shares['Alibaba'],
        upper_PB)

  return 'PB ( Yahoo - %.2f * Alibaba) = %.2f Yahoo upper PB = %.2f' % (ratio, PB, upper_PB)

STRATEGY_FUNCS = {
  YahooAndAlibaba: 'Yahoo and Alibaba comp',
  BuyApple: 'Buy Apple',
  BuyBig4BanksH: 'Buy 四大行H股 ',
  BuyDeNA:  'Buy :DeNA',
  BuyCMBH:  'Buy CMBH',
  BuyA50: 'Buy A50',
  BuyBOCH: 'Buy BOCH',
  BuyCCB: 'Buy CCB',
  BuyBOC: 'Buy BOC',
  BuyWeibo: 'Buy Weibo',
  KeepDaLanChou: 'Buy 大蓝筹',
  BOCHandBOC: 'BOCH and BOC',
  CMBHandCMB: 'CMBH and CMB',
  BuyYandex: 'Buy Yandex',
  #BuyYahoo: 'Buy Yahoo',
  ReduceOverflow: 'Reduce overflow',
  #CMBandBOC: 'CMB<->BOC',
  BOCHandA50: 'A50<->BOCH',
  SellBOCH: 'Sell BOCH',
  BOCandCB: 'BOC<->CB',
  BuyJixieGongcheng: '中国机械工程',
  BuyFbPut: 'Buy Facebook put',
}

#--------------End of strategy functions-----

def InitAll():
  for key in AH_PAIR.keys():
    AH_PAIR[AH_PAIR[key]] = key

  for dt in [WATCH_LIST_BANK, WATCH_LIST_BANK_1,  WATCH_LIST_INSURANCE, WATCH_LIST_MOBILE_GAMES,
             WATCH_LIST_INTERNET, WATCH_LIST_ETF, WATCH_LIST_CB, WATCH_LIST_OTHER]:
    for code in dt.keys():
      CODE_TO_NAME[code] = dt[code]
      if code in AH_PAIR:
        CODE_TO_NAME[AH_PAIR[code]] = dt[code] + 'H'.encode('utf-8')

  for code in CODE_TO_NAME.keys():
    NAME_TO_CODE[CODE_TO_NAME[code]] = code

  for dt in [WATCH_LIST_BANK, WATCH_LIST_BANK_1, WATCH_LIST_INSURANCE]:
    keys = dt.keys()
    for code in keys:
      if code in AH_PAIR:
        dt[AH_PAIR[code]] = dt[code] + 'H'.encode('utf-8')

  for dt in [STOCK_CURRENCY, SHARES, CAP, CB, EPS0, EPS, DVPS, DVPS0, SPS,
             BVPS0, BVPS, ETF_BOOK_VALUE_FUNC, FORGOTTEN, PERCENT_UPPER]:
    keys = dt.keys()
    for key in keys:
      dt[NAME_TO_CODE[key]] = dt[key]

  for dt in [SHARES, PERCENT_UPPER]:
    for key in dt.keys():
      if key in AH_PAIR:
        dt[AH_PAIR[key]] = dt[key]

  for dt in [CAP, EPS0, EPS, DVPS, DVPS0, SPS, BVPS0, BVPS]:
    for key in dt.keys():
      if key in AH_PAIR:
        dt[AH_PAIR[key]] = dt[key] * EX_RATE[GetCurrency(key) + '-' + GetCurrency(AH_PAIR[key])]

  for dt in [CB]:
    for key in dt.keys():
      if key in AH_PAIR:
        dt[AH_PAIR[key]] = map(lambda x: x * EX_RATE[GetCurrency(key) + '-' + GetCurrency(AH_PAIR[key])], dt[key])

  if 'all' in set(sys.argv):
    sys.argv += ['stock', 'hold', 'etf', 'Price']
  for name in EPS:
    if name in BVPS0 and (name in WATCH_LIST_BANK or name in WATCH_LIST_BANK_1):
      roe = 1.0 * EPS[name] / BVPS0[name]
      msg = '%s ROE=%.1f%%'%(name, roe * 100)
      if roe < 0.1 or roe > 0.28:
        print 'Bad estimation: %s'%(msg)
      else:
        sys.stderr.write('Estimation for %s\n'%(msg))

def CalOneStock(NO_RISK_RATE, records, code, name):
  capital_cost = 0.0
  net_profit = 0.0
  investment = 0.0
  prev_date = date(2000, 1, 1)
  holding_cost = 0.0
  holding_shares = 0
  records.sort()
  day_trade_profit = 0
  day_trade_net_shares = 0
  sum_day_trade_profit = 0
  day_trade_time = -1
  sum_fee = 0
  vid = 'visualization_%s'%(code)
  data = ''
  prices = []
  for cell in records:
    currency = cell[7]
    ex_rate = EX_RATE[currency + '-' + CURRENCY]
    trans_date = cell[0]
    buy_shares = cell[5]
    origin_price = cell[4]
    price = origin_price * ex_rate
    fee = cell[6] * ex_rate
    sum_fee += fee
    value = -price * buy_shares - fee - cell[8] * ex_rate
    if -1 == cell[1].find('股息'):
      data += '[new Date(%d, %d, %d), %.3f, \'%s%d\', \'%.0fK %s\'],\n'%(
          trans_date.year, trans_date.month - 1, trans_date.day,
          origin_price, '+' if buy_shares > 0 else '',
          buy_shares, (value + 500) / 1000, CURRENCY)
      prices.append(origin_price)
    if investment > 0.0:
      diff_days = (trans_date - prev_date).days
      capital_cost  += investment * NO_RISK_RATE / 365 * diff_days
    if prev_date == trans_date:
      day_trade_net_shares += buy_shares
      day_trade_profit += value
    else:
      if day_trade_net_shares == 0:
        sum_day_trade_profit += day_trade_profit
        day_trade_time += 1
      day_trade_profit = value
      day_trade_net_shares = buy_shares

    investment -= value
    #assert investment >= 0.0
    net_profit += value
    prev_date = trans_date
    if buy_shares > 0 and holding_shares > 0:
      assert value <= 0.0
      holding_cost = (holding_cost * holding_shares - value) / (holding_shares + buy_shares)
    holding_shares += buy_shares
  if investment > 0.0:
    capital_cost  += investment * NO_RISK_RATE / 365 * (date.today() - prev_date).days
  if day_trade_net_shares == 0:
    sum_day_trade_profit += day_trade_profit
    day_trade_time += 1
  return (net_profit, capital_cost, holding_shares, sum_day_trade_profit, day_trade_time, sum_fee,
          currency,
          FUNCTION_TEMPLATE%(
            name,
            data,
            vid,
            min(prices),
            max(prices),
            currency),
          DIV_TEMPLATE%(vid))

def ReadRecords(input):
  raw_all_records = []
  for line in input:
    if 0 != line.find('20'):
      continue
    cells = line.strip().split(',')
    cells[0] = date(int(cells[0][0:4]), int(cells[0][4:6]), int(cells[0][6:8]))
    raw_all_records.append(cells)
  raw_all_records.sort(key = lambda record: record[0]) 

  all_records = defaultdict(list)
  sell_fee = 18.1 / 10000
  buy_fee = 8.1 / 10000
  for cells in raw_all_records:
    cells.append(0.0)
    price, buy_shares = float(cells[4]), int(cells[5])
    fee = float(cells[6]) if cells[6] != '' else (
      buy_fee * abs(buy_shares * price) if buy_shares > 0 else sell_fee * abs(buy_shares * price))
    cells[4], cells[5], cells[6] = price, buy_shares, fee
    last = all_records[cells[2]][-1] if len(all_records[cells[2]]) > 0 else []
    if (len(last) > 0 and
        (cells[0] - last[0]).days < 7
        and cells[1].find('股息') == -1
        and last[1].find('股息') == -1):
      if buy_shares + last[5] != 0:
        last[4] = (last[8] + buy_shares * price + last[5] * last[4]) / (buy_shares + last[5])
        last[8] = 0
      else:
        last[8] += buy_shares * price + last[5] * last[4]
      last[5] += buy_shares
      last[6] += fee
    else:
      all_records[cells[2]].append(cells)
  return all_records

def PrintHoldingSecurities(all_records):
  global NET_ASSET
  table_header = [
                  'Percent',
                  'Percent1',
                  'MV(K)',
                  'HS',
                  'CC',
                  '#TxN',
                  'TNF',
                  'DTP',
                  '#DT',
                  'MP',
                  'Chg',
                  'P/E0',
                  'P/E',
                  'P/S',
                  'P/B0',
                  'P/B',
                  'DR0',
                  'DR',
                  'AHD',
                  'DvDays',
                  'Stock name']
  silent_column = [
    'MV',
    'MP',
    '#TxN',
    'TNF',
    'DTP',
    '#DT',
    'CC',
    'NCF',
    'HS',
  ]
  for col in ['Price']:
    if col not in set(sys.argv):
      silent_column.append(col)

  stat_records_map = []
  
  summation = {}
  summation['Stock name'] = 'Summary'
  
  function_html = ''
  div_html = ''
  
  for key in all_records.keys():
    if key in FORGOTTEN:
      # in CURRENCY
      name = all_records[key][0][3]
      (net_profit, capital_cost, remain_stock, dtp, dt, txn_fee, currency, function,division) = CalOneStock(
          NO_RISK_RATE, all_records[key], key, name)
      net_profit *= EX_RATE[CURRENCY + '-' + currency]
      cells = all_records[key][-1]
      cells[2:7] = [currency, '', 1, int(net_profit), 0]
      all_records[currency].append(cells)
      sys.stderr.write('Convert %s to cash %d in %s\n'%(CODE_TO_NAME[key], net_profit, currency))
      assert net_profit >= 0
      del all_records[key]
      function_html += function
      div_html += division
       
  for key in all_records.keys():
    sys.stderr.write('Processing [' + key + ']\n')
    name = all_records[key][0][3]
    # All in CURRENCY
    (net_profit, capital_cost, remain_stock, dtp, dt, txn_fee, currency, function, division) = CalOneStock(
      NO_RISK_RATE, all_records[key], key, name)
    if key in total_investment:
      total_capital[currency] += -net_profit
      total_capital_cost[currency] += capital_cost
      continue
    function_html += function
    div_html += division
    investment = -net_profit
    total_investment[currency] += investment
    total_transaction_fee[currency] += txn_fee
    ex_rate = EX_RATE[currency + '-' + CURRENCY]
    mp, chg, mp_pair_rmb, mv, = 0.0001, 0, 1, 0
    if remain_stock != 0:
      mp = GetMarketPrice(key)
      chg = GetMarketPriceChange(key)
      mp_pair_rmb = mp * ex_rate
      mv = mp * remain_stock * ex_rate
      if key in AH_PAIR:
        mp_pair_rmb = GetMarketPriceInBase(AH_PAIR[key])
    total_market_value[currency] += mv
    sys.stderr.write('%s profit %.0f %s from %s\n'%(
      'Realized' if remain_stock == 0 else 'Unrealized',
      net_profit + mv,
      CURRENCY,
      name))
    g_holding_shares[key] = remain_stock
    if key in CODE_TO_NAME:
      g_holding_shares[CODE_TO_NAME[key]] = remain_stock
    record = {
        'Code': key,
        'HS': remain_stock,
        'MV': myround(mv, 0),
        'MV(K)': myround(mv / 1000.0, 0),
        'currency': currency,
        'Price': mp,
        'Chg': round(chg, 2),
        'CC': myround(capital_cost, 0),
        '#TxN': len(all_records[key]),
        'TNF': myround(txn_fee, 0),
        'DTP': myround(dtp, 0),
        '#DT': dt,
        'Pos': remain_stock,
        'P/E0': myround(GetPE0(key, mp), 2),
        'P/E': myround(GetPE(key, mp), 2),
        'P/S': myround(GetPS(key, mp), 2),
        'P/B0': myround(GetPB0(key, mp), 3),
        'P/B': myround(GetPB(key, mp), 2),
        'DR0':  myround(GetDR0(key, mp) * 100 , 2),
        'DR':  myround(GetDR(key, mp) * 100 , 2),
        'AHD': str(myround(100.0 * (mp_pair_rmb - mp * ex_rate ) / mp / ex_rate, 1)) + '%',
        'DvDays': ((DIVIDEND_DATE[name] if name in DIVIDEND_DATE else date(2016, 1, 1)) - date.today()).days,
        'Stock name': name + '(' + key + ')',
    }
    for col in ['MV', 'MV(K)', 'CC', '#TxN', 'TNF', 'DTP', '#DT']:
      summation[col] = summation.get(col, 0) + record[col]
    if remain_stock != 0:
      stat_records_map.append(record)
  
  for dt in [total_market_value, total_capital,
             total_investment, total_transaction_fee]:
    dt['USD'] += dt['HKD']
    dt['USD'] += dt['YEN']
  
  capital_header = ['Currency', 'Market Value', 'Free Cash', 'Net', 'Cash',
                    'Transaction Fee', 'Max Decline', 'IRR']
  capital_table_map = []
  # All are in CURRENCY
  cash_flow = defaultdict(list)
  for key in all_records.keys():
    for cell in all_records[key]:
      currency = cell[7]
      ex_rate = EX_RATE[currency + '-' + CURRENCY]
      trans_date = cell[0]
      fee = cell[6] * ex_rate
      buy_shares = cell[5]
      price = cell[4] * ex_rate
      value = -price * buy_shares - fee - cell[8] * ex_rate
      cash_flow[currency].append([trans_date, key, value]);
  
  cash_flow['USD'] += cash_flow['HKD']
  cash_flow['USD'] += cash_flow['YEN']
  
  for dt in [total_market_value, total_capital,
             total_investment, total_transaction_fee]:
    dt['ALL'] = dt['USD'] + dt['RMB']
    dt['RMB'] *= EX_RATE[CURRENCY + '-RMB']
    dt['USD'] *= EX_RATE[CURRENCY + '-USD']

  cash_flow['ALL'] = copy.deepcopy(cash_flow['USD'] + cash_flow['RMB'])
  for record in cash_flow['RMB']:
    record[2] *= EX_RATE[CURRENCY + '-RMB']
  for record in cash_flow['USD']:
    record[2] *= EX_RATE[CURRENCY + '-USD']
  
  for currency in ['USD', 'RMB', 'ALL']:
    net_asset[currency] = total_market_value[currency] + total_capital[currency] - total_investment[currency]
    capital_table_map.append(
        {
        'Currency': currency,
        'Market Value': str(myround(total_market_value[currency] / 1000, 0)) + 'K',
        'Cash': str(myround(total_capital[currency] / 1000, 0)) + 'K',
        'Investment': str(myround(total_investment[currency] / 1000, 0)) + 'K',
        'Free Cash': str(myround((total_capital[currency] - total_investment[currency]) / 1000, 0)) + 'K',
        'Transaction Fee': str(myround(total_transaction_fee[currency] / 100.0, 0)) + 'h(' +
          str(myround(100.0 * total_transaction_fee[currency] / net_asset[currency], 2)) + '%)',
        'Max Decline': str(myround((total_market_value[currency] + 2 * total_capital[currency] - 2 * total_investment[currency]) * 100.0 / max(1, total_market_value[currency]), 0)) + '%',
        'IRR': str(myround(GetIRR(total_market_value[currency], cash_flow[currency]) * 100, 2)) + '%',
        'Net': str(myround((total_market_value[currency] + total_capital[currency] - total_investment[currency]) / 1000, 0)) + 'K',
        }
    )
  NET_ASSET = total_market_value['ALL'] + total_capital['ALL'] - total_investment['ALL']
  
  PrintTableMap(capital_header, capital_table_map, set(), truncate_float = False)
  for col in ['Chg', 'DR', 'DR0', 'Percent']:
    summation[col] = 0.0
  for record in stat_records_map:
    holding_percent[record['Code']] = 1.0 * record['MV'] / NET_ASSET
    summation['Percent'] += holding_percent[record['Code']]
    record['Percent'] = str(myround(holding_percent[record['Code']] * 100, 1)) + '%'
    currency = 'RMB' if record['currency'] == 'RMB' else 'USD'
    record['Percent1'] = str(myround(100.0 * record['MV'] * EX_RATE[CURRENCY + '-' + currency] / net_asset[currency], 1)) + '%'
    for col in ['Chg', 'DR', 'DR0']:
      summation[col] += holding_percent[record['Code']] * record[col]
  for col in ['Chg', 'DR', 'DR0']:
    summation[col] = round(summation[col], 2)
  summation['Percent'] = str(round(summation['Percent'] * 100, 0)) + '%'
  if 'hold' in set(sys.argv):
    stat_records_map.append(summation)
    stat_records_map.sort(reverse = True, key = lambda record: record.get('MV', 0))
    PrintTableMap(table_header, stat_records_map, silent_column, truncate_float = False)
  if 'chart' in set(sys.argv):
    open('/tmp/charts.html', 'w').write(
      HTML_TEMPLATE%(function_html, div_html) 
    )

def PrintWatchedETF():
  table_header = [
                  'Change',
                  'Real Value',
                  'Discount',
                  'P/E',
                  'Stock name',
                 ]
  table_map = []
  for code in WATCH_LIST_ETF.keys():
    func = ETF_BOOK_VALUE_FUNC[code] if code in ETF_BOOK_VALUE_FUNC else lambda: GetXueqiuETFBookValue(code)
    price, change, real_value = GetMarketPrice(code), GetMarketPriceChange(code), func()
    table_map.append({
      'Change': str(round(change, 1)) + '%',
      'Real Value': real_value,
      'Discount': str(myround((real_value - price) * 100 / real_value, 0)) + '%',
      'P/E': GetPE(code, price),
      'Stock name': CODE_TO_NAME[code],
    })
  silent = []
  if 'Price' not in set(sys.argv):
    silent += ['Price']
  PrintTableMap(table_header, table_map, silent, truncate_float = False)

def PrintWatchedStocks(watch_list, table_header, sort_key, rev = False):
  table, silent = [], []
  if 'Price' not in set(sys.argv):
    silent += ['Price']
  for code in watch_list.keys():
    mp = GetMarketPrice(code)
    record = {
              'Stock name': watch_list[code] + ('(' + code + ')').encode('utf-8'),
    }
    for col in table_header:
      if col == 'Change':
        record[col] = str(GetMarketPriceChange(code)) + '%'
      elif col in FINANCIAL_FUNC:
        record[col] = round(FINANCIAL_FUNC[col](code, mp), 3)
    table.append(record)
  table.sort(reverse = rev, key = lambda record: record.get(sort_key, 0))
  PrintTableMap(table_header, table, silent, truncate_float = False)

def PrintWatchedBank():
  table_header = [
                  'Change',
                  'P/E0',
                  'P/E',
                  'P/B0',
                  'P/B',
                  'DR0',
                  'DR',
                  'AHD',
                  'Stock name'
                  ]
  PrintWatchedStocks(WATCH_LIST_BANK_1, table_header, 'P/B')
  PrintWatchedStocks(WATCH_LIST_BANK, table_header, 'P/B')

def PrintWatchedInsurance():
  table_header = [
                  'Change',
                  'P/E',
                  'P/B',
                  'P/S',
                  'DR',
                  'AHD',
                  'Stock name'
                  ]
  PrintWatchedStocks(WATCH_LIST_INSURANCE, table_header, 'P/S')

def PrintWatchedInternet():
  table_header = [
                  'Change',
                  'P/E',
                  'P/S',
                  'CAP',
                  'P/B0',
                  'DR0',
                  'Stock name'
                  ]
  PrintWatchedStocks(WATCH_LIST_INTERNET, table_header, 'CAP')

def RunStrategies():
  for strategy in STRATEGY_FUNCS.keys():
    sys.stderr.write("Running straregy: %s\n"%(STRATEGY_FUNCS[strategy]))
    suggestion = strategy()
    if suggestion != '':
      print '%s'%(suggestion)

try:
  InitAll()
  
  if 'etf' in set(sys.argv):
    PrintWatchedETF()
  
  #if 'stock' in set(sys.argv) or 'insurance' in set(sys.argv):
    #PrintWatchedInsurance()
  
  if 'stock' in set(sys.argv) or 'internet' in set(sys.argv):
    PrintWatchedInternet()
  
  if 'stock' in set(sys.argv) or 'bank' in set(sys.argv):
    PrintWatchedBank()
  
  PrintHoldingSecurities(ReadRecords(sys.stdin))
  RunStrategies()
except Exception as ins:
  print 'Run time error: ', ins
  traceback.print_exc(file=sys.stdout)
