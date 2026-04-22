# -*- coding: utf-8 -*-
"""V94 best combo - 实盘选股"""
import sqlite3, sys, io
from datetime import datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB = 'data/stocks.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

stocks = cur.execute("SELECT DISTINCT code FROM kline WHERE code LIKE '000%' OR code LIKE '001%' OR code LIKE '002%' OR code LIKE '003%' OR code LIKE '600%' OR code LIKE '601%' OR code LIKE '603%'").fetchall()

candidates = []
for (code,) in stocks:
    klines = cur.execute('SELECT date,open,close,high,low,volume FROM kline WHERE code=? ORDER BY date DESC LIMIT 30', (code,)).fetchall()
    if len(klines) < 25: continue
    klines = list(reversed(klines))
    closes = [k[2] for k in klines]
    volumes = [k[5] for k in klines]
    n = len(closes)
    
    price = closes[-1]
    if price >= 10: continue
    
    # 连涨
    consec = 0
    for i in range(n-1, 0, -1):
        if closes[i] > closes[i-1]: consec += 1
        else: break
    if consec < 4: continue
    
    # 缩量
    shrink = 0
    avg_vol = sum(volumes[-6:-1])/5 if n>=6 else 1
    if consec >= 2 and n >= consec+1:
        shrink = 1
        for vi in range(n-1, n-consec-1, -1):
            if vi < 1: break
            if volumes[vi] >= volumes[vi-1]: shrink = 0; break
    if not shrink: continue
    
    # 均匀上涨(无单日>5%)
    uniform = 1
    daily_chgs = []
    for j in range(n-consec, n):
        c = (closes[j]/closes[j-1]-1)*100
        daily_chgs.append(c)
        if c >= 5: uniform = 0; break
    
    # 振幅收缩
    range_shrink = 0
    if n >= 10:
        rr = max(closes[-5:]) - min(closes[-5:])
        pr = max(closes[-10:-5]) - min(closes[-10:-5])
        if pr > 0 and rr/pr < 0.8:
            range_shrink = 1
    
    # 5日/10日涨幅
    chg5 = (closes[-1]/closes[-6]-1)*100 if n>=6 else 0
    chg10 = (closes[-1]/closes[-11]-1)*100 if n>=11 else 0
    today_chg = (klines[-1][2]/klines[-1][1]-1)*100
    
    # RSI
    gains=[]; losses=[]
    for i in range(n-6, n):
        d=closes[i]-closes[i-1]
        if d>0: gains.append(d);losses.append(0)
        else: gains.append(0);losses.append(abs(d))
    ag=sum(gains)/6 if gains else 0
    al=sum(losses)/6 if losses else 0
    rsi6 = 100-100/(1+ag/al) if al>0 else 100
    
    # 排除涨停
    if today_chg >= 9.5: continue
    
    candidates.append({
        'code': code, 'price': price, 'today_chg': today_chg,
        'consec': consec, 'chg5': chg5, 'chg10': chg10,
        'uniform': uniform, 'range_shrink': range_shrink,
        'rsi6': rsi6, 'daily_chgs': daily_chgs
    })

conn.close()
candidates.sort(key=lambda x: -x['chg5'])

print("=" * 60)
print("V94 Best Combo")
print("=" * 60)
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("consec>=4 + shrink + uniform + range_shrink")
print("Backtest: 10%=59.3%, 30%=22.0%, win=69.5%")
print(f"Signals: {len(candidates)}")
print()

for i, c in enumerate(candidates[:10]):
    flag = ""
    if c['uniform'] and c['range_shrink']: flag = " *BEST*"
    print(f"{i+1}. {c['code']} | {c['price']:.2f} | +{c['today_chg']:.1f}% | consec:{c['consec']} | 5d:+{c['chg5']:.1f}% | 10d:+{c['chg10']:.1f}% | RSI:{c['rsi6']:.0f}{flag}")
    print(f"   daily: {[f'+{d:.1f}%' for d in c['daily_chgs']]}")
