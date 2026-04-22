# -*- coding: utf-8 -*-
"""V92 - 在V90基础上逐个测试新因子"""
import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB = 'data/stocks.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

def ema(data, period):
    result = [data[0]]
    k = 2 / (period + 1)
    for i in range(1, len(data)):
        result.append(data[i] * k + result[-1] * (1 - k))
    return result

def calc_macd(closes):
    if len(closes) < 35: return 0, 0, 0
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    dif = [a - b for a, b in zip(ema12, ema26)]
    dea = ema(dif, 9)
    macd_h = [(d - e) * 2 for d, e in zip(dif, dea)]
    macd_turn = 0
    if len(macd_h) >= 3:
        if macd_h[-3] < 0 and macd_h[-2] < 0 and macd_h[-1] > 0:
            macd_turn = 1  # MACD柱翻红
    dif_up = 1 if dif[-1] > dif[-2] else 0  # DIF上升
    return macd_turn, dif_up, (1 if macd_h[-1] > 0 else 0)

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
    
    macd_turn, dif_up, macd_pos = calc_macd(closes)
    
    ma20 = sum(closes[-20:])/20 if n>=20 else closes[-1]
    ma_dev = (closes[-1]/ma20-1)*100 if ma20>0 else 0
    
    vcp = 0
    if n >= 20:
        for w in [3,5,8]:
            if n >= w*2:
                r1 = max(closes[-w:]) - min(closes[-w:])
                r2 = max(closes[-w*2:-w]) - min(closes[-w*2:-w])
                if r1 > 0 and r2 > 0 and r1/r2 < 1:
                    vcp = 1; break
    
    score = 0
    if consec>=4: score+=30
    elif consec>=3: score+=20
    elif consec>=2: score+=10
    if 5<=chg5<=15: score+=20
    elif 3<=chg5<5: score+=10
    if chg10<10: score+=15
    elif chg10<15: score+=5
    if shrink==1 and consec>=2: score+=15
    if shrink==1 and consec>=3: score+=10
    if vcp: score+=15
    if 0<ma_dev<5: score+=10
    elif -2<ma_dev<0: score+=5
    if 40<=rsi6<=75: score+=10
    elif 25<=rsi6<40: score+=5
    
    return consec, score, chg5, chg10, vol_ratio, shrink, rsi6, macd_turn, dif_up, macd_pos, vcp, ma_dev

hold_days = 60
min_price = 10
stocks = cur.execute("SELECT DISTINCT code FROM kline WHERE code LIKE '000%' OR code LIKE '001%' OR code LIKE '002%' OR code LIKE '003%' OR code LIKE '600%' OR code LIKE '601%' OR code LIKE '603%'").fetchall()

print("=" * 70)
print("V92 Factor-by-Factor Test (V90 base)")
print("=" * 70)

# Test each factor separately
tests = [
    ("V90 base", lambda f: f['consec']>=3 and f['score']>=75 and f['shrink']==1),
    ("+MACD turn", lambda f: f['consec']>=3 and f['score']>=75 and f['shrink']==1 and f['macd_turn']==1),
    ("+MACD pos", lambda f: f['consec']>=3 and f['score']>=75 and f['shrink']==1 and f['macd_pos']==1),
    ("+DIF up", lambda f: f['consec']>=3 and f['score']>=75 and f['shrink']==1 and f['dif_up']==1),
    ("+MACD any", lambda f: f['consec']>=3 and f['score']>=75 and f['shrink']==1 and (f['macd_turn'] or f['macd_pos'])),
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
            f['consec'], f['score'], f['chg5'], f['chg10'], f['vol_ratio'], f['shrink'], f['rsi6'], f['macd_turn'], f['dif_up'], f['macd_pos'], f['vcp'], f['ma_dev'] = calc_score(window)
            
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
        print(f"{name:20s} total={total:5d} 10%={good_10/total*100:.1f}% 30%={good_30/total*100:.1f}% avg={avg_r:.2f}% win={wins/total*100:.1f}%")
    else:
        print(f"{name:20s} total=0")

conn.close()
