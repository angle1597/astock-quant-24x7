# -*- coding: utf-8 -*-
"""V94 - 围绕consec>=4精细优化"""
import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB = 'data/stocks.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

def calc_score(klines):
    closes = [k[2] for k in klines]
    volumes = [k[5] for k in klines]
    n = len(closes)
    
    consec = 0
    for i in range(n-1, 0, -1):
        if closes[i] > closes[i-1]: consec += 1
        else: break
    
    chg5 = (closes[-1]/closes[-6]-1)*100 if n>=6 else 0
    chg10 = (closes[-1]/closes[-11]-1)*100 if n>=11 else 0
    chg3 = (closes[-1]/closes[-4]-1)*100 if n>=4 else 0
    avg_vol = sum(volumes[-6:-1])/5 if n>=6 else 1
    vol_ratio = volumes[-1]/avg_vol if avg_vol>0 else 1
    
    shrink = 0
    if consec >= 2 and n >= consec+1:
        shrink = 1
        for vi in range(n-1, n-consec-1, -1):
            if vi < 1: break
            if volumes[vi] >= volumes[vi-1]: shrink = 0; break
    
    gains=[]; losses=[]
    for i in range(n-6, n):
        d=closes[i]-closes[i-1]
        if d>0: gains.append(d);losses.append(0)
        else: gains.append(0);losses.append(abs(d))
    ag=sum(gains)/6 if gains else 0
    al=sum(losses)/6 if losses else 0
    rsi6 = 100-100/(1+ag/al) if al>0 else 100
    
    ma20 = sum(closes[-20:])/20 if n>=20 else closes[-1]
    ma_dev20 = (closes[-1]/ma20-1)*100 if ma20>0 else 0
    
    # 振幅收敛
    range_shrink = 0
    if n >= 10:
        recent_range = max(closes[-5:]) - min(closes[-5:])
        prev_range = max(closes[-10:-5]) - min(closes[-10:-5])
        if prev_range > 0 and recent_range/prev_range < 0.8:
            range_shrink = 1
    
    # 每日涨幅均匀度(不暴涨)
    if consec >= 3:
        daily_chgs = []
        for j in range(n-consec, n):
            daily_chgs.append((closes[j]/closes[j-1]-1)*100)
        max_chg = max(daily_chgs)
        uniform = 1 if max_chg < 5 else 0  # 没有单日暴涨>5%
    else:
        uniform = 0
    
    # 缩量程度
    shrink_pct = vol_ratio if avg_vol > 0 else 1
    
    score = 0
    if consec>=4: score+=30
    elif consec>=3: score+=20
    if 5<=chg5<=15: score+=20
    elif 3<=chg5<5: score+=10
    if chg10<10: score+=15
    if shrink==1 and consec>=2: score+=15
    if range_shrink: score+=10
    if uniform: score+=10
    if 40<=rsi6<=75: score+=10
    elif 25<=rsi6<40: score+=5
    if 0<ma_dev20<5: score+=10
    
    return consec, score, chg5, chg10, chg3, vol_ratio, shrink, shrink_pct, rsi6, range_shrink, uniform, ma_dev20

hold_days = 60
min_price = 10
stocks = cur.execute("SELECT DISTINCT code FROM kline WHERE code LIKE '000%' OR code LIKE '001%' OR code LIKE '002%' OR code LIKE '003%' OR code LIKE '600%' OR code LIKE '601%' OR code LIKE '603%'").fetchall()

print("=" * 70)
print("V94 consec>=4 精细优化")
print("=" * 70)

tests = [
    ("consec>=4 base", lambda f: f['consec']>=4),
    ("+shrink", lambda f: f['consec']>=4 and f['shrink']==1),
    ("+shrink+score75", lambda f: f['consec']>=4 and f['shrink']==1 and f['score']>=75),
    ("+shrink+score70", lambda f: f['consec']>=4 and f['shrink']==1 and f['score']>=70),
    ("+range shrink", lambda f: f['consec']>=4 and f['shrink']==1 and f['range_shrink']==1),
    ("+uniform", lambda f: f['consec']>=4 and f['shrink']==1 and f['uniform']==1),
    ("+shrink<0.7", lambda f: f['consec']>=4 and f['shrink']==1 and f['shrink_pct']<0.7),
    ("+shrink<0.8", lambda f: f['consec']>=4 and f['shrink']==1 and f['shrink_pct']<0.8),
    ("+rsi30-70", lambda f: f['consec']>=4 and f['shrink']==1 and 30<=f['rsi6']<=70),
    ("+ma_dev", lambda f: f['consec']>=4 and f['shrink']==1 and 0<f['ma_dev20']<5),
    ("best combo", lambda f: f['consec']>=4 and f['shrink']==1 and f['uniform']==1 and f['range_shrink']==1),
    ("best+score", lambda f: f['consec']>=4 and f['shrink']==1 and f['uniform']==1 and f['score']>=70),
    ("4+shrink+uni+rsi", lambda f: f['consec']>=4 and f['shrink']==1 and f['uniform']==1 and 30<=f['rsi6']<=70),
]

for name, cond in tests:
    total = good_10 = good_30 = wins = 0
    rets = []
    
    for (code,) in stocks:
        klines = cur.execute('SELECT date,open,close,high,low,volume FROM kline WHERE code=? ORDER BY date', (code,)).fetchall()
        if len(klines) < 40: continue
        klines = list(klines)
        
        for i in range(30, len(klines) - hold_days):
            window = klines[i-29:i+1]
            price = window[-1][2]
            if price >= min_price: continue
            
            f = {}
            f['consec'], f['score'], f['chg5'], f['chg10'], f['chg3'], f['vol_ratio'], f['shrink'], f['shrink_pct'], f['rsi6'], f['range_shrink'], f['uniform'], f['ma_dev20'] = calc_score(window)
            
            if not cond(f): continue
            
            total += 1
            buy_price = klines[i][2]
            hold_end = min(i + hold_days, len(klines) - 1)
            min_price_h = min(k[4] for k in klines[i:hold_end+1])
            if min_price_h <= buy_price * 0.93: continue
            sell_price = klines[hold_end][2]
            ret = (sell_price / buy_price - 1) * 100
            if ret >= 10: good_10 += 1
            if ret >= 30: good_30 += 1
            if ret > 0: wins += 1
            rets.append(ret)
    
    if total > 0:
        avg_r = sum(rets)/len(rets)
        print(f"{name:25s} total={total:4d} 10%={good_10/total*100:.1f}% 30%={good_30/total*100:.1f}% avg={avg_r:.2f}% win={wins/total*100:.1f}%")
    else:
        print(f"{name:25s} total=0")

conn.close()
