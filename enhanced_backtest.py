# -*- coding: utf-8 -*-
"""
增强版量化选股系统 - 数据收集 + 优化回测
"""
import os, sys, time, json, sqlite3, requests, numpy as np, pandas as pd
from datetime import datetime, timedelta

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

DB_PATH = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'
os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')

# ============================================================
# Step 1: 从实时行情获取候选股票, 用新浪API获取历史K线
# ============================================================
print("=" * 70)
print("Step 1: 获取候选股票列表 + 收集历史K线")
print("=" * 70)

conn = sqlite3.connect(DB_PATH)
# 从实时行情表获取候选股票
df_quotes = pd.read_sql('SELECT * FROM realtime_quote', conn)
conn.close()

print(f"实时行情: {len(df_quotes)} 只股票")

# 筛选候选股
candidates = []
for _, row in df_quotes.iterrows():
    code = row['code']
    name = row['name']
    if code.startswith('688') or code.startswith('300') or code.startswith('8'):
        continue
    if 'ST' in str(name) or '退' in str(name):
        continue
    try:
        price = float(row['close']) if row['close'] else 0
        change = float(row['change']) if row['change'] else 0
        amount = float(row['amount']) / 1e8 if row['amount'] else 0
    except:
        continue
    if price <= 0:
        continue
    candidates.append({
        'code': code, 'name': name, 'price': price,
        'change': change, 'amount': amount
    })

print(f"候选股票(排除ST/科创/北交所): {len(candidates)} 只")

# 用新浪API收集历史K线
def collect_sina(code, days=200):
    """用新浪财经API获取历史K线"""
    market = 'sh' if code.startswith('6') else 'sz'
    url = f'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
    params = {
        'symbol': f'{market}{code}',
        'scale': 240,  # 日K
        'ma': 'no',
        'datalen': days
    }
    try:
        r = requests.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        data = r.json()
        if data and isinstance(data, list) and len(data) > 5:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            count = 0
            for d in data:
                c.execute('''INSERT OR IGNORE INTO kline 
                    (code, date, open, close, high, low, volume, amount)
                    VALUES (?,?,?,?,?,?,?,?)''',
                    (code, d['day'], float(d['open']), float(d['close']),
                     float(d['high']), float(d['low']), float(d['volume']), 0))
                count += 1
            conn.commit()
            conn.close()
            return count
    except Exception as e:
        pass
    return 0

# 从实时行情中选取50只有代表性的股票
selected = sorted(candidates, key=lambda x: abs(x['change']), reverse=True)[:50]
print(f"\n选取交易活跃的 {len(selected)} 只股票收集K线...")

collected = []
for s in selected:
    n = collect_sina(s['code'], 200)
    if n > 0:
        collected.append((s['code'], s['name'], n))
    time.sleep(0.3)
    if len(collected) % 10 == 0:
        print(f"  已收集 {len(collected)} 只...")

print(f"\n收集完成: {len(collected)} 只")
for code, name, n in collected[:10]:
    print(f"  {code} {name}: {n} 条K线")

# ============================================================
# Step 2: 加载所有K线数据
# ============================================================
print("\n" + "=" * 70)
print("Step 2: 加载K线数据进行分析")
print("=" * 70)

conn = sqlite3.connect(DB_PATH)
codes_in_db = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
conn.close()
print(f"数据库中共有: {len(codes_in_db)} 只股票的K线")

# ============================================================
# Step 3: 多策略优化回测
# ============================================================
print("\n" + "=" * 70)
print("Step 3: 多策略优化回测 (寻找涨30%的规律)")
print("=" * 70)

all_results = []

for holding in [1, 2, 3, 5]:
    for buy_chg_min, buy_chg_max in [(0, 3), (1, 5), (2, 6), (3, 8), (5, 10), (8, 15)]:
        for price_min, price_max in [(0, 10), (0, 20), (3, 15), (5, 30), (10, 50)]:
            trades = []
            
            for code in codes_in_db:
                conn = sqlite3.connect(DB_PATH)
                df = pd.read_sql(
                    'SELECT * FROM kline WHERE code=? ORDER BY date',
                    conn, params=(code,))
                conn.close()
                
                if df is None or len(df) < 40:
                    continue
                df = df.sort_values('date').tail(120).reset_index(drop=True)
                
                for i in range(25, len(df) - holding - 1):
                    row = df.iloc[i]
                    prev = df.iloc[i-1]
                    
                    chg = (row['close'] - prev['close']) / prev['close'] * 100 if prev['close'] > 0 else 0
                    vol_ratio = row['volume'] / df.iloc[max(0,i-20):i]['volume'].mean() if i >= 20 and df.iloc[max(0,i-20):i]['volume'].mean() > 0 else 1
                    
                    if buy_chg_min <= chg <= buy_chg_max and price_min <= row['close'] <= price_max:
                        buy = row['close']
                        sell_prices = df.iloc[i+1:i+holding+1]['close'].tolist()
                        if buy > 0 and sell_prices:
                            sell_max = max(sell_prices)
                            sell_final = sell_prices[-1]
                            pnl_max = (sell_max - buy) / buy * 100
                            pnl_final = (sell_final - buy) / buy * 100
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
            targets_10 = sum(1 for p in pnls_max if p >= 10)
            avg_vol = np.mean([t['vol_ratio'] for t in trades])
            
            all_results.append({
                'holding': holding,
                'buy_chg': f'{buy_chg_min}-{buy_chg_max}',
                'price': f'{price_min}-{price_max}',
                'trades': len(trades),
                'win_rate': wins / len(trades) * 100,
                'avg_pnl': np.mean(pnls_final),
                'avg_max_pnl': np.mean(pnls_max),
                'max_pnl': max(pnls_max),
                'target_30_rate': targets_30 / len(trades) * 100,
                'target_10_rate': targets_10 / len(trades) * 100,
                'avg_vol_ratio': avg_vol,
            })

# 按达标率排序
all_results.sort(key=lambda x: x['target_30_rate'], reverse=True)

print(f"\n共测试 {len(all_results)} 种参数组合\n")
print("TOP 20 策略 (按达标率30%排序):")
print(f"{'#':^3} {'持有':^4} {'买入涨幅':^10} {'价格区间':^12} {'交易':^5} {'胜率':^8} {'平均最大':^10} {'最高单笔':^10} {'达标30%':^10} {'达标10%':^10} {'量比':^6}")
print("-" * 100)

for i, r in enumerate(all_results[:20], 1):
    print(f"{i:^3} {r['holding']:^4} {r['buy_chg']:^10} {r['price']:^12} "
          f"{r['trades']:^5} {r['win_rate']:>6.1f}% {r['avg_max_pnl']:>8.2f}% "
          f"{r['max_pnl']:>8.2f}% {r['target_30_rate']:>8.1f}% "
          f"{r['target_10_rate']:>8.1f}% {r['avg_vol_ratio']:>5.2f}x")

best = all_results[0] if all_results else None

# ============================================================
# Step 4: 找出最佳股票
# ============================================================
print("\n" + "=" * 70)
print("Step 4: 识别最佳股票 (按历史最大涨幅)")
print("=" * 70)

best_stocks = []
for code in codes_in_db:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
    conn.close()
    if df is None or len(df) < 30:
        continue
    
    df = df.sort_values('date').tail(120).reset_index(drop=True)
    
    max_pnl = 0
    best_date = ''
    best_buy = 0
    for i in range(20, len(df) - 5):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        chg = (row['close'] - prev['close']) / prev['close'] * 100 if prev['close'] > 0 else 0
        
        if 1 <= chg <= 8 and 3 <= row['close'] <= 30:
            buy = row['close']
            sell_max = max(df.iloc[i+1:i+6]['close'].tolist())
            pnl = (sell_max - buy) / buy * 100 if buy > 0 else 0
            if pnl > max_pnl:
                max_pnl = pnl
                best_date = row['date']
                best_buy = buy
    
    name = ''
    for s in candidates:
        if s['code'] == code:
            name = s['name']
            break
    
    if max_pnl > 3:
        best_stocks.append((code, name, round(max_pnl, 1), best_date))

best_stocks.sort(key=lambda x: x[2], reverse=True)

print("\n历史最大周涨幅 TOP 10:")
print(f"{'排名':^4} {'代码':^8} {'名称':^10} {'最大涨幅':^10} {'买点日期':^14}")
print("-" * 50)
for i, (code, name, pnl, date) in enumerate(best_stocks[:10], 1):
    print(f"{i:^4} {code:^8} {name:^10} {pnl:>7.1f}% {date:^14}")

# ============================================================
# Step 5: 今日选股推荐
# ============================================================
print("\n" + "=" * 70)
print("Step 5: 今日选股推荐 (基于优化策略)")
print("=" * 70)

# 从实时行情中按最优策略筛选
today_picks = []
for s in candidates:
    try:
        price = s['price']
        change = s['change']
        amount = s['amount']
        
        # 应用最优策略参数
        if best:
            buy_chg_parts = best['buy_chg'].split('-')
            chg_min, chg_max = float(buy_chg_parts[0]), float(buy_chg_parts[1])
            price_parts = best['price'].split('-')
            p_min, p_max = float(price_parts[0]), float(price_parts[1])
        else:
            chg_min, chg_max = 1, 8
            p_min, p_max = 3, 20
        
        if not (chg_min <= change <= chg_max and p_min <= price <= p_max):
            continue
        
        score = 0
        if 2 <= change <= 6:
            score += 40
        elif 1 <= change <= 9:
            score += 25
        
        if amount >= 5:
            score += 30
        elif amount >= 2:
            score += 20
        
        if price <= 10:
            score += 20
        elif price <= 20:
            score += 10
        
        if score >= 60:
            today_picks.append({
                'code': s['code'], 'name': s['name'],
                'price': price, 'change': change,
                'amount': amount, 'score': score
            })
    except:
        pass

today_picks.sort(key=lambda x: x['score'], reverse=True)

print(f"\n今日推荐 (共{len(today_picks)}只, 评分>=60):")
print(f"{'排名':^4} {'代码':^8} {'名称':^10} {'现价':^8} {'涨幅':^8} {'成交亿':^8} {'评分':^6}")
print("-" * 60)
for i, p in enumerate(today_picks[:15], 1):
    print(f"{i:^4} {p['code']:^8} {p['name']:^10} {p['price']:>6.2f} {p['change']:>+6.2f}% {p['amount']:>6.1f} {p['score']:^6}")

# ============================================================
# 保存结果
# ============================================================
output = {
    'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
    'stocks_collected': len(collected),
    'total_codes_in_db': len(codes_in_db),
    'total_candidates': len(candidates),
    'best_strategy': {
        'holding': best['holding'] if best else 0,
        'buy_chg': best['buy_chg'] if best else 'N/A',
        'price_range': best['price'] if best else 'N/A',
        'win_rate': round(best['win_rate'], 1) if best else 0,
        'avg_max_pnl': round(best['avg_max_pnl'], 2) if best else 0,
        'target_30_rate': round(best['target_30_rate'], 1) if best else 0,
        'target_10_rate': round(best['target_10_rate'], 1) if best else 0,
    },
    'top_stocks': best_stocks[:10],
    'today_picks': today_picks[:15],
    'all_results_top20': all_results[:20]
}

with open('data/enhanced_backtest_results.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 70)
print("【汇报】")
print("=" * 70)
print(f"- 收集进度: {len(collected)} 只股票 (数据库共 {len(codes_in_db)} 只)")
if best:
    print(f"- 回测结果: 胜率{best['win_rate']:.1f}%, 达标率(30%) {best['target_30_rate']:.1f}%, 达标率(10%) {best['target_10_rate']:.1f}%")
    print(f"  最优参数: 持有{best['holding']}天, 买入涨幅{best['buy_chg']}%, 价格区间{best['price']}")
else:
    print(f"- 回测结果: 数据不足")
if best_stocks:
    code, name, pnl, date = best_stocks[0]
    print(f"- 最佳股票: {code} {name} (历史最大周涨{pnl:.1f}%)")
print("- 下一步优化方向:")
print("  1. 收集更多股票数据(目标是100只)")
print("  2. 增加量价因子筛选(量比>1.5)")
print("  3. 结合资金流向数据优化选股")
print("  4. 尝试追涨策略(涨幅5-10%买入)")
print("=" * 70)
