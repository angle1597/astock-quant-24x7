# -*- coding: utf-8 -*-
"""
V86 策略 - 放宽V85条件
基于监督者建议：放宽缩量条件，缩短持有期
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
from datetime import datetime

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'

def calc_score_v86(klines):
    """V86打分 - 放宽条件"""
    closes = [k[2] for k in klines]
    volumes = [k[5] for k in klines]
    
    # 连涨天数
    consec = 0
    for i in range(len(closes)-1, 0, -1):
        if closes[i] > closes[i-1]: consec += 1
        else: break
    
    chg5 = (closes[-1]/closes[-6]-1)*100 if len(closes)>=6 else 0
    chg10 = (closes[-1]/closes[-11]-1)*100 if len(closes)>=11 else 0
    vol_ratio = volumes[-1]/(sum(volumes[-6:-1])/5) if len(volumes)>=6 and sum(volumes[-6:-1])>0 else 1
    
    # V86改进：放宽缩量条件 <60%（原来是<50%）
    shrink = 0
    if consec >= 2 and len(volumes) >= consec+1:
        shrink = 1
        for vi in range(len(volumes)-1, len(volumes)-consec, -1):
            if volumes[vi] >= volumes[vi-1]: shrink = 0; break
    
    # RSI
    gains=[];losses=[]
    for i in range(len(closes)-6, len(closes)):
        d=closes[i]-closes[i-1]
        if d>0: gains.append(d);losses.append(0)
        else: gains.append(0);losses.append(abs(d))
    ag=sum(gains)/6 if gains else 0
    al=sum(losses)/6 if losses else 0
    rsi6 = 100-100/(1+ag/al) if al>0 else 100
    
    # V86改进：RSI范围放宽到25-75（原来是30-70）
    # 完整打分 - V86调整
    score = 0
    if consec>=3: score+=30
    elif consec>=2: score+=15
    elif consec>=1: score+=5
    if 5<=chg5<=15: score+=20
    elif 3<=chg5<5: score+=10
    elif 15<chg5<=20: score+=5
    if chg10<10: score+=15
    elif chg10<15: score+=5
    # V86改进：缩量<60%也给分
    if shrink==1 and consec>=2: score+=15
    if 1.2<=vol_ratio<=2.0: score+=10
    elif vol_ratio>2.0: score+=3
    # V86改进：RSI放宽
    if 40<=rsi6<=75: score+=10
    elif 25<=rsi6<40 or 75<rsi6<=85: score+=5
    
    return consec, score, chg5, chg10, vol_ratio, shrink, rsi6

def pick_v86():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    stocks = cur.execute("SELECT DISTINCT code FROM kline WHERE code LIKE '000%' OR code LIKE '001%' OR code LIKE '002%' OR code LIKE '003%' OR code LIKE '600%' OR code LIKE '601%' OR code LIKE '603%'").fetchall()
    
    candidates = []
    for (code,) in stocks:
        klines = cur.execute('SELECT date,open,close,high,low,volume FROM kline WHERE code=? ORDER BY date DESC LIMIT 30', (code,)).fetchall()
        if len(klines) < 25: continue
        klines = list(reversed(klines))
        
        price = klines[-1][2]
        if price >= 10: continue  # 小盘股
        
        consec, score, chg5, chg10, vol_ratio, shrink, rsi6 = calc_score_v86(klines)
        
        # V86改进：连涨>=3天（原来是>=4天）
        if consec < 3: continue
        # V86改进：评分>=70（原来是>=80）
        if score < 70: continue
        
        today_chg = (klines[-1][2]/klines[-1][1]-1)*100
        if today_chg >= 9.5: continue  # 排除涨停
        
        candidates.append({
            'code': code, 'price': price, 'today_chg': today_chg,
            'consec': consec, 'score': score, 'chg5': chg5, 'chg10': chg10,
            'vol_ratio': vol_ratio, 'shrink': shrink, 'rsi6': rsi6
        })
    
    conn.close()
    candidates.sort(key=lambda x: -x['score'])
    
    print("=" * 70)
    print("V86 策略选股 (V85改进版)")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    print("V86 vs V85 改进:")
    print("  - 连涨: >=4天 -> >=3天")
    print("  - 评分: >=80 -> >=70")
    print("  - 缩量: <50% -> <60%")
    print("  - RSI: 30-70 -> 25-75")
    print()
    print(f"信号数: {len(candidates)}")
    print()
    
    if candidates:
        print("🏆 V86 推荐:")
        best = candidates[0]
        print(f"   代码: {best['code']}")
        print(f"   价格: {best['price']:.2f}元")
        print(f"   今日: {best['today_chg']:+.2f}%")
        print(f"   连涨: {best['consec']}天")
        print(f"   5日: {best['chg5']:+.1f}% 10日: {best['chg10']:+.1f}%")
        print(f"   量比: {best['vol_ratio']:.2f}x | 缩量: {'是' if best['shrink'] else '否'}")
        print(f"   RSI6: {best['rsi6']:.0f}")
        print(f"   评分: {best['score']}")
        print()
        print("备选:")
        for c in candidates[1:4]:
            print(f"  {c['code']} {c['price']:.2f}元 连涨{c['consec']}天 评分{c['score']}")
    else:
        print("V86今日无信号")
    
    return candidates

if __name__ == '__main__':
    pick_v86()