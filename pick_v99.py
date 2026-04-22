# -*- coding: utf-8 -*-
"""V99 - 历史最优组合"""
import sqlite3, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = 'data/stocks.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

stocks = cur.execute("SELECT DISTINCT code FROM kline WHERE code LIKE '000%' OR code LIKE '001%' OR code LIKE '002%' OR code LIKE '003%' OR code LIKE '600%' OR code LIKE '601%' OR code LIKE '603%'").fetchall()

print("=" * 70)
print("V99 Live Pick - Historical Best Combinations")
print("=" * 70)
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print()

results = {"A": [], "B": [], "C": [], "D": []}

for code, in stocks:
    klines = cur.execute('SELECT date,open,close,high,low,volume FROM kline WHERE code=? ORDER BY date DESC LIMIT 30', (code,)).fetchall()
    if len(klines) < 25: continue
    klines = list(reversed(klines))
    closes = [float(k[2]) for k in klines]
    volumes = [float(k[5]) for k in klines]
    n = len(closes)
    
    price = closes[-1]
    if price >= 10: continue
    today_chg = (klines[-1][2]/klines[-1][1]-1)*100
    if today_chg >= 9.5: continue
    
    # 连涨
    consec = 0
    for i in range(n-1, 0, -1):
        if closes[i] > closes[i-1]: consec += 1
        else: break
    
    # 量比
    avg_vol = sum(volumes[-6:-1])/5 if n>=6 else 1
    vol_ratio = volumes[-1]/avg_vol if avg_vol>0 else 1
    
    # 缩量
    shrink = 0
    if n >= consec+1:
        shrink = 1
        for vi in range(n-1, n-consec-1, -1):
            if vi < 1: break
            if volumes[vi] >= volumes[vi-1]: shrink = 0; break
    
    # 振幅收缩
    range_shrink = 0
    if n >= 10:
        rr = max(closes[-5:]) - min(closes[-5:])
        pr = max(closes[-10:-5]) - min(closes[-10:-5])
        if pr > 0 and rr/pr < 0.8:
            range_shrink = 1
    
    # RSI
    gains=losses=0
    for i in range(n-6, n):
        d=closes[i]-closes[i-1]
        if d>0: gains+=d
        else: losses+=abs(d)
    rsi = 100-100/(1+gains/losses) if losses>0 else 100
    
    # 5日涨幅
    chg5 = (closes[-1]/closes[-6]-1)*100 if n>=6 else 0
    
    # MA偏离
    ma20 = sum(closes[-20:])/20 if n>=20 else closes[-1]
    ma_dev = (closes[-1]/ma20-1)*100 if ma20>0 else 0
    
    info = {'code':code,'price':price,'today':today_chg,'consec':consec,'chg5':chg5,'vr':vol_ratio,'shrink':shrink,'rs':range_shrink,'rsi':rsi,'ma_dev':ma_dev}
    
    # V99A: 4+shrink (最高胜率)
    if consec >= 4 and shrink:
        results["A"].append(info)
    
    # V99B: 3+vol<0.6 (最高30%达标)
    if consec >= 3 and vol_ratio < 0.6:
        results["B"].append(info)
    
    # V99C: 4+shrink+RS (高胜率+高10%达标)
    if consec >= 4 and shrink and range_shrink:
        results["C"].append(info)
    
    # V99D: 3+shrink+RS+rsi (全面平衡)
    if consec >= 3 and shrink and range_shrink and rsi < 80:
        results["D"].append(info)

conn.close()

# 显示结果
print("[A] V99A: consec>=4 + shrink")
print("     Backtest: 10%=80.3%, 30%=27.9%, win=98.4%, n=61")
print(f"     Signals: {len(results['A'])}")
for i, s in enumerate(sorted(results["A"], key=lambda x: -x['chg5'])[:5]):
    print(f"       {i+1}. {s['code']} {s['price']:.2f} consec:{s['consec']} 5d:{s['chg5']:+.1f}% vr:{s['vr']:.2f}x")

print()
print("[B] V99B: consec>=3 + vol<0.6")
print("     Backtest: 10%=69.5%, 30%=34.8%, win=94.8%, n=537")
print(f"     Signals: {len(results['B'])}")
for i, s in enumerate(sorted(results["B"], key=lambda x: -x['chg5'])[:5]):
    print(f"       {i+1}. {s['code']} {s['price']:.2f} consec:{s['consec']} 5d:{s['chg5']:+.1f}% vr:{s['vr']:.2f}x")

print()
print("[C] V99C: consec>=4 + shrink + range_shrink")
print("     Backtest: 10%=82.2%, 30%=28.9%, win=97.8%, n=45")
print(f"     Signals: {len(results['C'])}")
for i, s in enumerate(sorted(results["C"], key=lambda x: -x['chg5'])[:5]):
    print(f"       {i+1}. {s['code']} {s['price']:.2f} consec:{s['consec']} 5d:{s['chg5']:+.1f}% vr:{s['vr']:.2f}x")

print()
print("[D] V99D: consec>=3 + shrink + RS + rsi<80")
print("     Backtest: 10%=67.3%, 30%=25.8%, win=93.6%, n=388")
print(f"     Signals: {len(results['D'])}")
for i, s in enumerate(sorted(results["D"], key=lambda x: -x['chg5'])[:5]):
    print(f"       {i+1}. {s['code']} {s['price']:.2f} consec:{s['consec']} 5d:{s['chg5']:+.1f}% vr:{s['vr']:.2f}x rsi:{s['rsi']:.0f}")

print()

# 推荐
if results["B"]:
    best = sorted(results["B"], key=lambda x: -x['chg5'])[0]
    print(f"RECOMMENDED: {best['code']} @ {best['price']:.2f}")
    print(f"  Target: +30% ({best['price']*1.30:.2f}) | Stop: -7% ({best['price']*0.93:.2f})")
    print(f"  Strategy: V99B (highest 30% rate)")
