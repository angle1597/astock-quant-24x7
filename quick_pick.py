# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3, numpy as np, pandas as pd

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'
conn = sqlite3.connect(DB)
codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
quotes = pd.read_sql(
    '''SELECT code, name, price, change, amount 
       FROM realtime_quote 
       WHERE change > 0 
       AND code NOT LIKE '688%' 
       AND name NOT LIKE '%ST%' ''', conn)
conn.close()

print(f'Stocks in DB: {len(codes)}')

# Best params from previous run
hold, chg_min, chg_max, pmax, vol_min = 10, 4, 10, 18, 1.2

# Find tomorrow picks
picks = []
for _, r in quotes.iterrows():
    try:
        price = float(r['price']) if r['price'] and r['price'] != '-' else 0
        change = float(r['change']) if r['change'] and r['change'] != '-' else 0
        amount = float(r['amount'])/1e8 if r['amount'] and r['amount'] != '-' else 0
    except:
        continue
    
    if price <= 0 or change <= 0:
        continue
    
    score = 0
    factors = []
    
    if chg_min <= change <= chg_max:
        score += 50
        factors.append(f'chg={change:.1f}%')
    elif change >= 9:
        score += 45
        factors.append('NEAR_LIMIT')
    elif change >= 7:
        score += 30
        factors.append(f'strong+{change:.1f}%')
    
    if 3 <= price <= pmax:
        score += 30
        factors.append(f'price={price:.1f}')
    
    if amount >= 3:
        score += 20
        factors.append(f'amt={amount:.1f}B')
    
    if change >= 9.5:
        score += 30
        factors.append('LIMIT_UP')
    
    if 3 <= price <= 10:
        score += 15
    
    hot = ['energy', 'power', 'AI', 'chip', 'EV']
    for kw in hot:
        if kw in str(r['name']):
            score += 10
            break
    
    if score >= 55:
        picks.append({
            'code': r['code'], 
            'name': r['name'], 
            'price': price, 
            'change': change, 
            'amount': amount, 
            'score': score, 
            'factors': factors
        })

picks.sort(key=lambda x: x['score'], reverse=True)

print(f'\nTomorrow picks ({len(picks)} stocks):')
for i, p in enumerate(picks[:15], 1):
    fac = ', '.join(p['factors'][:3])
    print(f'{i}. {p["code"]} {p["name"]} @ {p["price"]:.2f} chg={p["change"]:+.1f}% amt={p["amount"]:.1f}B score={p["score"]} [{fac}]')
