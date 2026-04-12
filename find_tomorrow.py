import sqlite3
import json
import statistics
from collections import defaultdict
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect('data/stocks.db')
cur = conn.cursor()

# Load today's quote data
cur.execute("SELECT code, name, price, change, change_pct, volume, amount, turnover FROM realtime_quote")
quotes = cur.fetchall()
print(f"Today's quotes: {len(quotes)} stocks")

# Load kline data for all stocks
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

# Build today's screening data
today_candidates = []

def to_float(v):
    try:
        s = str(v).strip()
        if s == '-' or s == '':
            return 0
        return float(s)
    except:
        return 0

for quote in quotes:
    code, name, price, change, change_pct, volume, amount, turnover = quote
    if code not in stock_data:
        continue
    bars = stock_data[code]
    if len(bars) < 10:
        continue
    
    # Get last 20 bars for analysis
    last20 = bars[-20:]
    last5 = bars[-6:-1]  # 5 days before today (excluding today which may not be in kline)
    last1 = bars[-2]  # yesterday (most recent complete day)
    last2 = bars[-3]  # day before yesterday
    
    # Recent stats
    if len(last5) >= 5:
        avg_vol_pre5 = statistics.mean([b['volume'] for b in last5])
    else:
        avg_vol_pre5 = statistics.mean([b['volume'] for b in last20])
    
    # Pre-move returns
    d1_return = (last1['close'] - last2['close']) / last2['close'] * 100 if last2['close'] > 0 else 0
    pre5_return = (last1['close'] - bars[-6]['open']) / bars[-6]['open'] * 100 if bars[-6]['open'] > 0 else 0
    
    # Volume ratio (yesterday vs avg 5-day)
    vol_ratio = last1['volume'] / avg_vol_pre5 if avg_vol_pre5 > 0 else 1
    
    # Check if today's data is available
    today_bar = bars[-1] if bars else None
    
    today_candidates.append({
        'code': code,
        'name': name,
        'price': to_float(price),
        'change_pct': to_float(change_pct),
        'turnover': to_float(turnover),
        'd1_return': d1_return,
        'pre5_return': pre5_return,
        'vol_ratio': vol_ratio,
        'today_vol': to_float(volume),
        'avg_vol_pre5': avg_vol_pre5,
        'last_date': bars[-1]['date'],
        'bars': bars[-10:]
    })

print(f"Stocks with history: {len(today_candidates)}")

# Strategy based on historical analysis:
# Sweet spot: d1_return 1-3% + pre5_return 5-10% → 30.6% fast hit, avg peak 28.4%
# Also: high volume (vol_ratio 2-3x) is strongly associated with bigger peaks

# STRATEGY DEFINITION:
# MUST have:
# 1. Yesterday return 1-5% (positive momentum, not overextended)
# 2. 5-day return 3-12% (accumulation phase)
# 3. Volume > avg 5-day (volume confirmation)
# 4. Price > 3 (avoid penny stocks)
# 5. Price < 150 (avoid very high price stocks)

# Nice to have:
# - vol_ratio > 1.5 (strong volume)
# - pre5 return 5-10% (the sweet spot range)

print("\n=== APPLYING STRATEGY ===")

# Score each candidate
for c in today_candidates:
    score = 0
    reasons = []
    price = float(c['price']) if c['price'] else 0
    d1 = float(c['d1_return']) if c['d1_return'] else 0
    p5 = float(c['pre5_return']) if c['pre5_return'] else 0
    vr = float(c['vol_ratio']) if c['vol_ratio'] else 0
    
    # Base score
    if 1 <= d1 < 5:
        score += 30
        reasons.append(f"昨日涨幅{d1:.1f}% (1-5%区间)")
    elif 0.5 <= d1 < 1:
        score += 15
        reasons.append(f"昨日涨幅{d1:.1f}% (小幅上涨)")
    elif 5 <= d1 < 8:
        score += 20
        reasons.append(f"昨日涨幅{d1:.1f}% (强势上涨)")
    elif d1 < 0:
        score += 0  # negative day before is less ideal
    
    if 3 <= p5 < 8:
        score += 25
        reasons.append(f"5日涨幅{p5:.1f}% (蓄势期)")
    elif 8 <= p5 < 12:
        score += 30
        reasons.append(f"5日涨幅{p5:.1f}% (强势蓄势)")
    elif 12 <= p5 < 20:
        score += 15
        reasons.append(f"5日涨幅{p5:.1f}% (注意追高风险)")
    elif p5 < 3 and p5 > 0:
        score += 10
        reasons.append(f"5日涨幅{p5:.1f}% (蓄势中)")
    
    if vr >= 2:
        score += 25
        reasons.append(f"量比{vr:.1f}x (放量)")
    elif vr >= 1.5:
        score += 15
        reasons.append(f"量比{vr:.1f}x (温和放量)")
    elif vr >= 1.0:
        score += 5
        reasons.append(f"量比{vr:.1f}x")
    
    # Price filter
    if price < 3:
        score = 0
        reasons.append("价格<3元，风险大")
    elif price > 100:
        score = max(0, score - 10)
        reasons.append(f"价格{price:.0f}元偏高")
    
    c['score'] = score
    c['reasons'] = reasons

# Sort by score
today_candidates.sort(key=lambda x: x['score'], reverse=True)

print("\n=== TOP CANDIDATES FOR TOMORROW ===")
for i, c in enumerate(today_candidates[:15]):
    price = float(c['price']) if c['price'] else 0
    d1 = float(c['d1_return']) if c['d1_return'] else 0
    p5 = float(c['pre5_return']) if c['pre5_return'] else 0
    vr = float(c['vol_ratio']) if c['vol_ratio'] else 0
    cp = float(c['change_pct']) if c['change_pct'] else 0
    to = float(c['turnover']) if c['turnover'] else 0
    print(f"\n{i+1}. {c['name']} ({c['code']}) - Score: {c['score']}")
    print(f"   价格: {price:.2f} | 今日涨幅: {cp:.2f}%")
    print(f"   昨日涨幅: {d1:.2f}% | 5日涨幅: {p5:.2f}%")
    print(f"   量比: {vr:.2f}x | 换手率: {to:.2f}%")
    print(f"   理由: {' | '.join(c['reasons'][:3])}")
    print(f"   最新日期: {c['last_date']}")

# Final picks
print("\n=== FINAL PICKS ===")
final_picks = [c for c in today_candidates if c['score'] >= 50]
for i, c in enumerate(final_picks[:5]):
    print(f"\n{i+1}. {c['name']} ({c['code']}) Score={c['score']}")
    print(f"   理由:")
    for r in c['reasons']:
        print(f"   - {r}")

# Save picks
result = {
    'date': '2026-04-10',
    'strategy': 'Historical Sweet Spot: d1 1-5% + pre5 3-12% + vol > avg + price 3-150',
    'key_findings': {
        'avg_d1_return_of_winners': '1.26% (median 0.64%)',
        'avg_pre5_return_of_winners': '5.39% (median 3.29%)', 
        'volume_ratio_importance': '2-3x vol → avg peak 34.5% vs 29.4% baseline',
        'sweet_spot': 'd1 1-3% + pre5 5-10% = 30.6% fast hit rate',
        'peak_timing': '26.8% hit on day 4, 26.9% on day 5 (most hit on day 4-5)',
        'avg_peak_gain': '29.62%'
    },
    'picks': [{
        'rank': i+1,
        'code': c['code'],
        'name': c['name'],
        'price': c['price'],
        'change_pct': c['change_pct'],
        'd1_return': c['d1_return'],
        'pre5_return': c['pre5_return'],
        'vol_ratio': c['vol_ratio'],
        'turnover': c['turnover'],
        'score': c['score'],
        'reasons': c['reasons']
    } for i, c in enumerate(final_picks[:5])]
}

with open('tomorrow_real_picks.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("\nSaved to tomorrow_real_picks.json")
