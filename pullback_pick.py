# -*- coding: utf-8 -*-
"""涨停回调策略选股"""
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

def find_pullback_candidates():
    """找出涨停后回调的股票"""
    conn = sqlite3.connect(DB_PATH)
    codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
    conn.close()
    
    candidates = []
    
    for code in codes:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
        conn.close()
        
        if df.empty or len(df) < 10:
            continue
        
        if code.startswith('688') or code.startswith('300') or code.startswith('8') or code.startswith('4'):
            continue
        
        # 检查近5天内是否有涨停
        recent = df.tail(5)
        
        limit_up_day = None
        for i in range(len(recent) - 1):
            row = recent.iloc[i]
            prev = recent.iloc[i-1] if i > 0 else row
            chg = (row['close'] - prev['close']) / prev['close'] * 100 if prev['close'] > 0 else 0
            if chg >= 9.5:
                limit_up_day = i
                break
        
        if limit_up_day is None:
            continue
        
        # 检查涨停后是否有回调
        last = df.iloc[-1]
        limit_up_row = recent.iloc[limit_up_day]
        
        pullback = (last['close'] - limit_up_row['close']) / limit_up_row['close'] * 100
        
        if pullback <= -2:  # 回调2%以上
            price = last['close']
            
            if not (3 <= price <= 15):
                continue
            
            # MACD确认
            macd = calc_macd(df['close'])
            if macd is None or macd <= 0:
                continue
            
            score = 80
            if pullback <= -5: score += 10
            if price <= 8: score += 10
            
            candidates.append({
                'code': code,
                'price': price,
                'pullback': pullback,
                'macd': macd,
                'score': score
            })
    
    candidates.sort(key=lambda x: x['score'], reverse=True)
    return candidates

print('='*60)
print('Limit-Up Pullback Strategy')
print('='*60)
picks = find_pullback_candidates()
print('Candidates:', len(picks))
for i, p in enumerate(picks[:10], 1):
    print(str(i) + '. ' + p['code'])
    print('   Price:' + str(round(p['price'], 2)) + ' Pullback:' + str(round(p['pullback'], 2)) + '% MACD:' + str(round(p['macd'], 4)) + ' Score:' + str(p['score']))
