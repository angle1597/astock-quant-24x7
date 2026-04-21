# -*- coding: utf-8 -*-
"""
V90 策略 - V87+V89融合
V87最优(评分75+必须缩量) + V89新因子(VCP+MA偏离)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
from datetime import datetime

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'

def calc_v90_score(klines, idx=None):
    if idx is not None:
        recent = klines[idx-25:idx]
    else:
        recent = klines[-25:]
    
    closes = [k[2] for k in recent]
    volumes = [k[5] for k in recent]
    highs = [k[3] for k in recent]
    lows = [k[4] for k in recent]
    n = len(closes)
    
    consec = 0
    for i in range(n-1, 0, -1):
        if closes[i] > closes[i-1]: consec += 1
        else: break
    
    chg5 = (closes[-1]/closes[-6]-1)*100 if n>=6 else 0
    chg10 = (closes[-1]/closes[-11]-1)*100 if n>=11 else 0
    vol_ratio = volumes[-1]/(sum(volumes[-6:-1])/5) if n>=6 and sum(volumes[-6:-1])>0 else 1
    
    shrink = 0
    if consec >= 2:
        shrink = 1
        for vi in range(n-1, n-consec, -1):
            if volumes[vi] >= volumes[vi-1]: shrink = 0; break
    
    # VCP
    if n >= 10:
        rr = (max(highs[-5:])-min(lows[-5:]))/min(lows[-5:])*100 if min(lows[-5:])>0 else 100
        pr = (max(highs[-10:-5])-min(lows[-10:-5]))/min(lows[-10:-5])*100 if min(lows[-10:-5])>0 else 100
        vcp = 1 if rr < pr*0.7 else 0
    else: vcp = 0
    
    # MA偏离
    if n >= 20:
        ma20 = sum(closes[-20:])/20
        ma_dev = (closes[-1]-ma20)/ma20*100
    else: ma_dev = 0
    
    # RSI
    gains=[];losses=[]
    for i in range(n-6, n):
        d=closes[i]-closes[i-1]
        if d>0: gains.append(d);losses.append(0)
        else: gains.append(0);losses.append(abs(d))
    ag=sum(gains)/6; al=sum(losses)/6
    rsi6 = 100-100/(1+ag/al) if al>0 else 100
    
    score = 0
    if consec>=4: score+=35
    elif consec>=3: score+=25
    elif consec>=2: score+=10
    if 5<=chg5<=12: score+=20
    elif 3<=chg5<5 or 12<chg5<=15: score+=10
    if chg10<10: score+=15
    elif chg10<15: score+=5
    if shrink==1 and consec>=3: score+=20
    if 1.2<=vol_ratio<=2.0: score+=10
    elif vol_ratio>2.0: score+=5
    if 40<=rsi6<=70: score+=10
    elif 30<=rsi6<40 or 70<rsi6<=75: score+=5
    # V89新因子
    if vcp==1: score+=10  # VCP加分
    if -5<=ma_dev<=5: score+=5  # MA偏离健康加分
    
    return consec, score, chg5, chg10, vol_ratio, shrink, rsi6, vcp, ma_dev

def backtest_v90():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    stocks = cur.execute("SELECT DISTINCT code FROM kline WHERE code LIKE '000%' OR code LIKE '600%' OR code LIKE '601%' OR code LIKE '603%'").fetchall()
    
    tc=0; wc=0; r10=0; r30=0; tp=0
    
    for (code,) in stocks:
        klines = cur.execute('SELECT date,open,close,high,low,volume FROM kline WHERE code=? ORDER BY date', (code,)).fetchall()
        if len(klines)<150: continue
        
        for idx in range(30, len(klines)-100):
            bp = klines[idx][2]
            if bp>=10 or bp<=0: continue
            
            result = calc_v90_score(klines, idx)
            if result is None: continue
            consec,score,_,_,_,shrink,_,_,_ = result
            
            if consec<3: continue
            if score<75: continue
            if shrink!=1: continue  # V87核心：必须缩量
            
            tchg = (klines[idx][2]/klines[idx][1]-1)*100 if klines[idx][1]>0 else 0
            if tchg>=9.5: continue
            
            si = min(idx+100, len(klines)-1)
            profit = (klines[si][2]/bp-1)*100
            tc+=1; tp+=profit
            if profit>0: wc+=1
            if profit>=10: r10+=1
            if profit>=30: r30+=1
    
    conn.close()
    
    print("=" * 70)
    print("V90 回测结果 (V87+V89融合)")
    print("=" * 70)
    if tc>0:
        print(f"交易次数: {tc}")
        print(f"胜率: {wc/tc*100:.1f}%")
        print(f"10%达标率: {r10/tc*100:.1f}%")
        print(f"30%达标率: {r30/tc*100:.1f}%")
        print(f"平均收益: {tp/tc:.2f}%")
    
    print("\n完整策略演进:")
    print("-" * 70)
    print(f"{'版本':<6} {'交易数':<8} {'10%达标':<10} {'30%达标':<10} {'均收益':<10} {'胜率':<8} {'核心改进'}")
    print("-" * 70)
    print(f"{'V85':<6} {'8':<8} {'87.5%':<10} {'87.5%':<10} {'85.10%':<10} {'100%':<8} {'MA20+缩量<50%'}")
    print(f"{'V86':<6} {'9338':<8} {'32.5%':<10} {'9.8%':<10} {'6.33%':<10} {'56.2%':<8} {'放宽条件'}")
    print(f"{'V87':<6} {'635':<8} {'44.1%':<10} {'19.4%':<10} {'14.22%':<10} {'67.6%':<8} {'必须缩量+评分75'}")
    print(f"{'V89':<6} {'11855':<8} {'44.7%':<10} {'17.4%':<10} {'13.55%':<10} {'67.3%':<8} {'+VCP+MA偏离'}")
    if tc>0:
        print(f"{'V90':<6} {tc:<8} {f'{r10/tc*100:.1f}%':<10} {f'{r30/tc*100:.1f}%':<10} {f'{tp/tc:.2f}%':<10} {f'{wc/tc*100:.1f}%':<8} {'V87+V89融合'}")
    print("-" * 70)

if __name__ == '__main__':
    backtest_v90()