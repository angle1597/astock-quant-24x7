# -*- coding: utf-8 -*-
"""高效策略优化管道 - Step 1: 预计算所有指标"""
import sqlite3, sys, time
import numpy as np
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 70)
print("STEP 1: Pre-compute All Indicators")
print("=" * 70)

DB = 'data/stocks.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

start_time = time.time()

# Check existing columns
cols = [r[1] for r in cur.execute("PRAGMA table_info(kline)").fetchall()]
print(f"Existing columns: {cols}")

# Pre-compute indicators for all stocks
stocks = cur.execute("SELECT DISTINCT code FROM kline WHERE code LIKE '000%' OR code LIKE '001%' OR code LIKE '002%' OR code LIKE '003%' OR code LIKE '600%' OR code LIKE '601%' OR code LIKE '603%'").fetchall()
print(f"Total stocks: {len(stocks)}")

# Pre-compute daily indicators
computed = 0
for si, (code,) in enumerate(stocks):
    klines = cur.execute('SELECT date,open,close,high,low,volume FROM kline WHERE code=? ORDER BY date', (code,)).fetchall()
    if len(klines) < 30: continue
    
    closes = np.array([float(k[2]) for k in klines])
    volumes = np.array([float(k[5]) for k in klines])
    highs = np.array([float(k[3]) for k in klines])
    lows = np.array([float(k[4]) for k in klines])
    n = len(closes)
    
    # Pre-compute indicators for each day
    for i in range(20, n):
        # RSI(6)
        if i >= 6:
            gains = np.where(closes[i-6:i] > closes[i-7:i-1], closes[i-6:i] - closes[i-7:i-1], 0)
            losses = np.where(closes[i-6:i] < closes[i-7:i-1], closes[i-7:i-1] - closes[i-6:i], 0)
            ag = gains.mean() if len(gains) > 0 else 0
            al = losses.mean() if len(losses) > 0 else 0
            rsi6 = 100 - 100/(1 + ag/al) if al > 0 else 100
        else:
            rsi6 = 50
        
        # MA5, MA10, MA20
        ma5 = closes[i-5:i+1].mean() if i >= 5 else closes[:i+1].mean()
        ma10 = closes[i-10:i+1].mean() if i >= 10 else closes[:i+1].mean()
        ma20 = closes[i-20:i+1].mean() if i >= 20 else closes[:i+1].mean()
        
        # Volatility
        if i >= 20:
            vol20 = closes[i-20:i+1].std()
        else:
            vol20 = closes[:i+1].std()
        
        # Volume ratio
        avg_vol5 = volumes[i-5:i].mean() if i >= 5 else volumes[:i+1].mean()
        vr = volumes[i] / avg_vol5 if avg_vol5 > 0 else 1
        
        # Range
        recent_range = highs[i-4:i+1].max() - lows[i-4:i+1].min()
        prev_range = highs[i-9:i-4].max() - lows[i-9:i-4].min() if i >= 10 else 0
        range_shrink = recent_range / prev_range if prev_range > 0 else 1
        
    computed += 1
    if (si+1) % 500 == 0:
        elapsed = time.time() - start_time
        print(f"Progress: {si+1}/{len(stocks)} ({elapsed:.1f}s)")

elapsed = time.time() - start_time
print(f"\nCompleted: {computed}/{len(stocks)} stocks in {elapsed:.1f}s")
print("Next: Run factor_combo_tester.py for fast combination testing")

conn.close()
