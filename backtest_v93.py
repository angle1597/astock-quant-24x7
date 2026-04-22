# -*- coding: utf-8 -*-
"""V93 - 修复因子测试 + 新因子探索"""
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
    ma5 = sum(closes[-5:])/5 if n>=5 else closes[-1]
    ma10 = sum(closes[-10:])/10 if n>=10 else closes[-1]
    ma_dev20 = (closes[-1]/ma20-1)*100 if ma20>0 else 0
    
    # 均线多头排列
    ma_bull = 1 if ma5 > ma10 > ma20 else 0
    
    # 价格离MA5距离(不要太远)
    ma5_dist = (closes[-1]/ma5-1)*100 if ma5>0 else 0
    near_ma5 = 1 if abs(ma5_dist) < 3 else 0
    
    # 成交量趋势(5日平均vs10日平均)
    vol5 = sum(volumes[-5:])/5
    vol10 = sum(volumes[-10:])/10
    vol_trend = vol5/vol10 if vol10>0 else 1
    
    # 振幅收敛
    if n >= 10:
        recent_range = max(closes[-5:]) - min(closes[-5:])
        prev_range = max(closes[-10:-5]) - min(closes[-10:-5])
        range_shrink = 1 if prev_range > 0 and recent_range/prev_range < 0.8 else 0
    else:
        range_shrink = 0
    
    # 评分
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
    if ma_bull: score+=10
    if near_ma5: score+=5
    if 40<=rsi6<=75: score+=10
    elif 25<=rsi6<40: score+=5
    if range_shrink: score+=10
    
    return consec, score, chg5, chg10, vol_ratio, shrink, rsi6, ma_bull, near_ma5, vol_trend, range_shrink, ma_dev20

hold_days = 60
min_price = 10
stocks = cur.execute("SELECT DISTINCT code FROM kline WHERE code LIKE '000%' OR code LIKE '001%' OR code LIKE '002%' OR code LIKE '003%' OR code LIKE '600%' OR code LIKE '601%' OR code LIKE '603%'").fetchall()

print("=" * 70)
print("V93 Factor-by-Factor Test")
print("=" * 70)

tests = [
    ("V87 base", lambda f: f['consec']>=3 and f['score']>=75 and f['shrink']==1),
    ("+MA bull", lambda f: f['consec']>=3 and f['score']>=75 and f['shrink']==1 and f['ma_bull']==1),
    ("+near MA5", lambda f: f['consec']>=3 and f['score']>=75 and f['shrink']==1 and f['near_ma5']==1),
    ("+range shrink", lambda f: f['consec']>=3 and f['score']>=75 and f['shrink']==1 and f['range_shrink']==1),
    ("+vol trend up", lambda f: f['consec']>=3 and f['score']>=75 and f['shrink']==1 and f['vol_trend']>1),
    ("+all new", lambda f: f['consec']>=3 and f['score']>=75 and f['shrink']==1 and f['ma_bull']==1 and f['range_shrink']==1),
    ("score>=70", lambda f: f['consec']>=3 and f['score']>=70 and f['shrink']==1),
    ("score>=65", lambda f: f['consec']>=3 and f['score']>=65 and f['shrink']==1),
    ("consec>=4", lambda f: f['consec']>=4 and f['score']>=75 and f['shrink']==1),
    ("V90 fusion", lambda f: f['consec']>=3 and f['score']>=75 and f['shrink']==1 and f['range_shrink']==1),
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
            f['consec'], f['score'], f['chg5'], f['chg10'], f['vol_ratio'], f['shrink'], f['rsi6'], f['ma_bull'], f['near_ma5'], f['vol_trend'], f['range_shrink'], f['ma_dev20'] = calc_score(window)
            
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
