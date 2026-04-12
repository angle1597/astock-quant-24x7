# -*- coding: utf-8 -*-
import sqlite3
import pandas as pd
import numpy as np
import json

DB_PATH = 'data/stocks.db'

def main():
    print('深度优化开始...')
    conn = sqlite3.connect(DB_PATH)
    codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
    conn.close()
    print('股票:', len(codes))

    results = []

    strategies = [
        {'holding': 21, 'chg_min': 8, 'chg_max': 15, 'price_max': 10, 'vol_min': 1.5},
        {'holding': 21, 'chg_min': 5, 'chg_max': 12, 'price_max': 10, 'vol_min': 1.5},
        {'holding': 21, 'chg_min': 10, 'chg_max': 20, 'price_max': 10, 'vol_min': 1.5},
        {'holding': 28, 'chg_min': 8, 'chg_max': 15, 'price_max': 10, 'vol_min': 1.5},
        {'holding': 21, 'chg_min': 8, 'chg_max': 15, 'price_max': 8, 'vol_min': 1.5},
        {'holding': 21, 'chg_min': 8, 'chg_max': 15, 'price_max': 12, 'vol_min': 2.0},
        {'holding': 21, 'chg_min': 6, 'chg_max': 12, 'price_max': 10, 'vol_min': 1.8},
        {'holding': 21, 'chg_min': 8, 'chg_max': 12, 'price_max': 10, 'vol_min': 1.5},
        {'holding': 30, 'chg_min': 8, 'chg_max': 15, 'price_max': 10, 'vol_min': 1.5},
        {'holding': 21, 'chg_min': 5, 'chg_max': 15, 'price_max': 10, 'vol_min': 2.0},
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

                if not (s['chg_min'] <= chg <= s['chg_max']):
                    continue
                if row['close'] > s['price_max']:
                    continue

                vol_ma5 = df.iloc[i-5:i]['volume'].mean() if i >= 5 else df.iloc[:i]['volume'].mean()
                vol_ratio = row['volume'] / vol_ma5 if vol_ma5 > 0 else 0
                if vol_ratio < s['vol_min']:
                    continue

                buy = row['close']
                sell = df.iloc[i + s['holding']]['close']
                pnl = (sell - buy) / buy * 100
                trades.append({'code': code, 'pnl': pnl})

        if trades:
            pnls = [t['pnl'] for t in trades]
            wins = sum(1 for p in pnls if p > 0)
            r30 = sum(1 for p in pnls if p >= 30) / len(pnls) * 100
            r20 = sum(1 for p in pnls if p >= 20) / len(pnls) * 100
            results.append({
                'holding': s['holding'],
                'chg': str(s['chg_min']) + '-' + str(s['chg_max']),
                'price_max': s['price_max'],
                'vol_min': s['vol_min'],
                'n': len(trades),
                'r30': r30,
                'r20': r20,
                'win': wins / len(trades) * 100
            })
            print('持有' + str(s['holding']) + '天 涨幅' + str(s['chg_min']) + '-' + str(s['chg_max']) + '% <=' + str(s['price_max']) + '元 量比' + str(s['vol_min']) + 'x: ' + str(len(trades)) + '笔 30%达标=' + str(round(r30, 1)) + '%')

    results.sort(key=lambda x: x['r30'], reverse=True)
    print()
    print('=== 最佳策略 ===')
    for i, r in enumerate(results[:3], 1):
        print(str(i) + '. 持有' + str(r['holding']) + '天 涨幅' + r['chg'] + '%: 30%达标率=' + str(round(r['r30'], 1)) + '%')

    with open('data/final_optimize.json', 'w') as f:
        json.dump(results, f)
    print('完成!')

main()
