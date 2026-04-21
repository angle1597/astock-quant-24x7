# -*- coding: utf-8 -*-
"""
V88 策略 - 放宽缩量要求，保持其他条件
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
from datetime import datetime

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'

def calc_score_v88(klines):
    closes = [k[2] for k in klines]
    volumes = [k[5] for k in klines]
    
    consec = 0
    for i in range(len(closes)-1, 0, -1):
        if closes[i] > closes[i-1]: consec += 1
        else: break
    
    chg5 = (closes[-1]/closes[-6]-1)*100 if len(closes)>=6 else 0
    chg10 = (closes[-1]/closes[-11]-1)*100 if len(closes)>=11 else 0
    vol_ratio = volumes[-1]/(sum(volumes[-6:-1])/5) if len(volumes)>=6 and sum(volumes[-6:-1])>0 else 1
    
    shrink = 0
    if consec >= 2 and len(volumes) >= consec+1:
        shrink = 1
        for vi in range(len(volumes)-1, len(volumes)-consec, -1):
            if volumes[vi] >= volumes[vi-1]: shrink = 0; break
    
    gains=[];losses=[]
    for i in range(len(closes)-6, len(closes)):
        d=closes[i]-closes[i-1]
        if d>0: gains.append(d);losses.append(0)
        else: gains.append(0);losses.append(abs(d))
    ag=sum(gains)/6 if gains else 0
    al=sum(losses)/6 if losses else 0
    rsi6 = 100-100/(1+ag/al) if al>0 else 100
    
    score = 0
    if consec>=4: score+=35
    elif consec>=3: score+=25
    elif consec>=2: score+=10
    if 5<=chg5<=12: score+=20
    elif 3<=chg5<5: score+=10
    elif 12<chg5<=15: score+=10
    if chg10<10: score+=15
    elif chg10<15: score+=5
    if shrink==1 and consec>=3: score+=20  # 缩量加分但不必须
    if 1.2<=vol_ratio<=2.0: score+=10
    elif vol_ratio>2.0: score+=5
    if 40<=rsi6<=70: score+=10
    elif 30<=rsi6<40 or 70<rsi6<=75: score+=5
    
    return consec, score, chg5, chg10, vol_ratio, shrink, rsi6

def pick_v88():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    stocks = cur.execute("SELECT DISTINCT code FROM kline WHERE code LIKE '000%' OR code LIKE '600%' OR code LIKE '601%' OR code LIKE '603%'").fetchall()
    
    candidates = []
    for (code,) in stocks:
        klines = cur.execute('SELECT date,open,close,high,low,volume FROM kline WHERE code=? ORDER BY date DESC LIMIT 30', (code,)).fetchall()
        if len(klines) < 25: continue
        klines = list(reversed(klines))
        
        price = klines[-1][2]
        if price >= 10: continue
        
        consec, score, chg5, chg10, vol_ratio, shrink, rsi6 = calc_score_v88(klines)
        
        # V88条件：连涨>=4 + 评分>=80（不强制缩量）
        if consec < 4: continue
        if score < 80: continue
        
        today_chg = (klines[-1][2]/klines[-1][1]-1)*100
        if today_chg >= 9.5: continue
        
        candidates.append({
            'code': code, 'price': price, 'today_chg': today_chg,
            'consec': consec, 'score': score, 'chg5': chg5, 'chg10': chg10,
            'vol_ratio': vol_ratio, 'shrink': shrink, 'rsi6': rsi6
        })
    
    conn.close()
    candidates.sort(key=lambda x: -x['score'])
    
    print("=" * 70)
    print("V88 策略选股")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    print("V88条件: 连涨>=4 + 评分>=80")
    print(f"信号数: {len(candidates)}")
    print()
    
    for i, c in enumerate(candidates[:5]):
        print(f"{i+1}. {c['code']} | {c['price']:.2f}元 | 评分:{c['score']} | 连涨:{c['consec']}天")
        print(f"   5日:{c['chg5']:+.1f}% 10日:{c['chg10']:+.1f}% RSI:{c['rsi6']:.0f} 缩量:{'是' if c['shrink'] else '否'}")
    
    return candidates

if __name__ == '__main__':
    pick_v88()