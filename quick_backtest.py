# -*- coding: utf-8 -*-
"""快速回测分析"""
import sys, sqlite3, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'
conn = sqlite3.connect(DB)
codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
conn.close()
print(f'Total stocks: {len(codes)}')

# 回测
results = []
for holding in [3, 5, 7]:
    for chg_min, chg_max in [(1,5), (2,8), (3,10)]:
        for pmax in [15, 20, 30]:
            trades = []
            for code in codes:
                conn = sqlite3.connect(DB)
                df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
                conn.close()
                if df is None or len(df) < 40:
                    continue
                df = df.tail(120).reset_index(drop=True)
                for i in range(20, len(df)-holding-1):
                    row, prev = df.iloc[i], df.iloc[i-1]
                    chg = (row['close']-prev['close'])/prev['close']*100 if prev['close']>0 else 0
                    if chg_min <= chg <= chg_max and 3 <= row['close'] <= pmax:
                        buy = row['close']
                        future = df.iloc[i+1:i+holding+1]['close'].tolist()
                        if future:
                            pnl_max = (max(future)-buy)/buy*100
                            trades.append(pnl_max)
            
            if len(trades) >= 10:
                targets_30 = sum(1 for p in trades if p >= 30)
                targets_20 = sum(1 for p in trades if p >= 20)
                results.append({
                    'hold': holding, 'chg': f'{chg_min}-{chg_max}', 'pmax': pmax,
                    'n': len(trades), 'avg': np.mean(trades), 'max': max(trades),
                    'r30': targets_30/len(trades)*100, 'r20': targets_20/len(trades)*100
                })

results.sort(key=lambda x: x['r30'], reverse=True)
print(f'\nTOP 10 strategies (by 30% target rate):')
for i, r in enumerate(results[:10], 1):
    print(f"{i}. hold={r['hold']}d chg={r['chg']}% price<={r['pmax']} -> trades={r['n']} avg={r['avg']:.1f}% max={r['max']:.1f}% 30%rate={r['r30']:.1f}% 20%rate={r['r20']:.1f}%")

# Find best stocks
print(f'\nBest performing stocks (history):')
best_stocks = []
for code in codes:
    conn = sqlite3.connect(DB)
    df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
    conn.close()
    if df is None or len(df) < 30:
        continue
    df = df.tail(100).reset_index(drop=True)
    max_pnl = 0
    for i in range(15, len(df)-5):
        row, prev = df.iloc[i], df.iloc[i-1]
        chg = (row['close']-prev['close'])/prev['close']*100 if prev['close']>0 else 0
        if 2 <= chg <= 8 and 3 <= row['close'] <= 20:
            buy = row['close']
            future = df.iloc[i+1:i+6]['close'].tolist()
            if future:
                pnl = (max(future)-buy)/buy*100
                if pnl > max_pnl:
                    max_pnl = pnl
    if max_pnl > 10:
        best_stocks.append((code, max_pnl))

best_stocks.sort(key=lambda x: x[1], reverse=True)
for code, pnl in best_stocks[:10]:
    print(f"  {code}: max weekly gain {pnl:.1f}%")
