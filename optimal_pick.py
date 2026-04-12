# -*- coding: utf-8 -*-
"""基于最优策略选股"""
import sqlite3
import pandas as pd
import numpy as np

DB_PATH = 'data/stocks.db'

def calc_macd(closes):
    if len(closes) < 30:
        return None
    ema12 = closes.ewm(span=12).mean()
    ema26 = closes.ewm(span=26).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9).mean()
    macd = (dif - dea) * 2
    return macd.iloc[-1]

def pick_stocks():
    conn = sqlite3.connect(DB_PATH)
    codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
    conn.close()
    
    candidates = []
    for code in codes:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
        conn.close()
        
        if df.empty or len(df) < 30:
            continue
        
        # 排除
        if code.startswith('688') or code.startswith('300') or code.startswith('8') or code.startswith('4'):
            continue
        
        row = df.iloc[-1]
        prev = df.iloc[-2]
        
        try:
            price = float(row['close'])
            prev_close = float(prev['close'])
            chg = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
        except:
            continue
        
        # 筛选条件
        if not (8 <= chg <= 15):
            continue
        if not (3 <= price <= 10):
            continue
        
        # MACD筛选
        macd = calc_macd(df['close'])
        if macd is None or macd <= 0:
            continue
        
        # 评分
        score = 0
        if 8 <= chg <= 12: score += 30
        if 3 <= price <= 8: score += 25
        if macd > 0.1: score += 20
        if price <= 5: score += 15
        
        candidates.append({
            'code': code,
            'price': price,
            'chg': chg,
            'macd': macd,
            'score': score
        })
    
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates[:10]

print('='*60)
print('Optimal Strategy Picks')
print('='*60)
picks = pick_stocks()
print('Candidates:', len(picks))
for i, p in enumerate(picks[:5], 1):
    print(str(i) + '. ' + p['code'])
    print('   Price:' + str(round(p['price'], 2)) + ' Chg:' + str(round(p['chg'], 2)) + '% MACD:' + str(round(p['macd'], 4)) + ' Score:' + str(p['score']))
