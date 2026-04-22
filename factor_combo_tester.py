# -*- coding: utf-8 -*-
"""高效因子组合测试器 - Step 2: 快速测试所有组合"""
import sqlite3, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("=" * 70)
print("STEP 2: Fast Factor Combination Tester")
print("=" * 70)

DB = 'data/stocks.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# 预加载所有数据
print("Loading data...")
all_data = []
stocks = cur.execute("SELECT DISTINCT code FROM kline WHERE code LIKE '000%' OR code LIKE '001%' OR code LIKE '002%' OR code LIKE '003%' OR code LIKE '600%' OR code LIKE '601%' OR code LIKE '603%'").fetchall()

for si, (code,) in enumerate(stocks):
    klines = cur.execute('SELECT date,open,close,high,low,volume FROM kline WHERE code=? ORDER BY date', (code,)).fetchall()
    if len(klines) < 30: continue
    
    for i in range(20, len(klines) - 60):
        window = klines[max(0,i-29):i+1]
        buy_day = klines[i]
        sell_day = klines[min(i+60, len(klines)-1)]
        
        closes = [float(k[2]) for k in window]
        volumes = [float(k[5]) for k in window]
        highs = [float(k[3]) for k in window]
        lows = [float(k[4]) for k in window]
        n = len(closes)
        
        price = closes[-1]
        if price >= 10: continue
        
        # 连涨天数
        consec = 0
        for j in range(n-1, 0, -1):
            if closes[j] > closes[j-1]: consec += 1
            else: break
        
        # 涨幅
        chg5 = (closes[-1]/closes[-6]-1)*100 if n>=6 else 0
        chg10 = (closes[-1]/closes[-11]-1)*100 if n>=11 else 0
        
        # 量比
        avg_vol = sum(volumes[-6:-1])/5 if n>=6 else 1
        vol_ratio = volumes[-1]/avg_vol if avg_vol>0 else 1
        
        # 缩量
        shrink = 1
        for vi in range(n-1, n-consec-1, -1):
            if vi < 1: break
            if volumes[vi] >= volumes[vi-1]: shrink = 0; break
        
        # RSI
        gains=losses=0
        for j in range(n-6, n):
            d=closes[j]-closes[j-1]
            if d>0: gains+=d
            else: losses+=abs(d)
        rsi = 100-100/(1+gains/losses) if losses>0 else 100
        
        # 振幅
        rr = max(closes[-5:]) - min(closes[-5:])
        pr = max(closes[-10:-5]) - min(closes[-10:-5]) if n>=10 else 0
        range_shrink = 1 if pr>0 and rr/pr<0.8 else 0
        
        # MA偏离
        ma20 = sum(closes[-20:])/20 if n>=20 else closes[-1]
        ma_dev = (closes[-1]/ma20-1)*100 if ma20>0 else 0
        
        # 收益率
        buy_p = float(buy_day[2])
        sell_p = float(sell_day[2])
        min_low = min(float(k[4]) for k in klines[i:i+61])
        if min_low <= buy_p * 0.93: continue  # 止损
        ret = (sell_p/buy_p-1)*100
        
        all_data.append({
            'consec': consec,
            'chg5': chg5,
            'chg10': chg10,
            'vol_ratio': vol_ratio,
            'shrink': shrink,
            'rsi': rsi,
            'range_shrink': range_shrink,
            'ma_dev': ma_dev,
            'ret': ret
        })
    
    if (si+1) % 500 == 0:
        print(f"  Loaded {si+1}/{len(stocks)} stocks...")

print(f"Total samples: {len(all_data)}")
print()

# 测试函数
def test_condition(cond_str, cond_func):
    total = good10 = good30 = wins = 0
    rets = []
    for d in all_data:
        if cond_func(d):
            total += 1
            if d['ret'] >= 10: good10 += 1
            if d['ret'] >= 30: good30 += 1
            if d['ret'] > 0: wins += 1
            rets.append(d['ret'])
    if total == 0: return None
    avg_r = sum(rets)/len(rets)
    return {
        'name': cond_str,
        'n': total,
        '10pct': good10/total*100,
        '30pct': good30/total*100,
        'avg': avg_r,
        'win': wins/total*100
    }

# 因子组合测试
print("Testing factor combinations...")
print()

results = []

# 1. 基准测试
tests = [
    # 基准
    ("consec>=3", lambda d: d['consec']>=3),
    ("consec>=4", lambda d: d['consec']>=4),
    ("consec>=5", lambda d: d['consec']>=5),
    
    # 缩量
    ("consec>=3 + shrink", lambda d: d['consec']>=3 and d['shrink']),
    ("consec>=4 + shrink", lambda d: d['consec']>=4 and d['shrink']),
    ("consec>=3 + vol<0.6", lambda d: d['consec']>=3 and d['vol_ratio']<0.6),
    
    # 组合
    ("consec>=4 + shrink + range_shrink", lambda d: d['consec']>=4 and d['shrink'] and d['range_shrink']),
    ("consec>=3 + shrink + range_shrink", lambda d: d['consec']>=3 and d['shrink'] and d['range_shrink']),
    ("consec>=3 + vol<0.6 + range_shrink", lambda d: d['consec']>=3 and d['vol_ratio']<0.6 and d['range_shrink']),
    
    # RSI过滤
    ("consec>=3 + shrink + rsi<80", lambda d: d['consec']>=3 and d['shrink'] and d['rsi']<80),
    ("consec>=4 + shrink + rsi<80", lambda d: d['consec']>=4 and d['shrink'] and d['rsi']<80),
    ("consec>=3 + shrink + 30<rsi<80", lambda d: d['consec']>=3 and d['shrink'] and 30<d['rsi']<80),
    
    # 涨幅过滤
    ("consec>=3 + shrink + chg5<10", lambda d: d['consec']>=3 and d['shrink'] and d['chg5']<10),
    ("consec>=3 + shrink + chg5<15", lambda d: d['consec']>=3 and d['shrink'] and d['chg5']<15),
    ("consec>=3 + shrink + chg10<15", lambda d: d['consec']>=3 and d['shrink'] and d['chg10']<15),
    
    # MA偏离
    ("consec>=3 + shrink + ma_dev<5", lambda d: d['consec']>=3 and d['shrink'] and d['ma_dev']<5),
    ("consec>=4 + shrink + ma_dev<5", lambda d: d['consec']>=4 and d['shrink'] and d['ma_dev']<5),
    
    # 多重组合
    ("3+shr+RS+rsi", lambda d: d['consec']>=3 and d['shrink'] and d['range_shrink'] and d['rsi']<80),
    ("4+shr+RS+rsi", lambda d: d['consec']>=4 and d['shrink'] and d['range_shrink'] and d['rsi']<80),
    ("3+shr+vol+RS", lambda d: d['consec']>=3 and d['vol_ratio']<0.6 and d['range_shrink']),
    
    # 最优组合
    ("3+shr+RS+rsi+chg5<10", lambda d: d['consec']>=3 and d['shrink'] and d['range_shrink'] and d['rsi']<80 and d['chg5']<10),
    ("4+shr+RS+rsi+chg5<10", lambda d: d['consec']>=4 and d['shrink'] and d['range_shrink'] and d['rsi']<80 and d['chg5']<10),
]

for name, cond in tests:
    r = test_condition(name, cond)
    if r:
        results.append(r)

# 排序并显示
results.sort(key=lambda x: -x['10pct'])
print("TOP 10 BY 10% RATE:")
print("-" * 70)
for i, r in enumerate(results[:10]):
    marker = " <-- BEST" if i == 0 else ""
    print(f"{i+1:2d}. {r['name']:30s} n={r['n']:5d} 10%={r['10pct']:5.1f}% 30%={r['30pct']:5.1f}% avg={r['avg']:6.2f}% win={r['win']:5.1f}%{marker}")

results.sort(key=lambda x: -x['30pct'])
print("\nTOP 10 BY 30% RATE:")
print("-" * 70)
for i, r in enumerate(results[:10]):
    marker = " <-- BEST" if i == 0 else ""
    print(f"{i+1:2d}. {r['name']:30s} n={r['n']:5d} 10%={r['10pct']:5.1f}% 30%={r['30pct']:5.1f}% avg={r['avg']:6.2f}% win={r['win']:5.1f}%{marker}")

results.sort(key=lambda x: -x['win'])
print("\nTOP 10 BY WIN RATE:")
print("-" * 70)
for i, r in enumerate(results[:10]):
    marker = " <-- BEST" if i == 0 else ""
    print(f"{i+1:2d}. {r['name']:30s} n={r['n']:5d} 10%={r['10pct']:5.1f}% 30%={r['30pct']:5.1f}% avg={r['avg']:6.2f}% win={r['win']:5.1f}%{marker}")

conn.close()
print("\n" + "=" * 70)
