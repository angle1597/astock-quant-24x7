# -*- coding: utf-8 -*-
"""
优化策略 - 目标达标率20%+
增加量比因子、连涨因子
"""
import sys, sqlite3, numpy as np, pandas as pd, time, requests
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'

# ============================================================
# Step 1: 收集更多数据
# ============================================================
print("=" * 60)
print("Step 1: Collecting more K-line data...")
print("=" * 60)

conn = sqlite3.connect(DB)
df_quotes = pd.read_sql(
    '''SELECT code, name, price, change, turnover, amount
       FROM realtime_quote
       WHERE code NOT LIKE '688%' AND code NOT LIKE '300%'
       AND code NOT LIKE '8%' AND name NOT LIKE '%ST%'
       AND name NOT LIKE '%退%' ''', conn)
conn.close()

candidates = df_quotes.to_dict('records')

# Check existing data
conn = sqlite3.connect(DB)
existing = pd.read_sql('SELECT code, COUNT(*) as cnt FROM kline GROUP BY code', conn)
existing_dict = dict(zip(existing['code'], existing['cnt']))
conn.close()

need_collect = [(c['code'], c['name'], existing_dict.get(c['code'], 0)) 
                for c in candidates if existing_dict.get(c['code'], 0) < 100]
need_collect.sort(key=lambda x: x[2])

print(f"Need to collect: {len(need_collect)} stocks")

def collect_sina(code, days=200):
    market = 'sh' if code.startswith('6') else 'sz'
    url = (f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php'
           f'/CN_MarketData.getKLineData')
    params = {'symbol': f'{market}{code}', 'scale': 240, 'ma': 'no', 'datalen': days}
    try:
        r = requests.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        data = r.json()
        if data and isinstance(data, list) and len(data) > 10:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            count = 0
            for d in data:
                try:
                    c.execute('''INSERT OR IGNORE INTO kline
                        (code,date,open,close,high,low,volume,turnover)
                        VALUES (?,?,?,?,?,?,?,?)''',
                        (code, d['day'], float(d['open']), float(d['close']),
                         float(d['high']), float(d['low']), float(d['volume']), 0))
                    count += 1
                except:
                    pass
            conn.commit()
            conn.close()
            return count
    except:
        pass
    return 0

# Collect top 50
collected = []
for code, name, old_cnt in need_collect[:50]:
    n = collect_sina(code, 200)
    if n > old_cnt:
        collected.append((code, name, old_cnt, old_cnt + n))
        print(f"  {code} {name}: {old_cnt} -> {old_cnt+n}")
    time.sleep(0.15)

# Update count
conn = sqlite3.connect(DB)
total_stocks = pd.read_sql('SELECT COUNT(DISTINCT code) as cnt FROM kline', conn)['cnt'][0]
total_klines = pd.read_sql('SELECT COUNT(*) as cnt FROM kline', conn)['cnt'][0]
codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
conn.close()

print(f"\nTotal: {total_stocks} stocks, {total_klines} k-lines")
print(f"Collected this run: {len(collected)}")

# ============================================================
# Step 2: Enhanced backtest with volume ratio
# ============================================================
print("\n" + "=" * 60)
print("Step 2: Enhanced backtest with volume ratio...")
print("=" * 60)

results = []
for holding in [3, 5, 7, 10]:
    for chg_min, chg_max in [(2, 5), (3, 7), (3, 10), (4, 10), (5, 10)]:
        for pmax in [12, 15, 18, 20]:
            for vol_ratio_min in [1.0, 1.5, 2.0]:
                trades = []
                for code in codes:
                    conn = sqlite3.connect(DB)
                    df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
                    conn.close()
                    if df is None or len(df) < 40:
                        continue
                    
                    df = df.tail(130).reset_index(drop=True)
                    df['vol_ma5'] = df['volume'].rolling(5).mean()
                    df['vol_ratio'] = df['volume'] / df['vol_ma5']
                    
                    for i in range(20, len(df)-holding-1):
                        row, prev = df.iloc[i], df.iloc[i-1]
                        chg = (row['close']-prev['close'])/prev['close']*100 if prev['close']>0 else 0
                        vol_ratio = row['vol_ratio'] if not pd.isna(row['vol_ratio']) else 1
                        
                        if chg_min <= chg <= chg_max and 3 <= row['close'] <= pmax and vol_ratio >= vol_ratio_min:
                            buy = row['close']
                            future = df.iloc[i+1:i+holding+1]['close'].tolist()
                            if future:
                                pnl_max = (max(future)-buy)/buy*100
                                pnl_final = (future[-1]-buy)/buy*100
                                trades.append({
                                    'pnl_max': pnl_max, 
                                    'pnl_final': pnl_final,
                                    'vol_ratio': vol_ratio,
                                    'chg': chg
                                })
                
                if len(trades) >= 10:
                    pnls_max = [t['pnl_max'] for t in trades]
                    pnls_final = [t['pnl_final'] for t in trades]
                    targets_30 = sum(1 for p in pnls_max if p >= 30)
                    targets_20 = sum(1 for p in pnls_max if p >= 20)
                    targets_10 = sum(1 for p in pnls_max if p >= 10)
                    wins = sum(1 for p in pnls_final if p > 0)
                    
                    results.append({
                        'hold': holding, 'chg': f'{chg_min}-{chg_max}', 
                        'pmax': pmax, 'vol': vol_ratio_min,
                        'n': len(trades), 
                        'win': wins/len(trades)*100,
                        'avg': np.mean(pnls_max), 
                        'max': max(pnls_max),
                        'r30': targets_30/len(trades)*100, 
                        'r20': targets_20/len(trades)*100,
                        'r10': targets_10/len(trades)*100
                    })

results.sort(key=lambda x: (x['r30'], x['avg']), reverse=True)

print(f'\nTOP 15 strategies (by 30% target rate):')
print(f"{'#':^3} {'hold':^4} {'chg':^8} {'pmax':^5} {'vol':^4} {'n':^5} {'win%':^6} {'avg%':^6} {'max%':^6} {'30%':^6} {'20%':^6}")
print("-" * 80)
for i, r in enumerate(results[:15], 1):
    print(f"{i:^3} {r['hold']:^4} {r['chg']:^8} {r['pmax']:^5} {r['vol']:^4.1f} {r['n']:^5} "
          f"{r['win']:^6.1f} {r['avg']:^6.1f} {r['max']:^6.1f} {r['r30']:^6.1f} {r['r20']:^6.1f}")

# ============================================================
# Step 3: Tomorrow picks
# ============================================================
print("\n" + "=" * 60)
print("Step 3: Tomorrow picks...")
print("=" * 60)

best = results[0] if results else None
if best:
    chg_parts = best['chg'].split('-')
    chg_min, chg_max = float(chg_parts[0]), float(chg_parts[1])
    pmax = best['pmax']
    vol_min = best['vol']
else:
    chg_min, chg_max, pmax, vol_min = 3, 7, 15, 1.5

picks = []
for s in candidates:
    try:
        price = float(s['price']) if s['price'] else 0
        change = float(s['change']) if s['change'] else 0
        amount = float(s['amount'])/1e8 if s['amount'] else 0
        
        if price <= 0 or change <= 0:
            continue
        
        score = 0
        reasons = []
        
        # Price condition
        if 3 <= price <= pmax:
            score += 30
            reasons.append(f"price={price:.1f}")
        
        # Change condition
        if chg_min <= change <= chg_max:
            score += 40
            reasons.append(f"chg={change:.1f}%")
        elif change > chg_max and change < 9.5:
            score += 25
            reasons.append(f"strong+{change:.1f}%")
        
        # Amount
        if amount >= 3:
            score += 20
            reasons.append(f"amt={amount:.1f}B")
        
        # Near limit up
        if change >= 9:
            score += 30
            reasons.append("near_limit")
        elif change >= 7:
            score += 15
            reasons.append("strong")
        
        # Low price bonus
        if 3 <= price <= 10:
            score += 15
            reasons.append("low_price")
        
        # Hot themes
        hot = ['energy', 'power', 'AI', 'military', 'chip', 'lithium', 'EV', 'solar']
        name = s['name']
        if any(kw in name for kw in ['能源', '电力', 'AI', '军工', '芯片', '锂', '汽车', '光伏']):
            score += 10
            reasons.append("hot_theme")
        
        if score >= 50:
            picks.append({
                'code': s['code'], 'name': name,
                'price': price, 'change': change,
                'amount': amount, 'score': score,
                'reasons': ', '.join(reasons[:3])
            })
    except:
        pass

picks.sort(key=lambda x: x['score'], reverse=True)

print(f"\nTomorrow picks ({len(picks)} stocks with score>=50):")
print(f"{'#':^3} {'code':^8} {'name':^10} {'price':^7} {'chg%':^7} {'amt':^6} {'score':^5} {'reasons':<25}")
print("-" * 85)
for i, p in enumerate(picks[:15], 1):
    print(f"{i:^3} {p['code']:^8} {p['name']:^10} {p['price']:^7.2f} {p['change']:>+6.1f}% "
          f"{p['amount']:^6.1f} {p['score']:^5} {p['reasons'][:25]}")

# ============================================================
# Report
# ============================================================
print("\n" + "=" * 60)
print("REPORT")
print("=" * 60)
print(f"- Total stocks: {total_stocks}")
print(f"- Total k-lines: {total_klines}")
print(f"- Collected this run: {len(collected)}")
if best:
    print(f"- Best strategy: hold={best['hold']}d chg={best['chg']}% price<={best['pmax']} vol>={best['vol']}")
    print(f"  Win rate: {best['win']:.1f}%")
    print(f"  30% target rate: {best['r30']:.1f}%")
    print(f"  20% target rate: {best['r20']:.1f}%")
    print(f"  10% target rate: {best['r10']:.1f}%")
    print(f"  Avg max gain: {best['avg']:.1f}%")
    print(f"  Max gain: {best['max']:.1f}%")
if picks:
    p = picks[0]
    print(f"- Top pick: {p['code']} {p['name']} score={p['score']}")
print("=" * 60)
