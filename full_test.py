# -*- coding: utf-8 -*-
"""全面优化测试"""
import sqlite3
import pandas as pd
import numpy as np
import json

DB_PATH = 'data/stocks.db'

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    delta = closes.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_macd(closes):
    if len(closes) < 30:
        return None
    ema12 = closes.ewm(span=12).mean()
    ema26 = closes.ewm(span=26).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9).mean()
    macd = (dif - dea) * 2
    return macd.iloc[-1]

def main():
    print('全面优化测试')
    conn = sqlite3.connect(DB_PATH)
    codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
    conn.close()
    print('股票:', len(codes))

    results = []
    
    # 测试各种因子组合
    strategies = [
        {'name': 'MACD金叉', 'holding': 28, 'chg': (8, 15), 'price': 10, 'macd': True, 'rsi': False, 'kdj': False},
        {'name': 'RSI<40', 'holding': 28, 'chg': (8, 15), 'price': 10, 'macd': False, 'rsi': True, 'kdj': False},
        {'name': 'MACD+RSI', 'holding': 28, 'chg': (8, 15), 'price': 10, 'macd': True, 'rsi': True, 'kdj': False},
        {'name': '无筛选', 'holding': 28, 'chg': (8, 15), 'price': 10, 'macd': False, 'rsi': False, 'kdj': False},
        {'name': 'MACD金叉(21天)', 'holding': 21, 'chg': (8, 15), 'price': 10, 'macd': True, 'rsi': False, 'kdj': False},
        {'name': 'MACD金叉(30天)', 'holding': 30, 'chg': (8, 15), 'price': 10, 'macd': True, 'rsi': False, 'kdj': False},
        {'name': '宽涨幅', 'holding': 28, 'chg': (5, 20), 'price': 10, 'macd': True, 'rsi': False, 'kdj': False},
        {'name': '低价股', 'holding': 28, 'chg': (8, 15), 'price': 8, 'macd': True, 'rsi': False, 'kdj': False},
    ]

    for s in strategies:
        trades = []
        for code in codes:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
            conn.close()
            if df.empty or len(df) < 60:
                continue
            
            for i in range(30, len(df) - s['holding']):
                row = df.iloc[i]
                prev = df.iloc[i-1]
                chg = (row['close'] - prev['close']) / prev['close'] * 100 if prev['close'] > 0 else 0
                
                if not (s['chg'][0] <= chg <= s['chg'][1]):
                    continue
                if row['close'] > s['price']:
                    continue
                
                # 因子筛选
                if s['macd']:
                    macd = calc_macd(df.iloc[:i+1]['close'])
                    if macd is None or macd <= 0:
                        continue
                
                if s['rsi']:
                    rsi = calc_rsi(df.iloc[:i+1]['close'])
                    if rsi is None or rsi.iloc[-1] >= 40:
                        continue
                
                buy = row['close']
                sell = df.iloc[i + s['holding']]['close']
                max_price = df.iloc[i+1:i+s['holding']+1]['close'].max()
                
                pnl = (sell - buy) / buy * 100
                max_pnl = (max_price - buy) / buy * 100
                
                trades.append({'pnl': pnl, 'max_pnl': max_pnl})
        
        if trades:
            pnls = [t['pnl'] for t in trades]
            max_pnls = [t['max_pnl'] for t in trades]
            wins = sum(1 for p in pnls if p > 0)
            r30 = sum(1 for p in pnls if p >= 30) / len(pnls) * 100
            r30_max = sum(1 for p in max_pnls if p >= 30) / len(max_pnls) * 100
            
            results.append({
                'name': s['name'],
                'n': len(trades),
                'win': wins / len(pnls) * 100,
                'r30': r30,
                'r30_max': r30_max,
                'avg': np.mean(pnls)
            })
            
            print(s['name'] + ': ' + str(len(trades)) + '笔 胜率' + str(round(wins/len(pnls)*100, 1)) + '% 30%=' + str(round(r30, 1)) + '% 最高30%=' + str(round(r30_max, 1)) + '%')

    results.sort(key=lambda x: x['r30_max'], reverse=True)
    
    print()
    print('='*60)
    print('最终排名')
    print('='*60)
    for i, r in enumerate(results, 1):
        print(str(i) + '. ' + r['name'] + ': ' + str(round(r['r30_max'], 1)) + '%')

main()
