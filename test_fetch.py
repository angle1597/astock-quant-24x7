# -*- coding: utf-8 -*-
import sys, os, requests, time, random
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Test fetching stock list
url = 'https://push2.eastmoney.com/api/qt/clist/get'
params = {
    'pn': 1, 'pz': 50, 'po': 1, 'np': 1, 'fltt': 2, 'invt': 2,
    'fid': 'f3',
    'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
    'fields': 'f12,f14,f2,f3,f6,f20'
}
try:
    resp = requests.get(url, params=params, headers=headers, timeout=15)
    data = resp.json()
    if data.get('data') and data['data'].get('diff'):
        print(f"Got {len(data['data']['diff'])} stocks")
        for item in data['data']['diff'][:5]:
            print(f"  {item.get('f12')} {item.get('f14')} price={item.get('f2')} chg={item.get('f3')}")
    else:
        print(f"Unexpected response: {str(data)[:200]}")
except Exception as e:
    print(f"Error: {e}")

# Test kline
print("\nTesting kline...")
url2 = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
params2 = {
    'secid': '0.000001',
    'fields1': 'f1,f2,f3,f4,f5,f6',
    'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
    'klt': '101', 'fqt': 1, 'end': '20500101', 'lmt': '10'
}
try:
    resp2 = requests.get(url2, params2, headers=headers, timeout=15)
    data2 = resp2.json()
    if data2.get('data') and data2['data'].get('klines'):
        print(f"Got {len(data2['data']['klines'])} klines")
        for k in data2['data']['klines'][:3]:
            print(f"  {k}")
    else:
        print(f"Unexpected kline response: {str(data2)[:200]}")
except Exception as e:
    print(f"Kline error: {e}")
