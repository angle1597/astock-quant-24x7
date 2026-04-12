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

# 实时行情解析
print("=== 实时行情 ===")
url = 'https://push2.eastmoney.com/api/qt/stock/get?ut=fa5fd1943c7b386f172d6893dbfba10b&fltt=2&invt=2&secid=0.002329&fields=f43,f57,f58,f169,f170,f171,f47,f48,f60,f46,f44,f45,f168'
d = json.loads(fetch(url))
data = d['data']
print(f"股票名称: {data['f58']}")
print(f"当前价: {data['f43']}")
print(f"昨收: {data['f60']}")
print(f"今开: {data['f46']}")
print(f"最高: {data['f44']}")
print(f"最低: {data['f45']}")
print(f"成交量: {data['f47']}")
print(f"成交额: {data['f48']}")
print(f"市盈率TTM: {data['f170']}")
print(f"市净率: {data['f171']}")
print(f"总市值: {data['f169']}亿")

# 东方财富 股东户数
print("\n=== 股东户数变化 ===")
url2 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_F10_SHAREHOLDER_NUM&columns=REPORT_DATE,Holder_Num,SH_HOLDER_NUM,SH_HOLDER_RATIO,A_SH_HOLDER_NUM,A_SH_HOLDER_RATIO&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=20&sortTypes=-1&sortColumns=REPORT_DATE&source=DataCenter&client=PC'
try:
    d2 = json.loads(fetch(url2))
    print(json.dumps(d2, ensure_ascii=False, indent=2)[:3000])
except Exception as e:
    print(f"Error: {e}")

# 主要财务指标
print("\n=== 主要财务指标 ===")
url3 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_F10_MAIN_INDICATOR&columns=REPORT_DATE,TOTAL_OPERATE_INCOME,PARENT_NETPROFIT,EPS,BPS,ROE,GPM&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=8&sortTypes=-1&sortColumns=REPORT_DATE&source=DataCenter&client=PC'
try:
    d3 = json.loads(fetch(url3))
    print(json.dumps(d3, ensure_ascii=False, indent=2)[:3000])
except Exception as e:
    print(f"Error: {e}")

# 融资融券
print("\n=== 融资融券 ===")
url4 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_RZRQ_RZRQ_DET&columns=TRADE_DATE,RZMRE,RZCHE,RQYL,ZQJRGMRQ,HXSUML&filter=(SECURITY_CODE=%22002329%22)&pageNumber=1&pageSize=10&sortTypes=-1&sortColumns=TRADE_DATE&source=DataCenter&client=PC'
try:
    d4 = json.loads(fetch(url4))
    print(json.dumps(d4, ensure_ascii=False, indent=2)[:3000])
except Exception as e:
    print(f"Error: {e}")

# 龙虎榜
print("\n=== 龙虎榜 ===")
url5 = 'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_STOCK_LHB&columns=TRADE_DATE,CLOSE_PRICE,CHANGE_RATE,BILLBOARD_NET_BUY,BILLBOARD_BUY_AMOUNT,BILLBOARD_SELL_AMOUNT,EXPLANATION&filter=(STOCK_CODE=%22002329%22)&pageNumber=1&pageSize=10&sortTypes=-1&sortColumns=TRADE_DATE&source=DataCenter&client=PC'
try:
    d5 = json.loads(fetch(url5))
    print(json.dumps(d5, ensure_ascii=False, indent=2)[:3000])
except Exception as e:
    print(f"Error: {e}")

# 资金流向
print("\n=== 资金流向 ===")
url6 = 'https://push2.eastmoney.com/api/qt/stock/fflow/kline/get?lmt=0&klt=1&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65&ut=fa5fd1943c7b386f172d6893dbfba10b&secid=0.002329'
try:
    d6 = json.loads(fetch(url6))
    print(json.dumps(d6, ensure_ascii=False, indent=2)[:3000])
except Exception as e:
    print(f"Error: {e}")
