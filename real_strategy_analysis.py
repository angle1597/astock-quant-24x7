import sqlite3
import json
from collections import defaultdict

conn = sqlite3.connect('data/stocks.db')
cur = conn.cursor()

# Load all kline data
cur.execute("SELECT code, date, open, high, low, close, volume, turnover FROM kline ORDER BY code, date")
rows = cur.fetchall()
print(f"Total kline rows: {len(rows)}")

# Build per-stock history
stock_data = defaultdict(list)
for row in rows:
    code, date, open_, high, low, close, volume, turnover = row
    stock_data[code].append({
        'date': date,
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
        'turnover': turnover
    })

# Sort each stock by date
for code in stock_data:
    stock_data[code].sort(key=lambda x: x['date'])

print(f"Total stocks: {len(stock_data)}")

# For each stock, find all windows where 5-day return > 20%
big_movers = []  # records of: code, start_date, end_date, start_price, end_price, pct_change

for code, bars in stock_data.items():
    if len(bars) < 6:
        continue
    for i in range(len(bars) - 5):
        window = bars[i:i+6]  # day 0 to day 5 (inclusive = 6 days, but 5 calendar days from start to end)
        start_close = window[0]['close']
        # max high in next 5 days
        max_high = max(b['high'] for b in window[1:])
        # ending close (day 5)
        end_close = window[-1]['close']
        
        # Check if it hit 20% at any point in next 5 days
        hit_20 = max_high >= start_close * 1.20
        
        if hit_20:
            # Find the day it first hit 20%
            hit_day = None
            for j in range(1, 6):
                if window[j]['high'] >= start_close * 1.20:
                    hit_day = j
                    break
            
            pct_change = (max_high - start_close) / start_close * 100
            big_movers.append({
                'code': code,
                'start_date': window[0]['date'],
                'hit_date': window[hit_day]['date'] if hit_day else window[-1]['date'],
                'start_price': start_close,
                'peak_price': max_high,
                'end_price': end_close,
                'pct_change': pct_change,
                'hit_day': hit_day if hit_day else 5
            })

print(f"\nFound {len(big_movers)} instances of stocks hitting 20%+ within 5 days")

# Now analyze characteristics BEFORE the big move
# For each big mover, look at the 5 days BEFORE the start date
characteristics = []

for bm in big_movers:
    code = bm['code']
    start_date = bm['start_date']
    bars = stock_data[code]
    
    # Find the index of start_date
    idx_map = {b['date']: i for i, b in enumerate(bars)}
    if start_date not in idx_map:
        continue
    start_idx = idx_map[start_date]
    
    # Need at least 5 days before
    if start_idx < 5:
        continue
    
    pre5 = bars[start_idx-5:start_idx]  # 5 days before (day -5 to -1)
    pre1 = bars[start_idx-1]  # day before
    
    # Pre-move stats
    pre5_closes = [b['close'] for b in pre5]
    pre5_volumes = [b['volume'] for b in pre5]
    
    # 5-day return before the move
    pre5_return = (pre1['close'] - pre5[0]['open']) / pre5[0]['open'] * 100
    
    # Day before return
    d1_return = (pre1['close'] - bars[start_idx-2]['close']) / bars[start_idx-2]['close'] * 100
    
    # Average volume in pre-5 days
    avg_vol_pre5 = sum(pre5_volumes) / len(pre5_volumes)
    
    # Volume on day before
    vol_pre1 = pre1['volume']
    
    # Price level at start
    start_price = bm['start_price']
    
    # Check if it was already up a lot recently (prev 10 days)
    if start_idx >= 10:
        prev10_start = bars[start_idx-10]
        prev10_return = (pre1['close'] - prev10_start['open']) / prev10_start['open'] * 100
    else:
        prev10_return = 0
    
    characteristics.append({
        'code': code,
        'start_date': start_date,
        'start_price': start_price,
        'pre1_close': pre1['close'],
        'pre1_return': d1_return,
        'pre5_return': pre5_return,
        'prev10_return': prev10_return,
        'avg_vol_pre5': avg_vol_pre5,
        'vol_pre1': vol_pre1,
        'pct_change': bm['pct_change'],
        'hit_day': bm['hit_day']
    })

print(f"Collected characteristics for {len(characteristics)} big movers")

# Analyze distributions
import statistics

if characteristics:
    pre1_returns = [c['pre1_return'] for c in characteristics]
    pre5_returns = [c['pre5_return'] for c in characteristics]
    prev10_returns = [c['prev10_return'] for c in characteristics]
    prices = [c['start_price'] for c in characteristics]
    pcts = [c['pct_change'] for c in characteristics]
    hit_days = [c['hit_day'] for c in characteristics]
    
    print("\n=== CHARACTERISTICS OF REAL BIG MOVERS (>20% in 5 days) ===")
    print(f"Total cases analyzed: {len(characteristics)}")
    print(f"\nDay-before return (%):")
    print(f"  Mean: {statistics.mean(pre1_returns):.2f}%")
    print(f"  Median: {statistics.median(pre1_returns):.2f}%")
    print(f"  StdDev: {statistics.stdev(pre1_returns):.2f}%")
    print(f"  Min: {min(pre1_returns):.2f}%")
    print(f"  Max: {max(pre1_returns):.2f}%")
    print(f"  P25: {sorted(pre1_returns)[int(len(pre1_returns)*0.25)]:.2f}%")
    print(f"  P75: {sorted(pre1_returns)[int(len(pre1_returns)*0.75)]:.2f}%")
    
    print(f"\n5-day pre-return (%):")
    print(f"  Mean: {statistics.mean(pre5_returns):.2f}%")
    print(f"  Median: {statistics.median(pre5_returns):.2f}%")
    print(f"  StdDev: {statistics.stdev(pre5_returns):.2f}%")
    
    print(f"\n10-day pre-return (%):")
    print(f"  Mean: {statistics.mean(prev10_returns):.2f}%")
    print(f"  Median: {statistics.median(prev10_returns):.2f}%")
    
    print(f"\nStart price:")
    print(f"  Mean: {statistics.mean(prices):.2f}")
    print(f"  Median: {statistics.median(prices):.2f}")
    print(f"  Min: {min(prices):.2f}")
    print(f"  Max: {max(prices):.2f}")
    
    print(f"\nActual 5-day peak gain (%):")
    print(f"  Mean: {statistics.mean(pcts):.2f}%")
    print(f"  Median: {statistics.median(pcts):.2f}%")
    
    print(f"\nWhen did it first hit 20%? (days after entry)")
    print(f"  Mean: {statistics.mean(hit_days):.2f}")
    print(f"  Median: {statistics.median(hit_days):.2f}")
    for d in range(1, 6):
        cnt = sum(1 for h in hit_days if h == d)
        print(f"  Day {d}: {cnt} ({cnt/len(hit_days)*100:.1f}%)")

# Save characteristics for further analysis
with open('big_mover_characteristics.json', 'w') as f:
    json.dump(characteristics, f, indent=2, ensure_ascii=False)
print("\nSaved to big_mover_characteristics.json")
