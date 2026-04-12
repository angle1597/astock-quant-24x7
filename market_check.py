# -*- coding: utf-8 -*-
import requests

print('='*60)
print('【国际市场动态】')
print('='*60)
print('')

h = {'User-Agent': 'Mozilla/5.0'}

# 1. 全球指数
url = 'https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&invt=2&fields=f12,f14,f2,f3&secids=100.DJIA,100.SPX,100.NDX,100.HSI'
try:
    r = requests.get(url, headers=h, timeout=10)
    d = r.json()
    print('全球指数:')
    for s in d['data']['diff']:
        chg = float(s['f3']) if s['f3'] != '-' else 0
        sign = '+' if chg >= 0 else ''
        print('  ' + s['f14'] + ': ' + sign + str(round(chg,2)) + '%')
except Exception as e:
    print('指数数据获取失败:', e)

print('')

# 2. A股板块热点
url2 = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=20&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:90+t:2&fields=f12,f14,f2,f3'
try:
    r2 = requests.get(url2, headers=h, timeout=10)
    d2 = r2.json()
    print('今日板块热点:')
    for s in d2['data']['diff'][:10]:
        chg = float(s['f3']) if s['f3'] != '-' else 0
        sign = '+' if chg >= 0 else ''
        print('  ' + s['f14'] + ': ' + sign + str(round(chg,2)) + '%')
except Exception as e:
    print('板块数据获取失败:', e)

print('')

# 3. 北向资金
url3 = 'https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.000001&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&end=20500101&lmt=1'
try:
    r3 = requests.get(url3, headers=h, timeout=10)
    d3 = r3.json()
    print('上证指数最新:')
    if d3 and 'data' in d3 and d3['data'] and 'klines' in d3['data']:
        kline = d3['data']['klines'][0].split(',')
        print('  收盘:', kline[2])
        print('  涨跌:', kline[5] + '%')
except Exception as e:
    print('指数数据获取失败:', e)
