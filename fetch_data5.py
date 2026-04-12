# -*- coding: utf-8 -*-
import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def fetch(url, referer='https://quote.eastmoney.com/'):
    req = urllib.request.Request(url, headers={
        'Referer': referer,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    })
    r = urllib.request.urlopen(req, timeout=15)
    return r.read().decode('utf-8')

# 尝试正确的东方财富API格式
print("=== 财务摘要 ===")
url1 = 'https://datacenter.eastmoney.com/api/data/v1/get?reportName=RPT_FINA_MAININDEX&columns=REPORT_DATE,TOTAL_OPERATE_INCOME,PARENT_NETPROFIT,EPS,ROE,GROSS_PROFIT_RTN&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=8&sortTypes=-1&sortColumns=REPORT_DATE'
try:
    d = json.loads(fetch(url1))
    print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
except Exception as e:
    print(f"Error: {e}")

# 尝试年度报告格式
print("\n=== 年度报告 ===")
url2 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_FINA_REPORT&columns=REPORT_DATE,TOTAL_OPERATE_INCOME,PARENT_NETPROFIT,EPS&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=8&sortTypes=-1&sortColumns=REPORT_DATE'
try:
    d = json.loads(fetch(url2))
    print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
except Exception as e:
    print(f"Error: {e}")

# 用东方财富F10的API
print("\n=== F10财务数据 ===")
url3 = 'https://emweb.securities.eastmoney.com/PC_HSF10/FinanceAnalysis/AnalysisMain?code=SH002329'
try:
    d = json.loads(fetch(url3, 'https://emweb.securities.eastmoney.com/PC_HSF10/FinanceAnalysis/AnalysisMain?code=SH002329'))
    print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
except Exception as e:
    print(f"Error: {e}")

# 另一个F10接口
print("\n=== F10资产负债表 ===")
url4 = 'https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/ZYZBAjaxNew?type=0&code=SH002329'
try:
    d = json.loads(fetch(url4, 'https://emweb.securities.eastmoney.com/'))
    print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
except Exception as e:
    print(f"Error: {e}")

# 公告 - 业绩预告
print("\n=== 公告列表 ===")
url5 = 'https://np-anotice-stock.eastmoney.com/api/security/ann?cb=&sr=-1&page_size=50&page_index=1&ann_type=SHA%2CSZA&client_source=web&f_node=0&s_node=0&stock_list=002329'
try:
    d = json.loads(fetch(url5, 'https://data.eastmoney.com/'))
    print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
except Exception as e:
    print(f"Error: {e}")
