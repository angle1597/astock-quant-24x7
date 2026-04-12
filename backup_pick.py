# -*- coding: utf-8 -*-
"""备用数据源 - 新浪财经"""
import requests
import json
from datetime import datetime

def get_realtime():
    url = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeDataSimple?page=1&num=200&sort=change&asc=0&node=hs_a'
    
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        data = r.json()
        
        candidates = []
        for s in data:
            code = s.get('symbol', '').replace('sh', '').replace('sz', '')
            name = s.get('name', '')
            
            if code.startswith('688') or code.startswith('300') or code.startswith('8') or code.startswith('4'):
                continue
            if 'ST' in name or '*' in name:
                continue
            
            try:
                price = float(s.get('trade', 0))
                chg = float(s.get('changepercent', 0))
                amount = float(s.get('amount', 0)) / 1e8
            except:
                continue
            
            if 3 <= price <= 15 and 2 <= chg <= 10 and amount >= 1:
                score = 0
                if 3 <= chg <= 7: score += 35
                elif 7 < chg <= 10: score += 20
                if 3 <= price <= 10: score += 30
                elif 10 < price <= 15: score += 20
                if amount >= 5: score += 25
                elif amount >= 2: score += 15
                score += 10
                
                candidates.append({
                    'code': code, 'name': name, 'price': price,
                    'chg': chg, 'amount': amount, 'score': score
                })
        
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:10]
    except Exception as e:
        print('Error:', e)
        return []

print('='*60)
print('实时选股 (备用数据源)')
print('='*60)
candidates = get_realtime()
print('候选:', len(candidates))
for i, c in enumerate(candidates[:10], 1):
    print(str(i) + '. ' + c['code'] + ' ' + c['name'])
    print('   ' + str(c['price']) + '元 ' + str(round(c['chg'], 2)) + '% ' + str(round(c['amount'], 2)) + '亿 评分' + str(c['score']))

if candidates:
    best = candidates[0]
    print()
    print('='*60)
    print('最佳:', best['code'], best['name'])
    print('价格:', best['price'], '元')
    print('涨幅:', best['chg'], '%')
    print('评分:', best['score'])
