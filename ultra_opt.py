# -*- coding: utf-8 -*-
"""极限优化 - 突破50%达标率"""
import sqlite3
import pandas as pd
import numpy as np
import json

DB_PATH = 'data/stocks.db'

def backtest_all(codes, holding, chg_min, chg_max, price_max):
    """回测所有股票"""
    trades = []
    conn = sqlite3.connect(DB_PATH)
    
    for code in codes:
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
            trades.append({'code': code, 'buy_date': row['date'], 'buy_price': buy, 'pnl': pnl})
    
    conn.close()
    return trades

def main():
    print('极限优化开始...')
    conn = sqlite3.connect(DB_PATH)
    codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
    conn.close()
    print('股票:', len(codes))

    results = []
    
    # 扩展参数网格
    params = [
        (21, 3, 10, 10),
        (21, 5, 15, 10),
        (21, 8, 20, 10),
        (28, 3, 10, 10),
        (28, 5, 15, 10),
        (28, 8, 20, 10),
        (30, 3, 10, 10),
        (30, 5, 15, 10),
        (30, 8, 20, 10),
        (21, 1, 5, 8),
        (21, 2, 8, 8),
        (21, 0, 3, 10),
        (28, 0, 5, 10),
        (30, 0, 5, 10),
        (21, -2, 3, 10),
        (21, -5, 5, 10),
    ]

    for holding, chg_min, chg_max, price_max in params:
        trades = backtest_all(codes, holding, chg_min, chg_max, price_max)
        
        if trades:
            pnls = [t['pnl'] for t in trades]
            wins = sum(1 for p in pnls if p > 0)
            r30 = sum(1 for p in pnls if p >= 30) / len(pnls) * 100
            r20 = sum(1 for p in pnls if p >= 20) / len(pnls) * 100
            r15 = sum(1 for p in pnls if p >= 15) / len(pnls) * 100
            
            results.append({
                'holding': holding,
                'chg_min': chg_min,
                'chg_max': chg_max,
                'price_max': price_max,
                'n': len(trades),
                'r30': r30,
                'r20': r20,
                'r15': r15,
                'win': wins / len(pnls) * 100,
                'avg': np.mean(pnls),
                'max': max(pnls)
            })
            
            print('持有' + str(holding) + '天 涨幅' + str(chg_min) + '-' + str(chg_max) + '% <=' + str(price_max) + '元: ' + str(len(trades)) + '笔 胜率' + str(round(wins/len(pnls)*100, 1)) + '% 30%达标=' + str(round(r30, 1)) + '%')

    results.sort(key=lambda x: x['r30'], reverse=True)
    
    print()
    print('='*60)
    print('TOP 5 最优策略')
    print('='*60)
    for i, r in enumerate(results[:5], 1):
        print(str(i) + '. 持有' + str(r['holding']) + '天 涨幅' + str(r['chg_min']) + '-' + str(r['chg_max']) + '% <=' + str(r['price_max']) + '元')
        print('   交易' + str(r['n']) + '笔 胜率' + str(round(r['win'], 1)) + '%')
        print('   30%达标=' + str(round(r['r30'], 1)) + '% 20%达标=' + str(round(r['r20'], 1)) + '% 最高=' + str(round(r['max'], 1)) + '%')

    with open('data/ultra_optimize.json', 'w') as f:
        json.dump(results[:20], f, ensure_ascii=False, indent=2)
    
    print()
    print('结果已保存!')

main()
