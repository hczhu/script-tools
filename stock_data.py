#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import date
from datetime import time

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

EX_RATE = {
  'USD-USD': 1.0,
  'RMB-USD': 0.1605,
  'HKD-USD': 0.129,
  'YEN-USD': 0.009782,
}
def InitExRate():
  currencies = [pr.split('-')[0] for pr in EX_RATE.keys()]
  base = EX_RATE.keys()[0].split('-')[1];
  for a in currencies:
    for b in currencies:
      EX_RATE[a + '-' + b] = EX_RATE[a + '-' + base] / EX_RATE[b + '-' + base]
  for pr in EX_RATE.keys():
    currencies = pr.split('-')
    assert(len(currencies) == 2)
    EX_RATE[currencies[1] + '-' + currencies[0]] = 1.0 / EX_RATE[pr]

InitExRate()

SHARES = {
  # 港股 ＋ A股
  '招商银行': 4590901172 + 20628944429,

  # 港股 ＋ A股
  '中国银行': 83622276395  + 195742329935,

  '兴业银行': 19052336751,

  '民生银行': 27106044823 + 6993579408,

  '建设银行': 240417319880 + 9593657606,

  'Weibo': 2 * 10**8,
  # subtract treasury stock.
  ':DeNA': 150810033 - 21283601,
  'Yahoo': 1015 * 10**6,

  '浦发银行': 18653471415,
  '中国机械工程': 4125700000,
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
  'Yandex': lambda: GetMarketCap('Baidu') / GetMarketCap('Yandex') / 4 * GetMarketPrice('Yandex') * (38.0 / 50.0),
  # 雅虎日本(24B)35％的股权和alibaba 24%的股权，阿里按180B估值。
  # 卖出股权税率38%
  # 净现金3B
  # 回购价格 34.94
  'Yahoo': lambda: ((24 * 0.35 + 200 * 0.24) * ( 1 - 0.38) + 3) * 10**9 / SHARES['Yahoo'],
  # 按照阿里收购UC出资的股票部分和对UC的估值计算。
  'Alibaba': 72,
}

BVPS0 = {
  # 最近一次报告期的净资产
  # 招商银行, 2014年 Q1
  '招商银行': 10**6 * 285936.0 / SHARES['招商银行'],
  
  # 2014 H1
  '中国银行': 10**6 * 965733.0 / SHARES['中国银行'],

  # 2013年年报
  '兴业银行': 199769.0 * 10**6 / SHARES['兴业银行'],

  # 2013年年报
  '民生银行': 222199.0 * 10**6 / SHARES['民生银行'],

  '建设银行': 1139141.0 * 10**6 / SHARES['建设银行'],

  'Weibo': CAP['Weibo'],

  'Yandex': CAP['Yandex'],

  'Yahoo': CAP['Yahoo'],

  # 净现金
  ':DeNA': 1.0 * (110418 - 52858) * 10**6 / SHARES[':DeNA'],

  '信诚300A': 1.043, #GetHexinFundBookValue('http://jingzhi.funds.hexun.com/150051.shtml')

  '南方A50': ETF_BOOK_VALUE_FUNC['南方A50'],
  '浦发银行': 218312.0 * 10**6 / SHARES['浦发银行'],
  '中国机械工程': EX_RATE['RMB-HKD'] * 12032874000.0 / SHARES['中国机械工程'],
  '中行转债': lambda: 100.0 * GetMarketPrice('中国银行') / CB['中国银行'][1],
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
  
  '南方A50': (3.63 - 1.0) / 100 * 8.4,
  '中国机械工程': 0.19 * EX_RATE['RMB-HKD'], # 2013年股息
}

# The portion of EPS used for dividend.
DVPS = {
  # 假定30%分红率，税率10%.
  '招商银行': EPS['招商银行'] * 0.3,

  # 过去四年年分红率 [0.35, 0.34, 0.36, 0.35]
  # 13年年报称以后不少于10%现金分红
  # 减去优先股股息,2014年后半年发行320亿，股息率8%
  '中国银行': (EPS['中国银行'] - 320 * 10**8 * 0.08 / 2 / SHARES['中国银行'])  * 0.35,
}

DIVIDEND_DATE = {
  '建设银行H': date(2014, 7, 2),
  '建设银行': date(2014, 7, 10),
  '招商银行H': date(2014, 7, 3),
  '招商银行': date(2014, 7, 11),
  '中国银行H': date(2014, 6, 19),
  '中国银行': date(2014, 6, 26),
}

WATCH_LIST_BANK = {
  '601988': '中国银行',
  '601939': '建设银行',
  '600036': '招商银行',
  '600000': '浦发银行',
  '601166': '兴业银行',
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
  'ALIBABA': 'Alibaba',
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

RZ_BASE = {
  '兴业银行': 6157420241,
  '招商银行': 3909913752,
  '中国银行': 322251548,
}

STOCK_CURRENCY = {
  ':DeNA': 'YEN',
}
