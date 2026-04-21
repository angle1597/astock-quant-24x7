# -*- coding: utf-8 -*-
"""
V89 回测验证
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'

def calc_v89_score(klines, idx):
    if idx < 25: return None
    recent = klines[idx-25:idx]
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
    
    avg_vol5 = sum(volumes[-6:-1])/5 if n>=6 else 1
    vol_ratio = volumes[-1]/avg_vol5 if avg_vol5 > 0 else 1
    
    shrink = 0
    if consec >= 2:
        shrink = 1
        for vi in range(n-1, n-consec, -1):
            if volumes[vi] >= volumes[vi-1]: shrink = 0; break
    
    if n >= 10:
        recent_range = (max(highs[-5:])-min(lows[-5:]))/min(lows[-5:])*100 if min(lows[-5:])>0 else 100
        prev_range = (max(highs[-10:-5])-min(lows[-10:-5]))/min(lows[-10:-5])*100 if min(lows[-10:-5])>0 else 100
        vcp = 1 if recent_range < prev_range*0.7 else 0
    else: vcp = 0
    
    if n >= 20:
        ma20 = sum(closes[-20:])/20
        ma_dev = (closes[-1]-ma20)/ma20*100
    else: ma_dev = 0
    
    gains=[];losses=[]
    for i in range(n-6, n):
        d=closes[i]-closes[i-1]
        if d>0: gains.append(d);losses.append(0)
        else: gains.append(0);losses.append(abs(d))
    ag=sum(gains)/6 if gains else 0
    al=sum(losses)/6 if losses else 0
    rsi6 = 100-100/(1+ag/al) if al>0 else 100
    
    score = 0
    if consec>=5: score+=35
    elif consec>=4: score+=30
    elif consec>=3: score+=20
    elif consec>=2: score+=10
    if 3<=chg5<=10: score+=20
    elif 10<chg5<=15: score+=10
    elif 1<=chg5<3: score+=5
    if chg10<10: score+=15
    elif chg10<15: score+=5
    if shrink==1 and consec>=3: score+=25
    elif shrink==1 and consec>=2: score+=15
    elif vol_ratio<0.8: score+=5
    if vcp==1: score+=15
    if -5<=ma_dev<=5: score+=10
    elif -8<=ma_dev<-5 or 5<ma_dev<=8: score+=5
    if 40<=rsi6<=70: score+=10
    elif 30<=rsi6<40 or 70<rsi6<=75: score+=5
    
    return consec, score

def backtest_v89():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    stocks = cur.execute("SELECT DISTINCT code FROM kline WHERE code LIKE '000%' OR code LIKE '600%' OR code LIKE '601%' OR code LIKE '603%'").fetchall()
    
    trade_count=0; win_count=0; r10=0; r30=0; total_profit=0
    
    for (code,) in stocks:
        klines = cur.execute('SELECT date,open,close,high,low,volume FROM kline WHERE code=? ORDER BY date', (code,)).fetchall()
        if len(klines) < 150: continue
        
        for idx in range(30, len(klines)-100):
            buy_price = klines[idx][2]
            if buy_price >= 10 or buy_price <= 0: continue
            
            result = calc_v89_score(klines, idx)
            if result is None: continue
            consec, score = result
            
            if consec < 3: continue
            if score < 75: continue
            
            today_chg = (klines[idx][2]/klines[idx][1]-1)*100 if klines[idx][1]>0 else 0
            if today_chg >= 9.5: continue
            
            sell_idx = min(idx+100, len(klines)-1)
            profit = (klines[sell_idx][2]/buy_price-1)*100
            
            trade_count += 1
            total_profit += profit
            if profit > 0: win_count += 1
            if profit >= 10: r10 += 1
            if profit >= 30: r30 += 1
    
    conn.close()
    
    print("=" * 70)
    print("V89 回测结果")
    print("=" * 70)
    print(f"交易次数: {trade_count}")
    if trade_count > 0:
        print(f"胜率: {win_count/trade_count*100:.1f}%")
        print(f"10%达标率: {r10/trade_count*100:.1f}%")
        print(f"30%达标率: {r30/trade_count*100:.1f}%")
        print(f"平均收益: {total_profit/trade_count:.2f}%")
    
    print("\n策略演进对比:")
    print("-" * 70)
    print(f"{'版本':<8} {'交易数':<10} {'10%达标':<12} {'30%达标':<12} {'均收益':<12} {'胜率':<10}")
    print("-" * 70)
    print(f"{'V85':<8} {'8':<10} {'87.5%':<12} {'87.5%':<12} {'85.10%':<12} {'100%':<10}")
    print(f"{'V86':<8} {'9338':<10} {'32.5%':<12} {'9.8%':<12} {'6.33%':<12} {'56.2%':<10}")
    print(f"{'V87':<8} {'635':<10} {'44.1%':<12} {'19.4%':<12} {'14.22%':<12} {'67.6%':<10}")
    print(f"{'V88':<8} {'4':<10} {'V86变体':<12} {'-':<12} {'-':<12} {'-':<10}")
    if trade_count > 0:
        print(f"{'V89':<8} {trade_count:<10} {f'{r10/trade_count*100:.1f}%':<12} {f'{r30/trade_count*100:.1f}%':<12} {f'{total_profit/trade_count:.2f}%':<12} {f'{win_count/trade_count*100:.1f}%':<10}")
    print("-" * 70)

if __name__ == '__main__':
    backtest_v89()