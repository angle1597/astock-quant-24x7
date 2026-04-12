# -*- coding: utf-8 -*-
"""
量化选股系统 V11 - 目标优化版
核心目标: 提高达标率(30%周涨幅)到20%+
"""
import os, sys, time, json, sqlite3, requests, numpy as np, pandas as pd
from datetime import datetime, timedelta

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')
DB_PATH = 'data/stocks.db'

# ============================================================
# Step 1: 扩展数据收集
# ============================================================
print("=" * 70)
print("Step 1: 扩展K线数据收集")
print("=" * 70)

# 获取实时行情作为候选
conn = sqlite3.connect(DB_PATH)
df_quotes = pd.read_sql(
    '''SELECT code, name, price, change, turnover, amount, mv
       FROM realtime_quote
       WHERE code NOT LIKE '688%' AND code NOT LIKE '300%'
       AND code NOT LIKE '8%' AND name NOT LIKE '%ST%'
       AND name NOT LIKE '%退%' ''',
    conn)
conn.close()

candidates = df_quotes.to_dict('records')
print(f"候选股票池: {len(candidates)} 只")

# 检查已有数据
conn = sqlite3.connect(DB_PATH)
existing = pd.read_sql('SELECT code, COUNT(*) as cnt FROM kline GROUP BY code', conn)
existing_dict = dict(zip(existing['code'], existing['cnt']))
conn.close()

# 筛选需要收集的股票 (数据少于100条的)
need_collect = []
for c in candidates:
    cnt = existing_dict.get(c['code'], 0)
    if cnt < 100:  # 数据不足100条
        need_collect.append((c['code'], c['name'], cnt))

need_collect.sort(key=lambda x: x[2])  # 按数据量升序
print(f"需要收集: {len(need_collect)} 只")

# 新浪K线API (更稳定)
def collect_sina(code, name, days=200):
    market = 'sh' if code.startswith('6') else 'sz'
    url = (f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php'
           f'/CN_MarketData.getKLineData')
    params = {'symbol': f'{market}{code}', 'scale': 240, 'ma': 'no', 'datalen': days}
    try:
        r = requests.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=12)
        data = r.json()
        if data and isinstance(data, list) and len(data) > 10:
            conn = sqlite3.connect(DB_PATH)
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
    except Exception as e:
        pass
    return 0

# 收集前100只
collected = []
for code, name, old_cnt in need_collect[:100]:
    n = collect_sina(code, name, 200)
    if n > old_cnt:
        collected.append((code, name, old_cnt, old_cnt + n))
        print(f"  {code} {name}: {old_cnt} -> {old_cnt+n}")
    time.sleep(0.2)

print(f"\n收集完成: {len(collected)} 只")

# 统计
conn = sqlite3.connect(DB_PATH)
total_stocks = pd.read_sql('SELECT COUNT(DISTINCT code) as cnt FROM kline', conn)['cnt'][0]
total_klines = pd.read_sql('SELECT COUNT(*) as cnt FROM kline', conn)['cnt'][0]
conn.close()
print(f"数据库总计: {total_stocks} 只股票, {total_klines} 条K线")

# ============================================================
# Step 2: 优化策略回测 - 目标30%周涨幅
# ============================================================
print("\n" + "=" * 70)
print("Step 2: 优化策略回测 - 目标30%周涨幅")
print("=" * 70)

conn = sqlite3.connect(DB_PATH)
codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
conn.close()

code_to_name = {c['code']: c['name'] for c in candidates}

# 扩展参数组合
all_results = []

for holding in [3, 5, 7, 10]:  # 持有天数
    for buy_chg_min, buy_chg_max in [
        (0, 3), (0, 5), (1, 4), (1, 5), (2, 5), (2, 8), 
        (3, 7), (3, 10), (5, 10), (6, 10)
    ]:
        for price_max in [10, 15, 20, 25, 30]:
            for vol_ratio_min in [0, 1.2, 1.5, 2.0]:  # 量比要求
                trades = []
                
                for code in codes:
                    conn = sqlite3.connect(DB_PATH)
                    df = pd.read_sql(
                        'SELECT * FROM kline WHERE code=? ORDER BY date',
                        conn, params=(code,))
                    conn.close()
                    
                    if df is None or len(df) < 40:
                        continue
                    
                    df = df.sort_values('date').tail(150).reset_index(drop=True)
                    
                    # 计算量比
                    df['vol_ma5'] = df['volume'].rolling(5).mean()
                    df['vol_ratio'] = df['volume'] / df['vol_ma5']
                    
                    for i in range(20, len(df) - holding - 1):
                        row = df.iloc[i]
                        prev = df.iloc[i-1]
                        
                        chg = (row['close'] - prev['close']) / prev['close'] * 100 if prev['close'] > 0 else 0
                        vol_ratio = row['vol_ratio'] if not pd.isna(row['vol_ratio']) else 1
                        
                        if (buy_chg_min <= chg <= buy_chg_max and 
                            3 <= row['close'] <= price_max and
                            vol_ratio >= vol_ratio_min):
                            buy = row['close']
                            # 持有期内最高价
                            future_prices = df.iloc[i+1:i+holding+1]['close'].tolist()
                            if future_prices:
                                sell_max = max(future_prices)
                                sell_final = future_prices[-1]
                                pnl_max = (sell_max - buy) / buy * 100 if buy > 0 else 0
                                pnl_final = (sell_final - buy) / buy * 100 if buy > 0 else 0
                                
                                trades.append({
                                    'code': code, 'date': row['date'],
                                    'buy_chg': chg, 'price': buy,
                                    'pnl_max': pnl_max, 'pnl_final': pnl_final,
                                    'vol_ratio': vol_ratio
                                })
                
                if len(trades) < 10:
                    continue
                
                pnls_max = [t['pnl_max'] for t in trades]
                pnls_final = [t['pnl_final'] for t in trades]
                
                targets_30 = sum(1 for p in pnls_max if p >= 30)
                targets_20 = sum(1 for p in pnls_max if p >= 20)
                targets_10 = sum(1 for p in pnls_max if p >= 10)
                wins = sum(1 for p in pnls_final if p > 0)
                
                all_results.append({
                    'holding': holding,
                    'buy_chg': f'{buy_chg_min}-{buy_chg_max}',
                    'price_max': price_max,
                    'vol_ratio_min': vol_ratio_min,
                    'trades': len(trades),
                    'win_rate': wins / len(trades) * 100,
                    'avg_pnl': np.mean(pnls_final),
                    'avg_max_pnl': np.mean(pnls_max),
                    'max_pnl': max(pnls_max),
                    'target_30_rate': targets_30 / len(trades) * 100,
                    'target_20_rate': targets_20 / len(trades) * 100,
                    'target_10_rate': targets_10 / len(trades) * 100,
                    'avg_vol_ratio': np.mean([t['vol_ratio'] for t in trades]),
                })

# 排序 - 按达标率优先
all_results.sort(key=lambda x: (x['target_30_rate'], x['avg_max_pnl']), reverse=True)

print(f"\n共测试 {len(all_results)} 种参数组合")
print("\nTOP 20 策略 (按30%达标率排序):")
print(f"{'#':^3} {'持有':^4} {'买入涨幅':^10} {'价上限':^6} {'量比':^6} {'交易':^5} {'胜率':^8} {'平均最大':^10} {'30%率':^8} {'20%率':^8} {'10%率':^8}")
print("-" * 100)

for i, r in enumerate(all_results[:20], 1):
    print(f"{i:^3} {r['holding']:^4} {r['buy_chg']:^10} {r['price_max']:^6} "
          f"{r['vol_ratio_min']:>5.1f} {r['trades']:^5} {r['win_rate']:>6.1f}% "
          f"{r['avg_max_pnl']:>8.2f}% {r['target_30_rate']:>6.1f}% "
          f"{r['target_20_rate']:>6.1f}% {r['target_10_rate']:>6.1f}%")

best = all_results[0] if all_results else None

# ============================================================
# Step 3: 找出明日有望涨停的股票
# ============================================================
print("\n" + "=" * 70)
print("Step 3: 明日涨停预测")
print("=" * 70)

# 使用最优策略找出当前符合条件的股票
if best:
    chg_parts = best['buy_chg'].split('-')
    chg_min, chg_max = float(chg_parts[0]), float(chg_parts[1])
    pmax = best['price_max']
    vol_min = best['vol_ratio_min']
else:
    chg_min, chg_max, pmax, vol_min = 2, 5, 20, 1.2

tomorrow_picks = []
for s in candidates:
    try:
        price = float(s['price']) if s['price'] else 0
        change = float(s['change']) if s['change'] else 0
        amount = float(s['amount']) / 1e8 if s['amount'] else 0
        turnover = float(s['turnover']) if s['turnover'] else 0
        
        if price <= 0 or change <= 0:
            continue
        
        # 计算评分
        score = 0
        reasons = []
        
        # 1. 涨幅符合条件
        if chg_min <= change <= chg_max:
            score += 40
            reasons.append(f"涨幅{change:.1f}%在{chg_min}-{chg_max}%区间")
        
        # 2. 价格符合条件
        if 3 <= price <= pmax:
            score += 30
            reasons.append(f"价格{price:.2f}元")
        
        # 3. 成交量放大
        if amount >= 3:
            score += 25
            reasons.append(f"成交额{amount:.1f}亿")
        
        # 4. 换手率
        if turnover >= 5:
            score += 15
            reasons.append(f"换手率{turnover:.1f}%")
        
        # 5. 涨停板特征
        if change >= 9.5:
            score += 30
            reasons.append("接近涨停")
        elif change >= 7:
            score += 20
            reasons.append("强势上涨")
        
        # 6. 低价股优势
        if 3 <= price <= 10:
            score += 15
            reasons.append("低价易涨")
        
        # 7. 题材热度
        hot = ['能源', '电力', '光伏', '新能源', 'AI', '军工', '稀土', '农业', '医药', 
               '汽车', '芯片', '半导体', '锂电', '储能', '风电']
        for kw in hot:
            if kw in s['name']:
                score += 10
                reasons.append(f"热门题材:{kw}")
                break
        
        if score >= 50:
            tomorrow_picks.append({
                'code': s['code'], 'name': s['name'],
                'price': price, 'change': change,
                'amount': amount, 'turnover': turnover,
                'score': score, 'reasons': reasons
            })
    except:
        pass

tomorrow_picks.sort(key=lambda x: x['score'], reverse=True)

print(f"\n明日涨停预测 ({len(tomorrow_picks)}只):")
print(f"{'#':^3} {'代码':^8} {'名称':^10} {'现价':^8} {'涨幅%':^8} {'成交亿':^8} {'评分':^6} {'理由':<30}")
print("-" * 100)

for i, p in enumerate(tomorrow_picks[:15], 1):
    reason_str = ', '.join(p['reasons'][:2])
    print(f"{i:^3} {p['code']:^8} {p['name']:^10} {p['price']:>6.2f} {p['change']:>+6.2f}% "
          f"{p['amount']:>5.1f} {p['score']:^6} {reason_str[:30]}")

# ============================================================
# Step 4: 历史验证最佳股票
# ============================================================
print("\n" + "=" * 70)
print("Step 4: 历史最佳股票验证")
print("=" * 70)

best_stocks = []
for code in codes:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
    conn.close()
    
    if df is None or len(df) < 30:
        continue
    
    df = df.sort_values('date').tail(120).reset_index(drop=True)
    df['vol_ma5'] = df['volume'].rolling(5).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma5']
    
    max_pnl = 0
    best_date = ''
    best_buy = 0
    
    for i in range(20, len(df) - 5):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        chg = (row['close'] - prev['close']) / prev['close'] * 100 if prev['close'] > 0 else 0
        vol_ratio = row['vol_ratio'] if not pd.isna(row['vol_ratio']) else 1
        
        if chg_min <= chg <= chg_max and 3 <= row['close'] <= pmax and vol_ratio >= vol_min:
            buy = row['close']
            future = df.iloc[i+1:i+6]['close'].tolist()
            if future:
                sell_max = max(future)
                pnl = (sell_max - buy) / buy * 100 if buy > 0 else 0
                if pnl > max_pnl:
                    max_pnl = pnl
                    best_date = row['date']
                    best_buy = buy
    
    name = code_to_name.get(code, code)
    if max_pnl > 5:
        best_stocks.append((code, name, round(max_pnl, 1), best_date, best_buy))

best_stocks.sort(key=lambda x: x[2], reverse=True)

print(f"\n历史最佳表现 TOP 15:")
print(f"{'#':^3} {'代码':^8} {'名称':^10} {'最大周涨':^10} {'买点日期':^14} {'买点价':^8}")
print("-" * 60)

for i, (code, name, pnl, date, buy) in enumerate(best_stocks[:15], 1):
    print(f"{i:^3} {code:^8} {name:^10} {pnl:>7.1f}% {date:^14} {buy:>7.2f}")

# ============================================================
# 保存结果
# ============================================================
output = {
    'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
    'total_stocks': total_stocks,
    'total_klines': total_klines,
    'stocks_collected_this_run': len(collected),
    'best_strategy': {
        'holding': best['holding'] if best else 0,
        'buy_chg': best['buy_chg'] if best else 'N/A',
        'price_max': best['price_max'] if best else 'N/A',
        'vol_ratio_min': best['vol_ratio_min'] if best else 0,
        'win_rate': round(best['win_rate'], 1) if best else 0,
        'avg_max_pnl': round(best['avg_max_pnl'], 2) if best else 0,
        'target_30_rate': round(best['target_30_rate'], 1) if best else 0,
        'target_20_rate': round(best['target_20_rate'], 1) if best else 0,
        'target_10_rate': round(best['target_10_rate'], 1) if best else 0,
        'max_pnl': round(best['max_pnl'], 1) if best else 0,
    },
    'tomorrow_picks': [{
        'code': p['code'], 'name': p['name'], 'price': p['price'],
        'change': p['change'], 'amount': p['amount'], 'score': p['score']
    } for p in tomorrow_picks[:20]],
    'best_stocks_history': [{
        'code': code, 'name': name, 'max_pnl': pnl, 'date': date, 'buy_price': buy
    } for code, name, pnl, date, buy in best_stocks[:20]],
}

with open('data/v11_results.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

# ============================================================
# 汇报
# ============================================================
print("\n" + "=" * 70)
print("【汇报】量化选股系统 V11")
print("=" * 70)
print(f"- 数据量: {total_stocks}只股票, {total_klines}条K线")
print(f"- 本次收集: {len(collected)}只")
if best:
    print(f"- 最优策略: 持有{best['holding']}天, 买入涨幅{best['buy_chg']}%, 价格<={best['price_max']}")
    print(f"  胜率: {best['win_rate']:.1f}%")
    print(f"  达标率(30%): {best['target_30_rate']:.1f}%")
    print(f"  达标率(20%): {best['target_20_rate']:.1f}%")
    print(f"  达标率(10%): {best['target_10_rate']:.1f}%")
    print(f"  平均最大收益: {best['avg_max_pnl']:.2f}%")
    print(f"  最高单笔: {best['max_pnl']:.1f}%")
if tomorrow_picks:
    p = tomorrow_picks[0]
    print(f"- 明日首选: {p['code']} {p['name']} 评分{p['score']}")
    for p in tomorrow_picks[1:5]:
        print(f"         {p['code']} {p['name']} 评分{p['score']}")
if best_stocks:
    code, name, pnl, date, buy = best_stocks[0]
    print(f"- 历史最佳: {code} {name} 周涨{pnl}%")
print("=" * 70)
