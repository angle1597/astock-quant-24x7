import sqlite3
import json
import statistics
from collections import defaultdict

conn = sqlite3.connect('data/stocks.db')
cur = conn.cursor()

cur.execute("SELECT code, date, open, high, low, close, volume, turnover FROM kline ORDER BY code, date")
rows = cur.fetchall()

stock_data = defaultdict(list)
for row in rows:
    code, date, open_, high, low, close, volume, turnover = row
    stock_data[code].append({
        'date': date, 'open': open_, 'high': high, 'low': low,
        'close': close, 'volume': volume, 'turnover': turnover
    })

for code in stock_data:
    stock_data[code].sort(key=lambda x: x['date'])

# Collect characteristics including volume
characteristics = []

for code, bars in stock_data.items():
    if len(bars) < 11:
        continue
    for i in range(5, len(bars) - 5):
        start_close = bars[i]['close']
        window = bars[i:i+6]
        max_high = max(b['high'] for b in window[1:])
        hit_20 = max_high >= start_close * 1.20
        
        if not hit_20:
            continue
        
        peak_pct = (max_high - start_close) / start_close * 100
        
        # Find hit day
        hit_day = None
        for j in range(1, 6):
            if window[j]['high'] >= start_close * 1.20:
                hit_day = j
                break
        
        pre1 = bars[i-1]
        pre5 = bars[i-5:i]
        pre20_bars = bars[max(0, i-20):i] if i >= 20 else bars[:i]
        
        d1_ret = (pre1['close'] - bars[i-2]['close']) / bars[i-2]['close'] * 100
        pre5_ret = (pre1['close'] - bars[i-5]['open']) / bars[i-5]['open'] * 100
        
        # Volume analysis
        avg_vol_pre5 = statistics.mean([b['volume'] for b in pre5])
        vol_pre1 = pre1['volume']
        vol_ratio = vol_pre1 / avg_vol_pre5 if avg_vol_pre5 > 0 else 0
        
        # Volume trend (is volume increasing?)
        if len(pre5) >= 3:
            vol_trend = (pre5[-1]['volume'] - pre5[0]['volume']) / pre5[0]['volume'] if pre5[0]['volume'] > 0 else 0
        else:
            vol_trend = 0
        
        # Price range
        price = start_close
        
        # Max drawdown in pre5 days
        pre5_lows = [b['low'] for b in pre5]
        pre5_highs = [b['high'] for b in pre5]
        max_drawdown_pre = min((pre5_lows[j] - pre5_highs[j-1]) / pre5_highs[j-1] * 100 
                                for j in range(1, len(pre5)) if pre5_highs[j-1] > 0)
        
        # Was it already up a lot?
        already_up_10 = pre5_ret > 10
        already_up_15 = pre5_ret > 15
        already_up_5 = pre5_ret > 5
        
        # Was the day before a big green candle?
        d1_green = pre1['close'] > pre1['open']
        d1_body = (pre1['close'] - pre1['open']) / pre1['open'] * 100 if pre1['open'] > 0 else 0
        
        characteristics.append({
            'code': code,
            'start_date': bars[i]['date'],
            'start_price': price,
            'd1_return': d1_ret,
            'pre5_return': pre5_ret,
            'peak_pct': peak_pct,
            'hit_day': hit_day,
            'vol_ratio': vol_ratio,
            'vol_trend': vol_trend,
            'd1_body': d1_body,
            'd1_green': d1_green,
            'already_up_5': already_up_5,
            'already_up_10': already_up_10,
            'max_drawdown_pre': max_drawdown_pre
        })

# Now analyze by different filters
print(f"Total big mover cases: {len(characteristics)}")

# Filter 1: Day-before return distribution
print("\n=== FILTER 1: Day-before return ===")
bins = [(-999, -5), (-5, -2), (-2, 0), (0, 2), (2, 5), (5, 999)]
for lo, hi in bins:
    cases = [c for c in characteristics if lo <= c['d1_return'] < hi]
    if cases:
        avg_hit = sum(1 for c in cases if c['peak_pct'] >= 20) / len(cases) * 100
        print(f"  d1_return {lo:>5} to {hi:>5}: {len(cases):>4} cases, avg peak={statistics.mean([c['peak_pct'] for c in cases]):.1f}%")

# Filter 2: Pre5 return distribution
print("\n=== FILTER 2: 5-day pre-return ===")
bins2 = [(-999, 0), (0, 3), (3, 5), (5, 8), (8, 12), (12, 20), (20, 999)]
for lo, hi in bins2:
    cases = [c for c in characteristics if lo <= c['pre5_return'] < hi]
    if cases:
        print(f"  pre5_return {lo:>5} to {hi:>5}: {len(cases):>4} cases")

# Filter 3: Volume ratio
print("\n=== FILTER 3: Volume ratio (day before / avg 5-day) ===")
vol_bins = [(0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 999)]
for lo, hi in vol_bins:
    cases = [c for c in characteristics if lo <= c['vol_ratio'] < hi]
    if cases:
        avg_hit = statistics.mean([c['peak_pct'] for c in cases])
        print(f"  vol_ratio {lo:>5.1f} to {hi:>5.1f}: {len(cases):>4} cases, avg peak={avg_hit:.1f}%")

# Filter 4: Price range
print("\n=== FILTER 4: Price range ===")
price_bins = [(0, 10), (10, 20), (20, 30), (30, 50), (50, 100), (100, 999)]
for lo, hi in price_bins:
    cases = [c for c in characteristics if lo <= c['start_price'] < hi]
    if cases:
        print(f"  price {lo:>5.1f} to {hi:>5.1f}: {len(cases):>4} cases")

# Cross analysis: best combination
print("\n=== BEST COMBINATIONS ===")

# Combination A: d1_return 0-5% AND pre5_return 3-12% AND vol_ratio 1-3
combo_a = [c for c in characteristics if 0 <= c['d1_return'] < 5 and 3 <= c['pre5_return'] < 12 and 1.0 <= c['vol_ratio'] < 3]
print(f"A: d1 0-5% + pre5 3-12% + vol 1-3x: {len(combo_a)} cases")

# Combination B: d1_return 1-4% AND pre5_return 5-10% AND vol_ratio >1.5
combo_b = [c for c in characteristics if 1 <= c['d1_return'] < 4 and 5 <= c['pre5_return'] < 10 and c['vol_ratio'] > 1.5]
print(f"B: d1 1-4% + pre5 5-10% + vol >1.5x: {len(combo_b)} cases")

# Combination C: tight pre5 range 3-8% + d1 positive + vol increasing
combo_c = [c for c in characteristics if 3 <= c['pre5_return'] < 8 and c['d1_return'] > 0 and c['vol_ratio'] > 1.2]
print(f"C: pre5 3-8% + d1>0 + vol>1.2x: {len(combo_c)} cases")

# Combination D: mild d1 0.5-3% + moderate pre5 3-8%
combo_d = [c for c in characteristics if 0.5 <= c['d1_return'] < 3 and 3 <= c['pre5_return'] < 8]
print(f"D: d1 0.5-3% + pre5 3-8%: {len(combo_d)} cases")

# What's the "sweet spot"?
print("\n=== SWEET SPOT ANALYSIS ===")
for d1_lo, d1_hi in [(0, 2), (0, 3), (0.5, 2), (0.5, 3), (1, 3), (2, 4)]:
    for p5_lo, p5_hi in [(0, 5), (2, 7), (3, 8), (3, 10), (5, 10)]:
        cases = [c for c in characteristics if d1_lo <= c['d1_return'] < d1_hi and p5_lo <= c['pre5_return'] < p5_hi]
        if len(cases) >= 30:
            avg_peak = statistics.mean([c['peak_pct'] for c in cases])
            hit_rate = sum(1 for c in cases if c['hit_day'] <= 2) / len(cases) * 100
            print(f"  d1 {d1_lo}-{d1_hi}% + pre5 {p5_lo}-{p5_hi}%: n={len(cases)}, avg_peak={avg_peak:.1f}%, fast_hit={hit_rate:.1f}%")

# Distribution of pre5 returns for best performers (peak > 25%)
print("\n=== PRE5 RETURN FOR TOP PERFORMERS (peak > 25%) ===")
top_perfs = [c for c in characteristics if c['peak_pct'] >= 25]
if top_perfs:
    p5 = [c['pre5_return'] for c in top_perfs]
    print(f"  Count: {len(top_perfs)}")
    print(f"  Mean pre5: {statistics.mean(p5):.2f}%")
    print(f"  Median pre5: {statistics.median(p5):.2f}%")
    # Distribution
    for lo, hi in [(-999, 0), (0, 3), (3, 5), (5, 8), (8, 12), (12, 20), (20, 999)]:
        cnt = sum(1 for p in p5 if lo <= p < hi)
        if cnt:
            print(f"  pre5 {lo:>5} to {hi:>5}: {cnt} ({cnt/len(top_perfs)*100:.1f}%)")

# Save for later
with open('deep_characteristics.json', 'w') as f:
    json.dump(characteristics, f, indent=2, ensure_ascii=False)
print("\nSaved deep characteristics.")
