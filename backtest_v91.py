# -*- coding: utf-8 -*-
"""V91 - MACD金叉 + 布林带 + V90融合 回测"""
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
    if len(closes) < 35: return None, None, None
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    dif = [a - b for a, b in zip(ema12, ema26)]
    dea = ema(dif, 9)
    macd = [(d - e) * 2 for d, e in zip(dif, dea)]
    return dif[-1], dea[-1], macd[-1]

def calc_bollinger(closes, period=20, std_mult=2):
    if len(closes) < period: return None, None, None
    ma = sum(closes[-period:]) / period
    variance = sum((c - ma) ** 2 for c in closes[-period:]) / period
    std = variance ** 0.5
    return ma - std_mult * std, ma, ma + std_mult * std

def calc_score(klines):
    closes = [k[2] for k in klines]
    volumes = [k[5] for k in klines]
    n = len(closes)
    
    # 连涨
    consec = 0
    for i in range(n-1, 0, -1):
        if closes[i] > closes[i-1]: consec += 1
        else: break
    
    # 5日/10日涨幅
    chg5 = (closes[-1]/closes[-6]-1)*100 if n>=6 else 0
    chg10 = (closes[-1]/closes[-11]-1)*100 if n>=11 else 0
    
    # 量比
    avg_vol = sum(volumes[-6:-1])/5 if n>=6 else 1
    vol_ratio = volumes[-1]/avg_vol if avg_vol>0 else 1
    
    # 缩量
    shrink = 0
    if consec >= 2 and n >= consec+1:
        shrink = 1
        for vi in range(n-1, n-consec-1, -1):
            if vi < 1: break
            if volumes[vi] >= volumes[vi-1]: shrink = 0; break
    
    # RSI
    gains=[]; losses=[]
    for i in range(n-6, n):
        d=closes[i]-closes[i-1]
        if d>0: gains.append(d);losses.append(0)
        else: gains.append(0);losses.append(abs(d))
    ag=sum(gains)/6 if gains else 0
    al=sum(losses)/6 if losses else 0
    rsi6 = 100-100/(1+ag/al) if al>0 else 100
    
    # MACD
    dif, dea, macd = calc_macd(closes)
    macd_golden = 1 if dif is not None and dea is not None and dif > dea and (n >= 27 and (dif[-2] if False else True)) else 0
    # 简化: DIF>DEA且MACD柱状图>0
    macd_positive = 1 if macd is not None and macd > 0 else 0
    
    # 布林带
    bl, bm, bu = calc_bollinger(closes)
    boll_pos = 0
    if bl is not None and bm is not None and bu is not None:
        boll_range = bu - bl
        if boll_range > 0:
            boll_pos = (closes[-1] - bl) / boll_range  # 0-1
    boll_squeeze = 0
    if bl is not None and bm is not None:
        avg_range = sum([closes[-i] - closes[-i-1] if closes[-i] > closes[-i-1] else 0 for i in range(1, min(20, n))]) / 19
        if avg_range > 0:
            boll_squeeze = 1 if boll_range / avg_range < 0.5 else 0
    
    # VCP
    vcp = 0
    if n >= 20:
        highs_20 = closes[-20:]
        max_h = max(highs_20)
        min_l = min(highs_20)
        if max_h > min_l:
            contractions = []
            for w in [3,5,8]:
                if n >= w*2:
                    r1 = max(closes[-w:]) - min(closes[-w:])
                    r2 = max(closes[-w*2:-w]) - min(closes[-w*2:-w])
                    if r1 > 0 and r2 > 0:
                        contractions.append(r1/r2)
            if len(contractions) >= 2:
                vcp = 1 if all(c < 1 for c in contractions) else 0
    
    # MA偏离
    ma20 = sum(closes[-20:])/20 if n>=20 else closes[-1]
    ma_dev = (closes[-1]/ma20-1)*100 if ma20>0 else 0
    
    # 打分
    score = 0
    if consec>=4: score+=30
    elif consec>=3: score+=20
    elif consec>=2: score+=10
    
    if 5<=chg5<=15: score+=20
    elif 3<=chg5<5: score+=10
    
    if chg10<15: score+=10
    elif chg10<10: score+=15
    
    if shrink==1 and consec>=2: score+=15
    if shrink==1 and consec>=3: score+=10  # 额外加分
    
    if macd_positive: score+=10
    
    if 0.3<boll_pos<0.8: score+=10  # 布林带中上轨
    if boll_squeeze: score+=10  # 布林带收缩
    
    if vcp: score+=15
    
    if 0<ma_dev<5: score+=10
    elif -2<ma_dev<0: score+=5
    
    if 40<=rsi6<=75: score+=10
    elif 25<=rsi6<40: score+=5
    
    return consec, score, chg5, chg10, vol_ratio, shrink, rsi6, macd_positive, boll_pos, boll_squeeze, vcp, ma_dev

# 回测
hold_days = 60
min_price = 10
stocks = cur.execute("SELECT DISTINCT code FROM kline WHERE code LIKE '000%' OR code LIKE '001%' OR code LIKE '002%' OR code LIKE '003%' OR code LIKE '600%' OR code LIKE '601%' OR code LIKE '603%'").fetchall()

total = good_10 = good_30 = wins = 0
results = []

for si, (code,) in enumerate(stocks):
    klines = cur.execute('SELECT date,open,close,high,low,volume FROM kline WHERE code=? ORDER BY date', (code,)).fetchall()
    if len(klines) < 40: continue
    klines = list(klines)
    
    for i in range(30, len(klines) - hold_days):
        window = klines[i-29:i+1]
        price = window[-1][2]
        if price >= min_price: continue
        
        consec, score, chg5, chg10, vol_ratio, shrink, rsi6, macd_pos, boll_pos, boll_squeeze, vcp, ma_dev = calc_score(window)
        
        if consec < 3: continue
        if score < 75: continue
        
        total += 1
        buy_price = klines[i][2]
        hold_end = min(i + hold_days, len(klines) - 1)
        max_price = max(k[3] for k in klines[i:hold_end+1])
        min_price_h = min(k[4] for k in klines[i:hold_end+1])
        sell_price = klines[hold_end][2]
        
        # 止损
        if min_price_h <= buy_price * 0.93:
            continue
        
        ret = (sell_price / buy_price - 1) * 100
        if ret >= 10: good_10 += 1
        if ret >= 30: good_30 += 1
        if ret > 0: wins += 1
        results.append(ret)

print("=" * 60)
print("V91 MACD + Bollinger + V90 fusion")
print("=" * 60)
print(f"total: {total} 10%={good_10/total*100 if total else 0:.1f}% 30%={good_30/total*100 if total else 0:.1f}% avg={sum(results)/len(results):.2f}% win={wins/total*100 if total else 0:.1f}%")
print()

# 对比V90
print("V90 vs V91:")
print(f"V90: 1680 trades, 10%=44.6%, 30%=18.8%, avg=14.30%, win=69.3%")
print(f"V91: {total} trades, 10%={good_10/total*100 if total else 0:.1f}%, 30%={good_30/total*100 if total else 0:.1f}%, avg={sum(results)/len(results):.2f}%, win={wins/total*100 if total else 0:.1f}%")

conn.close()
