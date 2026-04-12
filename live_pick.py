# -*- coding: utf-8 -*-
"""今日实时选股 - 午盘版"""
import requests
import json
from datetime import datetime

print('='*60)
print('今日实时选股')
print('北京时间: ' + datetime.utcnow().strftime('%Y-%m-%d ') + str(int(datetime.utcnow().strftime('%H')) + 8).zfill(2) + datetime.utcnow().strftime(':%M'))
print('='*60)

# 获取涨幅榜前300
url = 'https://push2.eastmoney.com/api/qt/clist/get?cb=jQuery&pn=1&pz=300&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f62,f128,f136,f115,f152'

r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}, timeout=15)
text = r.text
start = text.find('(') + 1
end = text.rfind(')')
data = json.loads(text[start:end])

stocks = data['data']['diff']
print(f'获取到 {len(stocks)} 只股票\n')

candidates = []
for s in stocks:
    code = str(s.get('f12', ''))
    name = str(s.get('f14', ''))

    # 排除创业板300、科创板688、北交所8开头
    if code.startswith('688') or code.startswith('300') or code.startswith('8') or code.startswith('4'):
        continue
    if 'ST' in name or '*' in name:
        continue

    try:
        price = float(s.get('f2', 0))
        chg = float(s.get('f3', 0))
        amount = float(s.get('f6', 0)) / 1e8
        turnover = float(s.get('f8', 0))  # 换手率
        pe = float(s.get('f9', 0))
    except:
        continue

    if price <= 0 or chg == '-' or amount == '-':
        continue

    # 筛选条件（基于实地调研策略）
    # 涨幅2-10%，价格3-15元，成交额1亿+
    if 2 <= chg <= 10 and 3 <= price <= 15 and amount >= 1:
        score = 0

        # 涨幅评分（蓄势区间）
        if 3 <= chg <= 7: score += 35
        elif 2 <= chg < 3: score += 25
        elif 7 < chg <= 10: score += 20

        # 价格评分（低价股）
        if 3 <= price <= 8: score += 30
        elif 8 < price <= 12: score += 20
        else: score += 10

        # 成交额评分（放量）
        if amount >= 5: score += 25
        elif amount >= 3: score += 18
        elif amount >= 1: score += 10

        # 换手率
        if 3 <= turnover <= 10: score += 10

        candidates.append({
            'code': code, 'name': name, 'price': price,
            'chg': chg, 'amount': amount, 'turnover': turnover,
            'score': score
        })

candidates.sort(key=lambda x: x['score'], reverse=True)

print(f'符合条件: {len(candidates)} 只\n')
print('TOP 10 候选股:')
print('-'*60)
for i, c in enumerate(candidates[:10], 1):
    print(f'{i:2}. {c["code"]} {c["name"]}')
    print(f'    价格:{c["price"]:.2f}元 涨幅:{c["chg"]:+.2f}% 成交:{c["amount"]:.2f}亿 换手:{c["turnover"]:.1f}% 评分:{c["score"]}')

if candidates:
    best = candidates[0]
    print('\n' + '='*60)
    print('【今日唯一推荐】')
    print('='*60)
    print(f'代码: {best["code"]}')
    print(f'名称: {best["name"]}')
    print(f'价格: {best["price"]:.2f}元')
    print(f'涨幅: {best["chg"]:+.2f}%')
    print(f'成交额: {best["amount"]:.2f}亿')
    print(f'评分: {best["score"]}分')
    print(f'策略: 持有5-7天，止损-5%，目标+20%')

with open('data/today_pick.json', 'w', encoding='utf-8') as f:
    json.dump(candidates[:10], f, ensure_ascii=False, indent=2)
