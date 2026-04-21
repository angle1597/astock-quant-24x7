# -*- coding: utf-8 -*-
"""
V89 策略 - 多因子融合优化版
融合最新学术研究成果:
1. 动量生命周期 (Momentum Life Cycle) - 连涨后缩量=动量延续信号
2. 成交量确认 (Volume Confirmation) - 缩量上涨=机构控盘
3. 波动率收缩 (Volatility Contraction) - 低波动+上涨=蓄力突破
4. 均线偏离率 (MA Deviation) - 偏离MA20不大=趋势健康
5. 换手率变化 (Turnover Change) - 换手率下降+上涨=锁仓
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import sqlite3
from datetime import datetime

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'

def calc_v89_score(klines):
    """V89多因子打分"""
    closes = [k[2] for k in klines]
    volumes = [k[5] for k in klines]
    highs = [k[3] for k in klines]
    lows = [k[4] for k in klines]
    
    n = len(closes)
    price = closes[-1]
    
    # === 因子1: 连涨天数 (Momentum) ===
    consec = 0
    for i in range(n-1, 0, -1):
        if closes[i] > closes[i-1]: consec += 1
        else: break
    
    # === 因子2: 5日/10日涨幅 ===
    chg5 = (closes[-1]/closes[-6]-1)*100 if n>=6 else 0
    chg10 = (closes[-1]/closes[-11]-1)*100 if n>=11 else 0
    chg20 = (closes[-1]/closes[-21]-1)*100 if n>=21 else 0
    
    # === 因子3: 缩量确认 ===
    avg_vol5 = sum(volumes[-6:-1])/5 if n>=6 else 1
    avg_vol10 = sum(volumes[-11:-1])/10 if n>=11 else 1
    vol_ratio = volumes[-1]/avg_vol5 if avg_vol5 > 0 else 1
    vol_ratio10 = volumes[-1]/avg_vol10 if avg_vol10 > 0 else 1
    
    shrink = 0
    if consec >= 2:
        shrink = 1
        for vi in range(n-1, n-consec, -1):
            if volumes[vi] >= volumes[vi-1]: shrink = 0; break
    
    # === 因子4: 波动率收缩 (VCP - Volatility Contraction Pattern) ===
    if n >= 10:
        recent_high = max(highs[-5:])
        recent_low = min(lows[-5:])
        prev_high = max(highs[-10:-5])
        prev_low = min(lows[-10:-5])
        recent_range = (recent_high - recent_low) / recent_low * 100 if recent_low > 0 else 100
        prev_range = (prev_high - prev_low) / prev_low * 100 if prev_low > 0 else 100
        vcp = 1 if recent_range < prev_range * 0.7 else 0  # 波动率收缩30%+
    else:
        vcp = 0
    
    # === 因子5: MA20偏离率 ===
    if n >= 20:
        ma20 = sum(closes[-20:]) / 20
        ma_dev = (price - ma20) / ma20 * 100
    else:
        ma20 = price
        ma_dev = 0
    
    # === 因子6: RSI ===
    gains=[];losses=[]
    for i in range(n-6, n):
        d=closes[i]-closes[i-1]
        if d>0: gains.append(d);losses.append(0)
        else: gains.append(0);losses.append(abs(d))
    ag=sum(gains)/6 if gains else 0
    al=sum(losses)/6 if losses else 0
    rsi6 = 100-100/(1+ag/al) if al>0 else 100
    
    # === 因子7: 量价背离检测 ===
    # 价格上涨但成交量递减 = 健康上涨
    price_up = consec >= 3
    vol_down = all(volumes[-i] < volumes[-i-1] for i in range(1, min(consec+1, 4))) if consec >= 2 else False
    healthy_uptrend = 1 if (price_up and vol_down) else 0
    
    # === V89 综合打分 ===
    score = 0
    
    # 连涨 (0-35分)
    if consec >= 5: score += 35
    elif consec >= 4: score += 30
    elif consec >= 3: score += 20
    elif consec >= 2: score += 10
    
    # 5日涨幅 (0-20分)
    if 3 <= chg5 <= 10: score += 20  # 温和上涨最好
    elif 10 < chg5 <= 15: score += 10
    elif 1 <= chg5 < 3: score += 5
    
    # 10日涨幅控制 (0-15分)
    if chg10 < 10: score += 15
    elif chg10 < 15: score += 5
    
    # 缩量确认 (0-25分) - V89核心因子
    if shrink == 1 and consec >= 3: score += 25  # 缩量+连涨=最强信号
    elif shrink == 1 and consec >= 2: score += 15
    elif vol_ratio < 0.8: score += 5  # 单日缩量
    
    # VCP波动率收缩 (0-15分) - 新增因子
    if vcp == 1: score += 15
    
    # MA20偏离率 (0-10分) - 新增因子
    if -5 <= ma_dev <= 5: score += 10  # 偏离不大=趋势健康
    elif -8 <= ma_dev < -5 or 5 < ma_dev <= 8: score += 5
    
    # 健康上涨 (0-10分) - 新增因子
    if healthy_uptrend == 1: score += 10
    
    # RSI (0-10分)
    if 40 <= rsi6 <= 70: score += 10
    elif 30 <= rsi6 < 40 or 70 < rsi6 <= 75: score += 5
    
    return {
        'consec': consec, 'score': score, 'chg5': chg5, 'chg10': chg10,
        'vol_ratio': vol_ratio, 'shrink': shrink, 'rsi6': rsi6,
        'vcp': vcp, 'ma_dev': ma_dev, 'healthy': healthy_uptrend
    }

def pick_v89():
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
        
        f = calc_v89_score(klines)
        
        # V89条件：连涨>=3 + 评分>=75
        if f['consec'] < 3: continue
        if f['score'] < 75: continue
        
        today_chg = (klines[-1][2]/klines[-1][1]-1)*100
        if today_chg >= 9.5: continue
        
        f['code'] = code
        f['price'] = price
        f['today_chg'] = today_chg
        candidates.append(f)
    
    conn.close()
    candidates.sort(key=lambda x: -x['score'])
    
    print("=" * 70)
    print("V89 多因子融合策略选股")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    print("V89新增因子:")
    print("  - VCP波动率收缩 (15分)")
    print("  - MA20偏离率 (10分)")
    print("  - 健康上涨量价背离 (10分)")
    print("  - 缩量确认加权提高 (25分)")
    print()
    print(f"信号数: {len(candidates)}")
    print()
    
    for i, c in enumerate(candidates[:5]):
        print(f"{i+1}. {c['code']} | {c['price']:.2f}元 | 评分:{c['score']}")
        print(f"   连涨:{c['consec']}天 | 5日:{c['chg5']:+.1f}% | 10日:{c['chg10']:+.1f}%")
        print(f"   缩量:{'是' if c['shrink'] else '否'} | VCP:{'是' if c['vcp'] else '否'} | 健康:{'是' if c['healthy'] else '否'} | MA偏离:{c['ma_dev']:+.1f}%")
        print()
    
    return candidates

if __name__ == '__main__':
    pick_v89()