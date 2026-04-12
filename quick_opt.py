# -*- coding: utf-8 -*-
"""
快速优化 - 测试核心策略组合
"""
import sqlite3
import json
import numpy as np
import pandas as pd

DB_PATH = 'data/stocks.db'

def quick_backtest(codes, holding, chg_min, chg_max, price_max):
    """快速回测"""
    conn = sqlite3.connect(DB_PATH)
    
    trades = []
    for code in codes[:100]:  # 只测试前100只
        df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
        if df.empty or len(df) < 60:
            continue
        
        for i in range(30, len(df) - holding):
            row = df.iloc[i]
            prev = df.iloc[i-1]
            
            chg = (row['close'] - prev['close']) / prev['close'] * 100 if prev['close'] > 0 else 0
            
            if not (chg_min <= chg <= chg_max):
                continue
            if row['close'] > price_max:
                continue
            
            buy = row['close']
            sell = df.iloc[i + holding]['close']
            pnl = (sell - buy) / buy * 100
            
            trades.append({'code': code, 'pnl': pnl})
    
    conn.close()
    
    if not trades:
        return {'n': 0, 'r30': 0, 'r20': 0, 'win': 0}
    
    pnls = [t['pnl'] for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    
    return {
        'n': len(trades),
        'r30': sum(1 for p in pnls if p >= 30) / len(pnls) * 100,
        'r20': sum(1 for p in pnls if p >= 20) / len(pnls) * 100,
        'win': wins / len(pnls) * 100,
        'avg': np.mean(pnls)
    }

def main():
    print('快速优化开始...')
    
    conn = sqlite3.connect(DB_PATH)
    codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
    conn.close()
    print(f'股票: {len(codes)}只')
    
    results = []
    
    # 测试不同组合
    params = [
        (14, 5, 10, 10),
        (14, 8, 15, 10),
        (21, 5, 10, 10),
        (21, 8, 15, 10),
        (21, 10, 20, 10),
        (28, 5, 10, 10),
        (28, 8, 15, 10),
        (14, 3, 8, 8),
        (21, 3, 8, 8),
        (21, 5, 12, 10),
    ]
    
    for holding, chg_min, chg_max, price_max in params:
        r = quick_backtest(codes, holding, chg_min, chg_max, price_max)
        if r['n'] > 0:
            results.append({
                'holding': holding,
                'chg': f'{chg_min}-{chg_max}',
                'price_max': price_max,
                'n': r['n'],
                'r30': r['r30'],
                'r20': r['r20'],
                'win': r['win'],
                'avg': r['avg']
            })
            print(f'持有{holding}天 涨幅{chg_min}-{chg_max}% ≤{price_max}元: {r["n"]}笔 胜率{r["win"]:.1f}% 达标率30%={r["r30"]:.1f}%')
    
    results.sort(key=lambda x: x['r30'], reverse=True)
    
    print('\n=== TOP 3 ===')
    for i, r in enumerate(results[:3], 1):
        print(f'{i}. 持有{r["holding"]}天 涨幅{r["chg"]}% ≤{r["price_max"]}元: 30%达标率{r["r30"]:.1f}% 胜率{r["win"]:.1f}%')
    
    with open('data/quick_optimize.json', 'w') as f:
        json.dump(results, f)
    
    print('\n完成!')

main()
