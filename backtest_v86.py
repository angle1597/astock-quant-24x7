# -*- coding: utf-8 -*-
"""
V86 回测验证
验证V86策略相比V85的历史表现
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
from datetime import datetime, timedelta

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'

def calc_score_v86(klines, idx):
    """V86打分"""
    if idx < 25:
        return 0, 0, 0, 0, 0, 0, 0
    
    recent = klines[idx-25:idx]  # 用25天前的数据
    closes = [k[2] for k in recent]
    volumes = [k[5] for k in recent]
    
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
    if consec>=3: score+=30
    elif consec>=2: score+=15
    elif consec>=1: score+=5
    if 5<=chg5<=15: score+=20
    elif 3<=chg5<5: score+=10
    elif 15<chg5<=20: score+=5
    if chg10<10: score+=15
    elif chg10<15: score+=5
    if shrink==1 and consec>=2: score+=15
    if 1.2<=vol_ratio<=2.0: score+=10
    elif vol_ratio>2.0: score+=3
    if 40<=rsi6<=75: score+=10
    elif 25<=rsi6<40 or 75<rsi6<=85: score+=5
    
    return consec, score, chg5, chg10, vol_ratio, shrink, rsi6

def backtest_v86():
    """V86回测"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # 获取所有股票
    stocks = cur.execute("SELECT DISTINCT code FROM kline WHERE code LIKE '000%' OR code LIKE '600%' OR code LIKE '601%' OR code LIKE '603%'").fetchall()
    
    trades = []
    trade_count = 0
    win_count = 0
    r10_count = 0  # 达标10%
    r30_count = 0  # 达标30%
    total_profit = 0
    
    for (code,) in stocks:
        klines = cur.execute('SELECT date,open,close,high,low,volume FROM kline WHERE code=? ORDER BY date', (code,)).fetchall()
        
        if len(klines) < 150:  # 需要足够数据
            continue
        
        # 从第30天开始模拟
        for idx in range(30, len(klines) - 40):
            buy_date = klines[idx][0]
            buy_price = klines[idx][2]
            
            if buy_price >= 10 or buy_price <= 0:
                continue
            
            consec, score, chg5, chg10, vol_ratio, shrink, rsi6 = calc_score_v86(klines, idx)
            
            # V86条件
            if consec < 3:
                continue
            if score < 70:
                continue
            
            # 排除涨停买入
            today_chg = (klines[idx][2]/klines[idx][1]-1)*100 if klines[idx][1] > 0 else 0
            if today_chg >= 9.5:
                continue
            
            # 模拟持有40天的收益（V86缩短了持有期）
            sell_idx = min(idx + 40, len(klines) - 1)
            sell_price = klines[sell_idx][2]
            profit_pct = (sell_price / buy_price - 1) * 100
            
            trade_count += 1
            total_profit += profit_pct
            if profit_pct > 0:
                win_count += 1
            if profit_pct >= 10:
                r10_count += 1
            if profit_pct >= 30:
                r30_count += 1
            
            trades.append({
                'code': code,
                'buy_date': buy_date,
                'buy_price': buy_price,
                'sell_price': sell_price,
                'profit': profit_pct
            })
    
    conn.close()
    
    # 统计结果
    print("=" * 70)
    print("V86 策略回测结果")
    print("=" * 70)
    print(f"回测时间范围: 使用历史K线数据")
    print(f"总交易次数: {trade_count}")
    print(f"盈利次数: {win_count}")
    print(f"胜率: {win_count/trade_count*100:.1f}%" if trade_count > 0 else "N/A")
    print(f"10%达标率: {r10_count/trade_count*100:.1f}%" if trade_count > 0 else "N/A")
    print(f"30%达标率: {r30_count/trade_count*100:.1f}%" if trade_count > 0 else "N/A")
    print(f"平均收益: {total_profit/trade_count:.2f}%" if trade_count > 0 else "N/A")
    print()
    
    # 与V85对比
    print("V86 vs V85 对比:")
    print("-" * 50)
    print(f"{'指标':<15} {'V85':<15} {'V86':<15}")
    print("-" * 50)
    print(f"{'交易次数':<15} {'8':<15} {trade_count}")
    print(f"{'10%达标率':<15} {'87.5%':<15} {f'{r10_count/trade_count*100:.1f}%' if trade_count > 0 else 'N/A'}")
    print(f"{'30%达标率':<15} {'87.5%':<15} {f'{r30_count/trade_count*100:.1f}%' if trade_count > 0 else 'N/A'}")
    print(f"{'平均收益':<15} {'85.10%':<15} {f'{total_profit/trade_count:.2f}%' if trade_count > 0 else 'N/A'}")
    print(f"{'胜率':<15} {'100%':<15} {f'{win_count/trade_count*100:.1f}%' if trade_count > 0 else 'N/A'}")
    print("-" * 50)
    
    return {
        'trade_count': trade_count,
        'win_rate': win_count/trade_count*100 if trade_count > 0 else 0,
        'r10_rate': r10_count/trade_count*100 if trade_count > 0 else 0,
        'r30_rate': r30_count/trade_count*100 if trade_count > 0 else 0,
        'avg_profit': total_profit/trade_count if trade_count > 0 else 0
    }

if __name__ == '__main__':
    backtest_v86()