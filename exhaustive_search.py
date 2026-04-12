# -*- coding: utf-8 -*-
"""
穷举优化 - 寻找达标率20%+的策略
"""
import sys, sqlite3, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'
conn = sqlite3.connect(DB)
codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
conn.close()

print(f'Total stocks: {len(codes)}')

results = []
for hold in [7, 10, 14]:
    for chg_min, chg_max in [(3, 8), (4, 9), (4, 10), (5, 10), (5, 12), (6, 10), (6, 12)]:
        for pmax in [15, 18, 20]:
            for vol_min in [1.0, 1.2, 1.5]:
                trades = []
                for code in codes:
                    conn = sqlite3.connect(DB)
                    df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
                    conn.close()
                    if df is None or len(df) < 40:
                        continue
                    df = df.tail(120).reset_index(drop=True)
                    df['vol_ma5'] = df['volume'].rolling(5).mean()
                    df['vol_ratio'] = df['volume'] / df['vol_ma5']
                    
                    for i in range(20, len(df)-hold-1):
                        row, prev = df.iloc[i], df.iloc[i-1]
                        chg = (row['close']-prev['close'])/prev['close']*100 if prev['close']>0 else 0
                        vol = row['vol_ratio'] if not pd.isna(row['vol_ratio']) else 1
                        if chg_min <= chg <= chg_max and 3 <= row['close'] <= pmax and vol >= vol_min:
                            buy = row['close']
                            future = df.iloc[i+1:i+hold+1]['close'].tolist()
                            if future:
                                pnl = (max(future)-buy)/buy*100
                                trades.append(pnl)
                
                if len(trades) >= 10:
                    r30 = sum(1 for p in trades if p >= 30) / len(trades) * 100
                    r20 = sum(1 for p in trades if p >= 20) / len(trades) * 100
                    r10 = sum(1 for p in trades if p >= 10) / len(trades) * 100
                    results.append({
                        'hold': hold, 'chg': f'{chg_min}-{chg_max}', 
                        'pmax': pmax, 'vol': vol_min,
                        'n': len(trades), 'avg': np.mean(trades), 
                        'max': max(trades), 'r30': r30, 'r20': r20, 'r10': r10
                    })

results.sort(key=lambda x: (x['r30'], x['avg']), reverse=True)

print(f'\nTOP 15 strategies by 30% target rate:')
print(f'{"#":^3} {"hold":^4} {"chg":^8} {"pmax":^5} {"vol":^4} {"n":^5} {"avg%":^6} {"max%":^6} {"30%":^6} {"20%":^6} {"10%":^6}')
print('-' * 80)
for i, r in enumerate(results[:15], 1):
    print(f'{i:^3} {r["hold"]:^4} {r["chg"]:^8} {r["pmax"]:^5} {r["vol"]:^4.1f} {r["n"]:^5} '
          f'{r["avg"]:^6.1f} {r["max"]:^6.1f} {r["r30"]:^6.1f} {r["r20"]:^6.1f} {r["r10"]:^6.1f}')

best = results[0] if results else None
if best:
    print(f'\nBest strategy: hold {best["hold"]}d, buy at {best["chg"]}% change, price <= {best["pmax"]}, vol >= {best["vol"]}')
    print(f'30% target rate: {best["r30"]:.1f}%')
    print(f'20% target rate: {best["r20"]:.1f}%')
    print(f'10% target rate: {best["r10"]:.1f}%')
