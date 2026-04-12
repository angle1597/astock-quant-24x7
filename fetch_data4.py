# -*- coding: utf-8 -*-
import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def fetch(url, referer='https://quote.eastmoney.com/'):
    req = urllib.request.Request(url, headers={
        'Referer': referer,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    r = urllib.request.urlopen(req, timeout=15)
    return r.read().decode('utf-8')

# East Money F10 - 基本指标
print("=== EastMoney F10 基本指标 ===")
url1 = 'https://emappdata.eastmoney.com/stockPage/finance/zczb?appId=appId01&cCode=002329&type=season&time=999999999'
try:
    d = json.loads(fetch(url1, 'https://emweb.securities.eastmoney.com/'))
    print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
except Exception as e:
    print(f"Error: {e}")

# 主要财务指标 - 正确的API
print("\n=== 主要财务指标 ===")
url2 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_FINA_MAININDEX&columns=REPORT_DATE,TOTAL_OPERATE_INCOME,PARENT_NETPROFIT,EPS,ROE,GROSS_PROFIT_RTN,DEBT_ASSET_RATIO&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=10&sortTypes=-1&sortColumns=REPORT_DATE&source=DataCenter&client=PC'
try:
    d = json.loads(fetch(url2))
    print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
except Exception as e:
    print(f"Error: {e}")

# 利润表
print("\n=== 利润表 ===")
url3 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_FINA_PROFITSTATEMENT&columns=REPORT_DATE,TOTAL_OPERATE_INCOME,OPERATE_PROFIT,PARENT_NETPROFIT,NON_OPERATE_INCOME,EPS&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=10&sortTypes=-1&sortColumns=REPORT_DATE&source=DataCenter&client=PC'
try:
    d = json.loads(fetch(url3))
    print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
except Exception as e:
    print(f"Error: {e}")

# 资产负债表
print("\n=== 资产负债表 ===")
url4 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_FINA_BALANCE&columns=REPORT_DATE,TOTAL_ASSETS,TOTAL_LIABILITIES,ACCOUNTS_RECEIVABLE,INVENTORY,GOODWILL,WORK_CAPITAL&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=10&sortTypes=-1&sortColumns=REPORT_DATE&source=DataCenter&client=PC'
try:
    d = json.loads(fetch(url4))
    print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
except Exception as e:
    print(f"Error: {e}")

# 现金流
print("\n=== 现金流量表 ===")
url5 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_FINA_CASHFLOW&columns=REPORT_DATE,OPERATE_CASH_FLOW,INVEST_CASH_FLOW,FINANCE_CASH_FLOW&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=10&sortTypes=-1&sortColumns=REPORT_DATE&source=DataCenter&client=PC'
try:
    d = json.loads(fetch(url5))
    print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
except Exception as e:
    print(f"Error: {e}")

# 股东户数
print("\n=== 股东户数 ===")
url6 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_SHAREHOLDER_NUM&columns=END_DATE,HOLDER_NUM&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=20&sortTypes=-1&sortColumns=END_DATE&source=DataCenter&client=PC'
try:
    d = json.loads(fetch(url6))
    print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
except Exception as e:
    print(f"Error: {e}")
