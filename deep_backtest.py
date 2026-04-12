# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3, numpy as np, pandas as pd

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'
conn = sqlite3.connect(DB)
codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
conn.close()

print(f'Total stocks: {len(codes)}')

# Deep backtest with best params
hold, chg_min, chg_max, pmax, vol_min = 10, 4, 10, 18, 1.2

trades = []
for code in codes:
    conn = sqlite3.connect(DB)
    df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
    conn.close()
    if df is None or len(df) < 35:
        continue
    df = df.tail(100).reset_index(drop=True)
    df['vol_ma5'] = df['volume'].rolling(5).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma5']
    
    for i in range(15, len(df)-hold-1):
        row, prev = df.iloc[i], df.iloc[i-1]
        chg = (row['close']-prev['close'])/prev['close']*100 if prev['close']>0 else 0
        vol = row['vol_ratio'] if not pd.isna(row['vol_ratio']) else 1
        if chg_min <= chg <= chg_max and 3 <= row['close'] <= pmax and vol >= vol_min:
            buy = row['close']
            future = df.iloc[i+1:i+hold+1]['close'].tolist()
            if future:
                pnl = (max(future)-buy)/buy*100
                trades.append({'code': code, 'date': row['date'], 'buy': buy, 'pnl': pnl, 'vol': vol, 'chg': chg})

if trades:
    pnls = [t['pnl'] for t in trades]
    wins = sum(1 for t in trades if t['pnl'] > 0)
    targets_30 = sum(1 for p in pnls if p >= 30)
    targets_20 = sum(1 for p in pnls if p >= 20)
    targets_10 = sum(1 for p in pnls if p >= 10)
    
    print(f'\nBacktest results (hold={hold}d, chg={chg_min}-{chg_max}%, price<={pmax}, vol>={vol_min}):')
    print(f'  Trades: {len(trades)}')
    print(f'  Win rate: {wins/len(trades)*100:.1f}%')
    print(f'  Avg gain: {np.mean(pnls):.1f}%')
    print(f'  Max gain: {max(pnls):.1f}%')
    print(f'  30% target rate: {targets_30/len(trades)*100:.1f}%')
    print(f'  20% target rate: {targets_20/len(trades)*100:.1f}%')
    print(f'  10% target rate: {targets_10/len(trades)*100:.1f}%')
    
    # Best trades
    trades.sort(key=lambda x: x['pnl'], reverse=True)
    print(f'\nTop 10 best trades:')
    for i, t in enumerate(trades[:10], 1):
        code = t['code']
        date = t['date']
        buy = t['buy']
        pnl = t['pnl']
        print(f'  {i}. {code} @ {buy:.2f} on {date} -> {pnl:.1f}%')
