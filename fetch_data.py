# -*- coding: utf-8 -*-
import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def fetch(url):
    req = urllib.request.Request(url, headers={'Referer': 'https://quote.eastmoney.com/', 'User-Agent': 'Mozilla/5.0'})
    r = urllib.request.urlopen(req, timeout=15)
    return r.read().decode('utf-8')

# 1. 实时行情
print("=== 实时行情 ===")
url = 'https://push2.eastmoney.com/api/qt/stock/get?ut=fa5fd1943c7b386f172d6893dbfba10b&fltt=2&invt=2&secid=0.002329&fields=f43,f57,f58,f169,f170,f171,f47,f48,f60,f46,f44,f45,f168'
data = fetch(url)
print(data[:2000])

# 2. 股东人数变化
print("\n=== 股东人数变化 ===")
url2 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_F10_EH_GDJZXX&columns=REPORT_DATE,Holder_Num,SH_HOLDER_NUM,SH_HOLDER_RATIO,A_SH_HOLDER_NUM,A_SH_HOLDER_RATIO&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=20&sortTypes=-1&sortColumns=REPORT_DATE&source=DataCenter&client=PC'
data2 = fetch(url2)
print(data2[:3000])

# 3. 前十大流通股东
print("\n=== 前十大流通股东 ===")
url3 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_F10_EH_HOLDERSDETAILS&columns=SECURITY_CODE,HOLDER_NAME,HOLDER_TYPE,TOTAL_HOLD_NUM,TOTAL_HOLD_RATIO,CHANGE_NUM,CHANGE_REASON,TRADE_DATE&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=20&sortTypes=-1&sortColumns=TRADE_DATE&source=DataCenter&client=PC'
data3 = fetch(url3)
print(data3[:3000])

# 4. 主要财务指标
print("\n=== 主要财务指标 ===")
url4 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_F10_FN_ZDZX&columns=REPORT_DATE,TOTAL_OPERATE_INCOME,PARENT_NETPROFIT,EPS,BPS,ROE,GPM,RoeTTM&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=8&sortTypes=-1&sortColumns=REPORT_DATE&source=DataCenter&client=PC'
data4 = fetch(url4)
print(data4[:3000])
