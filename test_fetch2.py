# -*- coding: utf-8 -*-
import sys, os, requests, time, random
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://quote.eastmoney.com/',
    'Accept': 'application/json',
}

# Test kline with different approach
print("Testing kline v2...")
session = requests.Session()
session.headers.update(headers)

# Try with secid format
code = '000001'
market = '0'  # 深市
secid = f'{market}.{code}'

url = f'https://push2his.eastmoney.com/api/qt/stock/kline/get'
params = {
    'secid': secid,
    'fields1': 'f1,f2,f3,f4,f5,f6',
    'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
    'klt': '101',
    'fqt': '1',
    'end': '20500101',
    'lmt': '10'
}

try:
    resp = session.get(url, params=params, timeout=20)
    print(f"Status: {resp.status_code}")
    data = resp.json()
    if data.get('data') and data['data'].get('klines'):
        print(f"Success! Got {len(data['data']['klines'])} klines")
        for k in data['data']['klines'][:3]:
            print(f"  {k}")
    else:
        print(f"Response: {str(data)[:300]}")
except Exception as e:
    print(f"Error: {e}")

# Try with 6开头 (沪市)
print("\nTesting sh stock...")
secid2 = '1.600519'  # 贵州茅台
params2 = dict(params, secid=secid2)
try:
    resp2 = session.get(url, params=params2, timeout=20)
    data2 = resp2.json()
    if data2.get('data') and data2['data'].get('klines'):
        print(f"Success! Got {len(data2['data']['klines'])} klines for 600519")
    else:
        print(f"Response: {str(data2)[:300]}")
except Exception as e:
    print(f"Error: {e}")

# Try Sina as alternative
print("\nTesting Sina kline...")
try:
    url_sina = f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sz{code}&scale=240&ma=no&datalen=10'
    resp_sina = session.get(url_sina, timeout=15)
    print(f"Sina status: {resp_sina.status_code}")
    print(f"Sina response: {resp_sina.text[:300]}")
except Exception as e:
    print(f"Sina error: {e}")
