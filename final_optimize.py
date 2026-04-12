# -*- coding: utf-8 -*-
"""
最终优化版 - 选出明日涨停股票
"""
import sys, sqlite3, numpy as np, pandas as pd, json
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'

# ============================================================
# Step 1: 当前数据库状态
# ============================================================
conn = sqlite3.connect(DB)
total_stocks = pd.read_sql('SELECT COUNT(DISTINCT code) as cnt FROM kline', conn)['cnt'][0]
total_klines = pd.read_sql('SELECT COUNT(*) as cnt FROM kline', conn)['cnt'][0]
codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
conn.close()

print(f"=" * 60)
print(f"Database: {total_stocks} stocks, {total_klines} k-lines")
print(f"=" * 60)

# ============================================================
# Step 2: 深度优化回测
# ============================================================
print(f"\nRunning deep backtest...")

all_results = []
for holding in [5, 7, 10, 14]:
    for chg_min, chg_max in [(2, 5), (3, 7), (3, 10), (4, 10), (5, 10)]:
        for pmax in [12, 15, 18, 20]:
            for vol_min in [1.0, 1.3, 1.5, 1.8]:
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
                        vol = row['vol_ratio'] if not pd.isna(row['vol_ratio']) else 1
                        
                        if chg_min <= chg <= chg_max and 3 <= row['close'] <= pmax and vol >= vol_min:
                            buy = row['close']
                            future = df.iloc[i+1:i+holding+1]['close'].tolist()
                            if future:
                                pnl_max = (max(future)-buy)/buy*100
                                pnl_final = (future[-1]-buy)/buy*100
                                trades.append({
                                    'pnl_max': pnl_max,
                                    'pnl_final': pnl_final,
                                    'vol': vol
                                })
                
                if len(trades) >= 10:
                    pnls_max = [t['pnl_max'] for t in trades]
                    pnls_final = [t['pnl_final'] for t in trades]
                    targets_30 = sum(1 for p in pnls_max if p >= 30)
                    targets_20 = sum(1 for p in pnls_max if p >= 20)
                    wins = sum(1 for p in pnls_final if p > 0)
                    
                    all_results.append({
                        'hold': holding,
                        'chg': f'{chg_min}-{chg_max}',
                        'pmax': pmax,
                        'vol': vol_min,
                        'n': len(trades),
                        'win': wins/len(trades)*100,
                        'avg': np.mean(pnls_max),
                        'max': max(pnls_max),
                        'r30': targets_30/len(trades)*100,
                        'r20': targets_20/len(trades)*100
                    })

all_results.sort(key=lambda x: (x['r30'], x['avg']), reverse=True)

print(f"\nTOP 20 strategies (by 30% target rate):")
print(f"{'#':^3} {'hold':^4} {'chg':^8} {'pmax':^5} {'vol':^4} {'n':^5} {'win%':^6} {'avg%':^6} {'max%':^6} {'30%':^6} {'20%':^6}")
print("-" * 75)
for i, r in enumerate(all_results[:20], 1):
    print(f"{i:^3} {r['hold']:^4} {r['chg']:^8} {r['pmax']:^5} {r['vol']:^4.1f} {r['n']:^5} "
          f"{r['win']:^6.1f} {r['avg']:^6.1f} {r['max']:^6.1f} {r['r30']:^6.1f} {r['r20']:^6.1f}")

best = all_results[0] if all_results else None

# ============================================================
# Step 3: 明日涨停预测
# ============================================================
print(f"\n" + "=" * 60)
print(f"Tomorrow's Limit-Up Prediction")
print(f"=" * 60)

# 获取实时行情
conn = sqlite3.connect(DB)
quotes = pd.read_sql(
    '''SELECT code, name, price, change, turnover, amount, mv
       FROM realtime_quote
       WHERE code NOT LIKE '688%' AND code NOT LIKE '300%'
       AND code NOT LIKE '8%' AND name NOT LIKE '%ST%'
       AND name NOT LIKE '%退%' AND change > 0''', conn)
conn.close()

candidates = quotes.to_dict('records')

# 使用最优策略参数
if best:
    chg_parts = best['chg'].split('-')
    chg_min, chg_max = float(chg_parts[0]), float(chg_parts[1])
    pmax = best['pmax']
    vol_min = best['vol']
else:
    chg_min, chg_max, pmax, vol_min = 4, 10, 18, 1.2

picks = []
for s in candidates:
    try:
        price = float(s['price']) if s['price'] else 0
        change = float(s['change']) if s['change'] else 0
        amount = float(s['amount'])/1e8 if s['amount'] else 0
        turnover = float(s['turnover']) if s['turnover'] else 0
        mv = float(s['mv']) if s['mv'] else 0
        
        if price <= 0 or change <= 0:
            continue
        
        score = 0
        factors = []
        
        # 1. 涨幅因子 (符合策略区间加分)
        if chg_min <= change <= chg_max:
            score += 50
            factors.append(f"chg={change:.1f}%")
        elif change >= 9:
            score += 40
            factors.append("near_limit")
        elif change >= 7:
            score += 30
            factors.append(f"strong+{change:.1f}%")
        
        # 2. 价格因子
        if 3 <= price <= pmax:
            score += 30
            factors.append(f"price={price:.1f}")
        elif price <= 25:
            score += 20
        
        # 3. 成交额因子
        if amount >= 5:
            score += 25
            factors.append(f"amt={amount:.1f}B")
        elif amount >= 2:
            score += 15
        
        # 4. 换手率因子
        if turnover >= 8:
            score += 20
            factors.append(f"turn={turnover:.1f}%")
        elif turnover >= 5:
            score += 10
        
        # 5. 涨停板临近 (最关键)
        if change >= 9.5:
            score += 35
            factors.append("LIMIT_UP")
        elif change >= 9:
            score += 25
        
        # 6. 低价股优势
        if 3 <= price <= 10:
            score += 15
            factors.append("low_price")
        
        # 7. 小市值优势
        if 0 < mv < 100:
            score += 10
            factors.append("small_cap")
        
        # 8. 热门题材
        name = s['name']
        hot_themes = ['能源', '电力', '光伏', '新能源', 'AI', '军工', '芯片', '半导体', 
                      '锂电', '储能', '风电', '汽车', '稀土', '医药', '白酒']
        for kw in hot_themes:
            if kw in name:
                score += 10
                factors.append(f"hot:{kw}")
                break
        
        if score >= 60:
            picks.append({
                'code': s['code'],
                'name': name,
                'price': price,
                'change': change,
                'amount': amount,
                'turnover': turnover,
                'score': score,
                'factors': ', '.join(factors[:4])
            })
    except:
        pass

picks.sort(key=lambda x: (x['score'], -x['price']), reverse=True)

print(f"\nTop picks for tomorrow ({len(picks)} stocks, score>=60):")
print(f"{'#':^3} {'code':^8} {'name':^10} {'price':^7} {'chg%':^7} {'amt':^6} {'score':^5} {'factors':<30}")
print("-" * 90)
for i, p in enumerate(picks[:20], 1):
    print(f"{i:^3} {p['code']:^8} {p['name']:^10} {p['price']:^7.2f} {p['change']:>+6.1f}% "
          f"{p['amount']:^6.1f} {p['score']:^5} {p['factors'][:30]}")

# ============================================================
# Step 4: 历史最佳股票
# ============================================================
print(f"\n" + "=" * 60)
print(f"Best Performing Stocks (Historical)")
print(f"=" * 60)

best_stocks = []
for code in codes:
    conn = sqlite3.connect(DB)
    df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
    conn.close()
    
    if df is None or len(df) < 35:
        continue
    
    df = df.tail(100).reset_index(drop=True)
    df['vol_ma5'] = df['volume'].rolling(5).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma5']
    
    max_pnl = 0
    best_date = ''
    best_buy = 0
    
    for i in range(15, len(df)-7):
        row, prev = df.iloc[i], df.iloc[i-1]
        chg = (row['close']-prev['close'])/prev['close']*100 if prev['close']>0 else 0
        vol = row['vol_ratio'] if not pd.isna(row['vol_ratio']) else 1
        
        if 4 <= chg <= 10 and 3 <= row['close'] <= 18 and vol >= 1.2:
            buy = row['close']
            future = df.iloc[i+1:i+8]['close'].tolist()
            if future:
                pnl = (max(future)-buy)/buy*100
                if pnl > max_pnl:
                    max_pnl = pnl
                    best_date = row['date']
                    best_buy = buy
    
    if max_pnl > 15:
        best_stocks.append((code, max_pnl, best_date, best_buy))

best_stocks.sort(key=lambda x: x[1], reverse=True)

print(f"\nTop 15 stocks by max weekly gain:")
print(f"{'#':^3} {'code':^8} {'max_gain%':^10} {'date':^12} {'buy_price':^10}")
print("-" * 50)
for i, (code, pnl, date, buy) in enumerate(best_stocks[:15], 1):
    print(f"{i:^3} {code:^8} {pnl:^10.1f} {date:^12} {buy:^10.2f}")

# ============================================================
# 保存结果
# ============================================================
output = {
    'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
    'total_stocks': total_stocks,
    'total_klines': total_klines,
    'best_strategy': {
        'holding': best['hold'] if best else 0,
        'buy_chg': best['chg'] if best else 'N/A',
        'price_max': best['pmax'] if best else 0,
        'vol_ratio': best['vol'] if best else 0,
        'win_rate': round(best['win'], 1) if best else 0,
        'avg_max_pnl': round(best['avg'], 1) if best else 0,
        'max_pnl': round(best['max'], 1) if best else 0,
        'target_30_rate': round(best['r30'], 1) if best else 0,
        'target_20_rate': round(best['r20'], 1) if best else 0,
    },
    'tomorrow_picks': picks[:30],
    'best_stocks_history': [{
        'code': c, 'max_pnl': round(p, 1), 'date': d, 'buy_price': round(b, 2)
    } for c, p, d, b in best_stocks[:30]]
}

with open('data/optimize_v2_results.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

# ============================================================
# 最终汇报
# ============================================================
print(f"\n" + "=" * 60)
print(f"FINAL REPORT")
print(f"=" * 60)
print(f"- Data: {total_stocks} stocks, {total_klines} k-lines")
if best:
    print(f"- Best strategy: hold {best['hold']}d, buy at {best['chg']}% change, price <= {best['pmax']}, vol >= {best['vol']}")
    print(f"- Win rate: {best['win']:.1f}%")
    print(f"- Target 30% rate: {best['r30']:.1f}%")
    print(f"- Target 20% rate: {best['r20']:.1f}%")
    print(f"- Avg max gain: {best['avg']:.1f}%")
    print(f"- Max gain: {best['max']:.1f}%")

if picks:
    print(f"\n- TOP 5 PICKS FOR TOMORROW:")
    for i, p in enumerate(picks[:5], 1):
        print(f"  {i}. {p['code']} {p['name']} @ {p['price']:.2f} chg={p['change']:+.1f}% score={p['score']}")

if best_stocks:
    print(f"\n- TOP 5 HISTORICAL PERFORMERS:")
    for i, (c, p, d, b) in enumerate(best_stocks[:5], 1):
        print(f"  {i}. {c} max gain={p:.1f}% on {d}")

print(f"\n" + "=" * 60)
