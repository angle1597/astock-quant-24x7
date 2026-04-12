# -*- coding: utf-8 -*-
"""
量化选股系统 - 最终分析版
数据收集 + 多策略优化回测 + 智能选股
"""
import os, sys, time, json, sqlite3, requests, numpy as np, pandas as pd
from datetime import datetime, timedelta

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

DB_PATH = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'
os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')

# ============================================================
# Step 1: 收集K线数据 (新浪财经API)
# ============================================================
print("=" * 70)
print("Step 1: 收集K线数据")
print("=" * 70)

conn = sqlite3.connect(DB_PATH)
df_quotes = pd.read_sql(
    '''SELECT code, name, price, change, turnover, amount, mv
       FROM realtime_quote
       WHERE code NOT LIKE '688%' AND code NOT LIKE '300%'
       AND code NOT LIKE '8%' AND name NOT LIKE '%ST%' ''',
    conn)
conn.close()

# Filter: keep main board stocks
df_quotes = df_quotes[~df_quotes['name'].str.contains('ST', na=False)]
candidates = df_quotes.to_dict('records')
print(f"候选股票: {len(candidates)} 只")

# Sina K-line API
def collect_sina(code, name, days=200):
    market = 'sh' if code.startswith('6') else 'sz'
    url = (f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php'
           f'/CN_MarketData.getKLineData')
    params = {'symbol': f'{market}{code}', 'scale': 240, 'ma': 'no', 'datalen': days}
    try:
        r = requests.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=12)
        data = r.json()
        if data and isinstance(data, list) and len(data) > 5:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            count = 0
            for d in data:
                c.execute('''INSERT OR IGNORE INTO kline
                    (code,date,open,close,high,low,volume,turnover)
                    VALUES (?,?,?,?,?,?,?,?)''',
                    (code, d['day'], float(d['open']), float(d['close']),
                     float(d['high']), float(d['low']), float(d['volume']), 0))
                count += 1
            conn.commit()
            conn.close()
            return count
    except:
        pass
    return 0

# 优先收集数据量少的股票
conn = sqlite3.connect(DB_PATH)
existing = pd.read_sql('SELECT code, COUNT(*) as cnt FROM kline GROUP BY code', conn)
existing_dict = dict(zip(existing['code'], existing['cnt']))
conn.close()

need_collect = []
for c in candidates:
    cnt = existing_dict.get(c['code'], 0)
    need_collect.append((c['code'], c['name'], cnt))

# 按数据量升序排列，优先收集数据少的
need_collect.sort(key=lambda x: x[2])
print(f"需要收集: {len(need_collect)} 只")

collected = []
for code, name, old_cnt in need_collect[:80]:
    n = collect_sina(code, name, 200)
    if n > old_cnt:
        collected.append((code, name, old_cnt, old_cnt + n))
    time.sleep(0.25)
    if len(collected) % 15 == 0:
        print(f"  已新增收集 {len(collected)} 只...")

print(f"\n收集完成: {len(collected)} 只")
for code, name, old_n, new_n in collected[:8]:
    print(f"  {code} {name}: {old_n} -> {new_n} 条K线")

# ============================================================
# Step 2: 加载数据 + 多策略回测
# ============================================================
print("\n" + "=" * 70)
print("Step 2: 多策略优化回测")
print("=" * 70)

conn = sqlite3.connect(DB_PATH)
codes_in_db = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
conn.close()
print(f"数据库中: {len(codes_in_db)} 只股票")

# 创建代码->名称映射
code_to_name = {c['code']: c['name'] for c in candidates}
for code in codes_in_db:
    if code not in code_to_name:
        code_to_name[code] = code

all_results = []

for holding in [1, 2, 3, 5, 7]:
    for buy_chg_min, buy_chg_max in [(0, 2), (0, 3), (1, 4), (1, 5), (2, 5), (2, 8), (3, 7), (3, 10), (5, 10)]:
        for price_max in [10, 15, 20, 30]:
            trades = []

            for code in codes_in_db:
                conn = sqlite3.connect(DB_PATH)
                df = pd.read_sql(
                    'SELECT * FROM kline WHERE code=? ORDER BY date',
                    conn, params=(code,))
                conn.close()

                if df is None or len(df) < 30:
                    continue
                df = df.sort_values('date').tail(150).reset_index(drop=True)

                # 计算量比
                df['vol_ma5'] = df['volume'].rolling(5).mean()
                df['vol_ratio'] = df['volume'] / df['vol_ma5']

                for i in range(20, len(df) - holding - 1):
                    row = df.iloc[i]
                    prev = df.iloc[i-1]

                    chg = (row['close'] - prev['close']) / prev['close'] * 100 if prev['close'] > 0 else 0

                    if buy_chg_min <= chg <= buy_chg_max and row['close'] <= price_max and row['close'] >= 3:
                        buy = row['close']
                        # 持有期内最高价和最终价
                        sell_max = max(df.iloc[i+1:i+holding+1]['close'].tolist())
                        sell_final = df.iloc[i+holding]['close'] if i+holding < len(df) else buy
                        if buy > 0:
                            pnl_max = (sell_max - buy) / buy * 100
                            pnl_final = (sell_final - buy) / buy * 100
                            vol_ratio = row['vol_ratio'] if not pd.isna(row['vol_ratio']) else 1
                            trades.append({
                                'code': code, 'date': row['date'],
                                'buy_chg': chg, 'price': buy,
                                'pnl_max': pnl_max, 'pnl_final': pnl_final,
                                'vol_ratio': vol_ratio
                            })

            if len(trades) < 5:
                continue

            pnls_max = [t['pnl_max'] for t in trades]
            pnls_final = [t['pnl_final'] for t in trades]
            wins = sum(1 for p in pnls_final if p > 0)
            targets_30 = sum(1 for p in pnls_max if p >= 30)
            targets_20 = sum(1 for p in pnls_max if p >= 20)
            targets_10 = sum(1 for p in pnls_max if p >= 10)

            all_results.append({
                'holding': holding,
                'buy_chg': f'{buy_chg_min}-{buy_chg_max}',
                'price_max': price_max,
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

all_results.sort(key=lambda x: (x['target_30_rate'], x['avg_max_pnl']), reverse=True)

print(f"\n共测试 {len(all_results)} 种参数组合\n")
print("TOP 15 策略:")
print(f"{'#':^3} {'持有':^4} {'买入涨幅':^10} {'价上限':^6} {'交易':^5} {'胜率':^8} {'平均最大':^10} {'最高':^8} {'30%率':^8} {'20%率':^8} {'10%率':^8}")
print("-" * 90)

for i, r in enumerate(all_results[:15], 1):
    print(f"{i:^3} {r['holding']:^4} {r['buy_chg']:^10} {r['price_max']:^6} "
          f"{r['trades']:^5} {r['win_rate']:>6.1f}% {r['avg_max_pnl']:>8.2f}% "
          f"{r['max_pnl']:>6.1f}% {r['target_30_rate']:>6.1f}% "
          f"{r['target_20_rate']:>6.1f}% {r['target_10_rate']:>6.1f}%")

best = all_results[0] if all_results else None

# ============================================================
# Step 3: 分析最佳股票
# ============================================================
print("\n" + "=" * 70)
print("Step 3: 历史最佳股票分析")
print("=" * 70)

# 使用最优策略找最佳股票
if best:
    chg_parts = best['buy_chg'].split('-')
    chg_min, chg_max = float(chg_parts[0]), float(chg_parts[1])
    pmax = best['price_max']
else:
    chg_min, chg_max, pmax = 1, 5, 15

best_stocks = []
for code in codes_in_db:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
    conn.close()
    if df is None or len(df) < 30:
        continue
    df = df.sort_values('date').tail(150).reset_index(drop=True)
    df['vol_ma5'] = df['volume'].rolling(5).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma5']

    max_pnl = 0
    best_date = ''
    best_buy = 0
    for i in range(20, len(df) - 5):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        chg = (row['close'] - prev['close']) / prev['close'] * 100 if prev['close'] > 0 else 0
        if chg_min <= chg <= chg_max and 3 <= row['close'] <= pmax:
            buy = row['close']
            sell_max = max(df.iloc[i+1:i+6]['close'].tolist())
            pnl = (sell_max - buy) / buy * 100 if buy > 0 else 0
            if pnl > max_pnl:
                max_pnl = pnl
                best_date = row['date']
                best_buy = buy

    name = code_to_name.get(code, code)
    if max_pnl > 2:
        best_stocks.append((code, name, round(max_pnl, 1), best_date, best_buy))

best_stocks.sort(key=lambda x: x[2], reverse=True)

print(f"\n历史最佳表现 TOP 10 (按最大周涨幅):")
print(f"{'#':^3} {'代码':^8} {'名称':^10} {'最大周涨':^10} {'买点日期':^14} {'买点价格':^10}")
print("-" * 60)
for i, (code, name, pnl, date, buy) in enumerate(best_stocks[:10], 1):
    print(f"{i:^3} {code:^8} {name:^10} {pnl:>7.1f}% {date:^14} {buy:>8.2f}")

# ============================================================
# Step 4: 今日选股
# ============================================================
print("\n" + "=" * 70)
print("Step 4: 今日选股推荐")
print("=" * 70)

today_picks = []
for s in candidates:
    try:
        price = float(s['price']) if s['price'] else 0
        change = float(s['change']) if s['change'] else 0  # Already in percent
        amount = float(s['amount']) / 1e8 if s['amount'] else 0
        turnover = float(s['turnover']) if s['turnover'] else 0

        if price <= 0:
            continue
        if change <= 0 or change > 10:
            continue

        score = 0
        # 动量因子
        if 2 <= change <= 6:
            score += 40
        elif 1 <= change <= 9:
            score += 25
        elif change < 2:
            score += 15

        # 价格因子
        if 3 <= price <= 10:
            score += 30
        elif 10 < price <= 20:
            score += 20

        # 量能因子
        if amount >= 5:
            score += 25
        elif amount >= 2:
            score += 15

        # 换手率
        if turnover >= 10:
            score += 15
        elif turnover >= 5:
            score += 10

        # 题材加分
        hot = ['能源', '电力', '光伏', '新能源', 'AI', '军工', '稀土', '农业', '医药', '汽车']
        for kw in hot:
            if kw in s['name']:
                score += 10
                break

        if score >= 55:
            today_picks.append({
                'code': s['code'], 'name': s['name'],
                'price': price, 'change': change,
                'amount': amount, 'turnover': turnover,
                'score': score
            })
    except:
        pass

today_picks.sort(key=lambda x: x['score'], reverse=True)

print(f"\n今日推荐 ({len(today_picks)}只, 评分>=55):")
print(f"{'#':^3} {'代码':^8} {'名称':^10} {'现价':^8} {'涨幅%':^8} {'成交亿':^8} {'换手%':^8} {'评分':^6}")
print("-" * 70)
for i, p in enumerate(today_picks[:20], 1):
    print(f"{i:^3} {p['code']:^8} {p['name']:^10} {p['price']:>6.2f} {p['change']:>+6.2f}% "
          f"{p['amount']:>5.1f} {p['turnover']:>5.1f}% {p['score']:^6}")

# ============================================================
# 保存结果
# ============================================================
output = {
    'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
    'stocks_collected': len(collected),
    'total_codes_in_db': len(codes_in_db),
    'best_strategy': {
        'holding': best['holding'] if best else 0,
        'buy_chg': best['buy_chg'] if best else 'N/A',
        'price_max': best['price_max'] if best else 'N/A',
        'win_rate': round(best['win_rate'], 1) if best else 0,
        'avg_max_pnl': round(best['avg_max_pnl'], 2) if best else 0,
        'max_pnl': round(best['max_pnl'], 1) if best else 0,
        'target_30_rate': round(best['target_30_rate'], 1) if best else 0,
        'target_20_rate': round(best['target_20_rate'], 1) if best else 0,
        'target_10_rate': round(best['target_10_rate'], 1) if best else 0,
    },
    'top_stocks': [(code, name, pnl, date, buy) for code, name, pnl, date, buy in best_stocks[:10]],
    'today_picks': today_picks[:20],
    'all_results_top20': [{
        'holding': r['holding'], 'buy_chg': r['buy_chg'], 'price_max': r['price_max'],
        'trades': r['trades'], 'win_rate': round(r['win_rate'], 1),
        'avg_max_pnl': round(r['avg_max_pnl'], 2), 'max_pnl': round(r['max_pnl'], 1),
        'target_30_rate': round(r['target_30_rate'], 1),
        'target_20_rate': round(r['target_20_rate'], 1),
        'target_10_rate': round(r['target_10_rate'], 1),
    } for r in all_results[:20]]
}

with open('data/final_analysis_results.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

# ============================================================
# 汇报
# ============================================================
print("\n" + "=" * 70)
print("【汇报】")
print("=" * 70)
print(f"- 收集进度: {len(collected)} 只股票 (数据库共 {len(codes_in_db)} 只)")
if best:
    print(f"- 回测结果: 胜率{best['win_rate']:.1f}%, 达标率(30%) {best['target_30_rate']:.1f}%")
    print(f"  达标率(20%) {best['target_20_rate']:.1f}%, 达标率(10%) {best['target_10_rate']:.1f}%")
    print(f"  最优参数: 持有{best['holding']}天, 买入涨幅{best['buy_chg']}%, 价格<={best['price_max']}")
    print(f"  平均最大收益: {best['avg_max_pnl']:.2f}%, 最高单笔: {best['max_pnl']:.1f}%")
else:
    print("- 回测结果: 数据不足")
if best_stocks:
    code, name, pnl, date, buy = best_stocks[0]
    print(f"- 最佳股票: {code} {name} (历史最大周涨{pnl:.1f}%, 买点在{date}@{buy})")
    for code, name, pnl, date, buy in best_stocks[1:5]:
        print(f"           {code} {name} (周涨{pnl:.1f}%)")
else:
    print("- 最佳股票: 无")
print("- 下一步优化方向:")
print("  1. 扩展数据收集(目标是收集100只股票的历史K线)")
print("  2. 增加量比因子(vol_ratio>1.5)筛选")
print("  3. 结合资金流向数据优化")
print("  4. 尝试追涨策略(涨幅5-10%次日买入)")
print("  5. 加入技术指标(MACD/RSI)综合评分")
print("=" * 70)
