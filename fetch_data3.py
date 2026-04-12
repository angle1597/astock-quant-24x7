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

# 年度报告主要财务数据
print("=== 年度主要财务数据 ===")
url1 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_LICO_FN_CPD&columns=REPORT_DATE,TOTAL_OPERATE_INCOME,OPERATE_PROFIT,PARENT_NETPROFIT,NON_RECURRING_GAIN_LOSS,EPS,JLROA,JLROE,GROSS_PROFIT_RTN,TOTAL_ASSETS,TOTAL_LIABILITIES&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=8&sortTypes=-1&sortColumns=REPORT_DATE&source=DataCenter&client=PC'
try:
    d = json.loads(fetch(url1))
    print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
except Exception as e:
    print(f"Error: {e}")

# 季度报告
print("\n=== 季度主要财务数据 ===")
url2 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_FINA_MAIN_INDICATOR&columns=REPORT_DATE,TOTAL_OPERATE_INCOME,PARENT_NETPROFIT,EPS,ROE,GROSS_MARGIN,DEBT_ASSET_RATIO&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=12&sortTypes=-1&sortColumns=REPORT_DATE&source=DataCenter&client=PC'
try:
    d = json.loads(fetch(url2))
    print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
except Exception as e:
    print(f"Error: {e}")

# 应收账款/存货
print("\n=== 资产负债表摘要 ===")
url3 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_FINA_INDICATORS&columns=REPORT_DATE,ACCOUNTS_RECEIVABLE,INVENTORY,TOTAL_CURRENT_ASSETS,TOTAL_CURRENT_LIABILITIES,OPERATE_CASH_FLOW,INVEST_CASH_FLOW,FINANCE_CASH_FLOW&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=8&sortTypes=-1&sortColumns=REPORT_DATE&source=DataCenter&client=PC'
try:
    d = json.loads(fetch(url3))
    print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
except Exception as e:
    print(f"Error: {e}")

# 股权质押
print("\n=== 股权质押 ===")
url4 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_F10_SHARE_PLEDGE&columns=REPORT_DATE,PLEDGE_HOLD_NUM,PLEDGE_RATIO,HOLDER_NAME,NEW_PLEDGE_NUM,RELEASED_NUM,STATUS&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=20&sortTypes=-1&sortColumns=REPORT_DATE&source=DataCenter&client=PC'
try:
    d = json.loads(fetch(url4))
    print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
except Exception as e:
    print(f"Error: {e}")

# 解禁
print("\n=== 限售股解禁 ===")
url5 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_STOCK_BS_LIST&columns=IPO_DATE,UNLOCK_DATE,FREE_SHARES,FREE_RATIO,LISTED_SHARES,TYPE,REASON&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=20&sortTypes=1&sortColumns=UNLOCK_DATE&source=DataCenter&client=PC'
try:
    d = json.loads(fetch(url5))
    print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
except Exception as e:
    print(f"Error: {e}")

# 商誉
print("\n=== 商誉情况 ===")
url6 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_FINA_GOODWILL&columns=REPORT_DATE,GOODWILL,GOODWILL_RATIO,IMPAIRMENT&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=10&sortTypes=-1&sortColumns=REPORT_DATE&source=DataCenter&client=PC'
try:
    d = json.loads(fetch(url6))
    print(json.dumps(d, ensure_ascii=False, indent=2)[:5000])
except Exception as e:
    print(f"Error: {e}")
