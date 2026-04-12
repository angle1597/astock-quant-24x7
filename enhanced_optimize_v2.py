# -*- coding: utf-8 -*-
"""
增强版量化系统持续优化
1. 收集100只新股票K线数据
2. 测试新策略: RSI超卖, KDJ金叉, 量比>2x, 涨停后回调
3. 找出达标率更高的策略
"""
import sys, os, sqlite3, json, math, time, random
import numpy as np
import pandas as pd
import requests

sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'
OUTPUT = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\enhanced_optimize.json'

# ===== 技术指标计算 =====

def calc_rsi_full(closes, period=14):
    if len(closes) < period + 1:
        return [None] * len(closes)
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    rsi = [None] * period
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, len(closes)):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        if avg_loss == 0:
            rsi.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100 - (100 / (1 + rs)))
    return rsi

def calc_ema(series, n):
    if len(series) < n:
        return [None] * len(series)
    k = 2 / (n + 1)
    ema = [None] * (n - 1)
    ema.append(series[n - 1])
    for i in range(n, len(series)):
        ema.append(series[i] * k + ema[-1] * (1 - k))
    return ema

def calc_macd(closes, fast=12, slow=26, signal=9):
    n = len(closes)
    dif = [None] * n
    dea = [None] * n
    macd_bar = [None] * n
    if n < slow + signal:
        return dif, dea, macd_bar
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    for i in range(n):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            dif[i] = ema_fast[i] - ema_slow[i]
    dif_valid = [(i, x) for i, x in enumerate(dif) if x is not None]
    if len(dif_valid) < signal:
        return dif, dea, macd_bar
    k = 2 / (signal + 1)
    valid_dif = [x for _, x in dif_valid]
    dea_values = [valid_dif[signal - 1]]
    for i in range(signal, len(valid_dif)):
        dea_values.append(valid_dif[i] * k + dea_values[-1] * (1 - k))
    first_valid_idx = dif_valid[0][0]
    last_valid_idx = dif_valid[-1][0]
    for j, idx in enumerate(range(first_valid_idx + signal - 1, last_valid_idx + 1)):
        if idx < n:
            dea[idx] = dea_values[j]
    for i in range(n):
        if dif[i] is not None and dea[i] is not None:
            macd_bar[i] = (dif[i] - dea[i]) * 2
    return dif, dea, macd_bar

def calc_kdj(highs, lows, closes, n=9, m1=3, m2=3):
    """计算KDJ指标"""
    length = len(closes)
    k_vals = [None] * length
    d_vals = [None] * length
    j_vals = [None] * length
    if length < n:
        return k_vals, d_vals, j_vals
    
    rsv = [None] * length
    for i in range(n - 1, length):
        h_n = max(highs[i - n + 1:i + 1])
        l_n = min(lows[i - n + 1:i + 1])
        if h_n == l_n:
            rsv[i] = 50
        else:
            rsv[i] = (closes[i] - l_n) / (h_n - l_n) * 100
    
    # K = SMA(RSV, m1), D = SMA(K, m2), J = 3K - 2D
    prev_k = 50
    prev_d = 50
    for i in range(length):
        if rsv[i] is not None:
            k_vals[i] = (2 / m1) * prev_k + (1 / m1) * rsv[i] if i >= n - 1 else None
            if k_vals[i] is not None:
                prev_k = k_vals[i]
                d_vals[i] = (2 / m2) * prev_d + (1 / m2) * k_vals[i]
                prev_d = d_vals[i]
                j_vals[i] = 3 * k_vals[i] - 2 * d_vals[i]
    
    return k_vals, d_vals, j_vals

def calc_ma(closes, period):
    if len(closes) < period:
        return [None] * len(closes)
    return [None] * (period - 1) + [np.mean(closes[i - period + 1:i + 1]) for i in range(period - 1, len(closes))]

def calc_volume_ma(volumes, period=5):
    if len(volumes) < period:
        return [None] * len(volumes)
    return [None] * (period - 1) + [np.mean(volumes[i - period + 1:i + 1]) for i in range(period - 1, len(volumes))]


# ===================================================================
# STEP 1: 收集100只新股票K线数据
# ===================================================================
print("=" * 80)
print("【增强版量化系统持续优化】")
print("=" * 80)

# 获取已有股票
conn = sqlite3.connect(DB)
existing_codes = set(pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist())
print(f"已有股票数: {len(existing_codes)}")

# 从东方财富获取更多股票
def fetch_stock_list():
    """获取沪深A股列表"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    url = 'https://push2.eastmoney.com/api/qt/clist/get'
    
    all_stocks = []
    for page in range(1, 15):  # 多页获取
        params = {
            'pn': page, 'pz': 500, 'po': 1, 'np': 1, 'fltt': 2, 'invt': 2,
            'fid': 'f3',
            'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
            'fields': 'f12,f14,f2,f3,f6,f20'
        }
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            data = resp.json()
            if data.get('data') and data['data'].get('diff'):
                for item in data['data']['diff']:
                    code = item.get('f12', '')
                    name = item.get('f14', '')
                    price = item.get('f2', 0)
                    change = item.get('f3', 0)
                    vol = item.get('f6', 0)
                    mv = item.get('f20', 0)
                    if code and len(code) == 6 and code.isdigit() and price > 0:
                        # 过滤ST、退市、北交所
                        if 'ST' not in name and '退' not in name and not code.startswith('4') and not code.startswith('8'):
                            all_stocks.append({'code': code, 'name': name, 'price': price, 
                                              'change': change, 'vol': vol, 'mv': mv})
        except Exception as e:
            print(f"  获取第{page}页失败: {e}")
            continue
        time.sleep(0.3)
    
    return all_stocks

def fetch_kline(code, limit=200):
    """获取K线数据"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    market = '1' if code.startswith('6') else '0'
    secid = f'{market}.{code}'
    url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
    params = {
        'secid': secid,
        'fields1': 'f1,f2,f3,f4,f5,f6',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
        'klt': '101', 'fqt': 1, 'end': '20500101', 'lmt': str(limit)
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        data = resp.json()
        if data.get('data') and data['data'].get('klines'):
            rows = []
            for line in data['data']['klines']:
                parts = line.split(',')
                rows.append({
                    'code': code, 'date': parts[0],
                    'open': float(parts[1]), 'high': float(parts[2]),
                    'low': float(parts[3]), 'close': float(parts[4]),
                    'volume': float(parts[5]),
                    'turnover': float(parts[6]) if len(parts) > 6 else 0
                })
            return rows
    except Exception as e:
        pass
    return []

print("\n[1/3] 收集100只新股票K线数据...")

stock_list = fetch_stock_list()
print(f"  获取到 {len(stock_list)} 只候选股票")

# 筛选新股票(不在已有列表中)，优先选择市值适中、成交量活跃的
new_stocks = [s for s in stock_list if s['code'] not in existing_codes]
# 按成交额排序(活跃优先)
new_stocks.sort(key=lambda x: x.get('vol', 0) or 0, reverse=True)
# 取前120只尝试(会有部分失败)
new_stocks = new_stocks[:120]

print(f"  新股票候选: {len(new_stocks)} 只")

added_count = 0
cursor = conn.cursor()
for i, stock in enumerate(new_stocks):
    if added_count >= 100:
        break
    klines = fetch_kline(stock['code'], 200)
    if len(klines) >= 100:  # 至少100根K线
        for row in klines:
            cursor.execute('''
                INSERT OR REPLACE INTO kline (code, date, open, high, low, close, volume, turnover)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (row['code'], row['date'], row['open'], row['high'], row['low'],
                  row['close'], row['volume'], row['turnover']))
        added_count += 1
        if added_count % 20 == 0:
            print(f"  已收集 {added_count}/100 只")
    time.sleep(0.3 + random.uniform(0, 0.3))

conn.commit()
print(f"  ✓ 新增 {added_count} 只股票K线数据")

# 更新股票列表
total_codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
print(f"  数据库总股票数: {len(total_codes)}")

# ===================================================================
# STEP 2: 加载数据 & 计算指标
# ===================================================================
print("\n[2/3] 计算技术指标 & 测试新策略...")

df_all = pd.read_sql('SELECT * FROM kline ORDER BY code, date', conn)
conn.close()

print(f"  总K线记录: {len(df_all)}, 股票数: {df_all['code'].nunique()}")
print(f"  日期范围: {df_all['date'].min()} ~ {df_all['date'].max()}")

for col in ['open', 'high', 'low', 'close', 'volume']:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce')

# 按股票分组计算指标
dfs = []
for code, grp in df_all.groupby('code'):
    grp = grp.sort_values('date').reset_index(drop=True)
    closes = grp['close'].tolist()
    highs = grp['high'].tolist()
    lows = grp['low'].tolist()
    volumes = grp['volume'].tolist()
    
    grp['rsi14'] = calc_rsi_full(closes, 14)
    grp['rsi6'] = calc_rsi_full(closes, 6)
    dif, dea, macd_bar = calc_macd(closes)
    grp['dif'] = dif
    grp['dea'] = dea
    grp['macd_bar'] = macd_bar
    
    k_vals, d_vals, j_vals = calc_kdj(highs, lows, closes)
    grp['k9'] = k_vals
    grp['d9'] = d_vals
    grp['j9'] = j_vals
    
    grp['ma5'] = calc_ma(closes, 5)
    grp['ma10'] = calc_ma(closes, 10)
    grp['ma20'] = calc_ma(closes, 20)
    grp['vol_ma5'] = calc_volume_ma(volumes, 5)
    grp['vol_ma10'] = calc_volume_ma(volumes, 10)
    grp['price_chg'] = grp['close'].pct_change() * 100
    grp['vol_ratio'] = grp['volume'] / grp['vol_ma5']
    
    # 涨停标记: 当日涨幅 >= 9.9% (非ST)
    grp['is_limit_up'] = grp['price_chg'] >= 9.9
    
    dfs.append(grp)

df = pd.concat(dfs, ignore_index=True)
print(f"  指标计算完成, 总行数: {len(df)}")


# ===================================================================
# STEP 3: 策略测试
# ===================================================================

def backtest_strategy(df, strategy_fn, name, hold_days_list=[5, 7, 10, 14, 21]):
    """通用回测框架"""
    results = []
    for hold in hold_days_list:
        trades = []
        for code, grp in df.groupby('code'):
            if len(grp) < hold + 40:
                continue
            grp = grp.reset_index(drop=True)
            
            for i in range(30, len(grp) - hold - 1):
                if not strategy_fn(grp, i):
                    continue
                
                buy_price = grp.iloc[i]['close']
                future = grp.iloc[i + 1:i + hold + 1]['close'].tolist()
                if not future or buy_price <= 0:
                    continue
                pnl_max = (max(future) - buy_price) / buy_price * 100
                pnl_final = (future[-1] - buy_price) / buy_price * 100
                trades.append({'max': pnl_max, 'final': pnl_final})
        
        if len(trades) >= 10:
            pnls_max = [t['max'] for t in trades]
            pnls_final = [t['final'] for t in trades]
            wins = sum(1 for p in pnls_final if p > 0)
            def hit_rate(threshold):
                return sum(1 for p in pnls_max if p >= threshold) / len(trades) * 100
            
            results.append({
                'strategy': name,
                'hold': hold,
                'n': len(trades),
                'win_rate': round(wins / len(trades) * 100, 1),
                'avg_max': round(np.mean(pnls_max), 1),
                'avg_final': round(np.mean(pnls_final), 1),
                'r50': round(hit_rate(50), 1),
                'r40': round(hit_rate(40), 1),
                'r30': round(hit_rate(30), 1),
                'r25': round(hit_rate(25), 1),
                'r20': round(hit_rate(20), 1),
            })
    return results

# ===== 新策略定义 =====

# 策略1: RSI超卖筛选 (RSI < 40)
def strategy_rsi_oversold(grp, i):
    row = grp.iloc[i]
    # RSI14 < 40, 价格3-30元, 当日跌幅 > -2%
    rsi = row['rsi14']
    if rsi is None or rsi >= 40:
        return False
    if not (3 <= row['close'] <= 30):
        return False
    chg = row['price_chg'] if not pd.isna(row['price_chg']) else 0
    if chg > 3:  # 不追涨太多
        return False
    return True

# 策略2: RSI超卖+MACD金叉
def strategy_rsi_macd(grp, i):
    row = grp.iloc[i]
    prev = grp.iloc[i - 1]
    rsi = row['rsi14']
    if rsi is None or rsi >= 45:
        return False
    if not (3 <= row['close'] <= 30):
        return False
    # MACD柱由负转正
    if row['macd_bar'] is None or prev['macd_bar'] is None:
        return False
    if not (prev['macd_bar'] < 0 and row['macd_bar'] > 0):
        return False
    return True

# 策略3: KDJ金叉筛选
def strategy_kdj_golden(grp, i):
    row = grp.iloc[i]
    prev = grp.iloc[i - 1]
    # K上穿D, J < 80 (未超买)
    k = row['k9']
    d = row['d9']
    j = row['j9']
    k_prev = prev['k9']
    d_prev = prev['d9']
    if any(v is None for v in [k, d, j, k_prev, d_prev]):
        return False
    if not (k_prev < d_prev and k > d):  # K金叉D
        return False
    if j > 100:  # 超买区不追
        return False
    if not (3 <= row['close'] <= 30):
        return False
    return True

# 策略4: KDJ金叉+RSI偏低
def strategy_kdj_rsi(grp, i):
    row = grp.iloc[i]
    prev = grp.iloc[i - 1]
    k = row['k9']
    d = row['d9']
    j = row['j9']
    k_prev = prev['k9']
    d_prev = prev['d9']
    rsi = row['rsi14']
    if any(v is None for v in [k, d, j, k_prev, d_prev, rsi]):
        return False
    if not (k_prev < d_prev and k > d):
        return False
    if rsi > 55:  # RSI中等偏低
        return False
    if not (3 <= row['close'] <= 30):
        return False
    return True

# 策略5: 量比>2x筛选
def strategy_volume_breakout(grp, i):
    row = grp.iloc[i]
    vr = row['vol_ratio']
    if vr is None or vr < 2.0:
        return False
    if not (3 <= row['close'] <= 30):
        return False
    chg = row['price_chg'] if not pd.isna(row['price_chg']) else 0
    if not (0 < chg <= 8):  # 放量上涨但不追涨停
        return False
    return True

# 策略6: 量比>2x + MA5>MA10 (趋势向上)
def strategy_volume_trend(grp, i):
    row = grp.iloc[i]
    vr = row['vol_ratio']
    if vr is None or vr < 2.0:
        return False
    if not (3 <= row['close'] <= 30):
        return False
    chg = row['price_chg'] if not pd.isna(row['price_chg']) else 0
    if not (0 < chg <= 8):
        return False
    # MA5 > MA10 趋势向上
    if row['ma5'] is None or row['ma10'] is None:
        return False
    if row['ma5'] <= row['ma10']:
        return False
    return True

# 策略7: 涨停后回调买入
def strategy_limit_up_pullback(grp, i):
    row = grp.iloc[i]
    # 检查过去5天内是否有涨停
    if i < 5:
        return False
    recent = grp.iloc[max(0, i-5):i]
    had_limit_up = recent['is_limit_up'].any()
    if not had_limit_up:
        return False
    # 当前日回调(涨幅 < 0)
    chg = row['price_chg'] if not pd.isna(row['price_chg']) else 0
    if chg >= 0:
        return False
    if not (3 <= row['close'] <= 30):
        return False
    # 回调幅度不超过5%
    if chg < -5:
        return False
    return True

# 策略8: 涨停后缩量回调
def strategy_limit_up_shrink(grp, i):
    row = grp.iloc[i]
    if i < 5:
        return False
    recent = grp.iloc[max(0, i-5):i]
    had_limit_up = recent['is_limit_up'].any()
    if not had_limit_up:
        return False
    chg = row['price_chg'] if not pd.isna(row['price_chg']) else 0
    if chg >= 0:
        return False
    if not (3 <= row['close'] <= 30):
        return False
    # 缩量回调: 量比 < 1
    vr = row['vol_ratio']
    if vr is not None and vr > 1.0:
        return False
    return True

# 策略9: RSI超卖 + KDJ金叉 + 量能放大 (复合策略)
def strategy_triple_filter(grp, i):
    row = grp.iloc[i]
    prev = grp.iloc[i - 1]
    # RSI < 45
    rsi = row['rsi14']
    if rsi is None or rsi >= 45:
        return False
    # KDJ金叉
    k = row['k9']
    d = row['d9']
    k_prev = prev['k9']
    d_prev = prev['d9']
    if any(v is None for v in [k, d, k_prev, d_prev]):
        return False
    if not (k_prev < d_prev and k > d):
        return False
    # 量比 > 1.2
    vr = row['vol_ratio']
    if vr is None or vr < 1.2:
        return False
    if not (3 <= row['close'] <= 30):
        return False
    return True

# 策略10: MACD金叉 + 量比放大 + RSI中等 (经典趋势策略)
def strategy_classic_trend(grp, i):
    row = grp.iloc[i]
    prev = grp.iloc[i - 1]
    # MACD柱由负转正
    if row['macd_bar'] is None or prev['macd_bar'] is None:
        return False
    if not (prev['macd_bar'] < 0 and row['macd_bar'] > 0):
        return False
    # 量比 > 1.5
    vr = row['vol_ratio']
    if vr is None or vr < 1.5:
        return False
    # RSI 40-60 中性区间
    rsi = row['rsi14']
    if rsi is None or not (35 <= rsi <= 65):
        return False
    if not (3 <= row['close'] <= 30):
        return False
    return True

# 策略11: 布林带下轨反弹
def strategy_bollinger_bounce(grp, i):
    row = grp.iloc[i]
    closes_so_far = grp.iloc[:i+1]['close'].tolist()
    if len(closes_so_far) < 20:
        return False
    ma20 = np.mean(closes_so_far[-20:])
    std20 = np.std(closes_so_far[-20:])
    lower_band = ma20 - 2 * std20
    # 价格触及或跌破下轨后反弹
    if row['close'] > lower_band * 1.02:  # 允许2%的偏离
        return False
    if not (3 <= row['close'] <= 30):
        return False
    return True

# 策略12: 缩量企稳(地量地价)
def strategy_volume_shrink_bottom(grp, i):
    row = grp.iloc[i]
    if i < 10:
        return False
    # 近10日最低量
    recent_vol = grp.iloc[i-10:i+1]['volume'].tolist()
    if not recent_vol or min(recent_vol) <= 0:
        return False
    if row['volume'] > min(recent_vol) * 1.2:
        return False
    # 价格在底部区域(低于MA20)
    if row['ma20'] is None or row['close'] > row['ma20']:
        return False
    if not (3 <= row['close'] <= 30):
        return False
    # RSI < 45
    rsi = row['rsi14']
    if rsi is None or rsi >= 45:
        return False
    return True

# ===== 运行所有策略回测 =====
all_strategies = [
    ("RSI超卖(RSI<40)", strategy_rsi_oversold),
    ("RSI超卖+MACD金叉", strategy_rsi_macd),
    ("KDJ金叉", strategy_kdj_golden),
    ("KDJ金叉+RSI偏低", strategy_kdj_rsi),
    ("量比>2x放量上涨", strategy_volume_breakout),
    ("量比>2x+趋势向上", strategy_volume_trend),
    ("涨停后回调", strategy_limit_up_pullback),
    ("涨停后缩量回调", strategy_limit_up_shrink),
    ("RSI+KDJ+量能三重过滤", strategy_triple_filter),
    ("MACD金叉+量比+RSI中性", strategy_classic_trend),
    ("布林带下轨反弹", strategy_bollinger_bounce),
    ("缩量企稳(地量地价)", strategy_volume_shrink_bottom),
]

all_results = []
for name, fn in all_strategies:
    print(f"  测试策略: {name}...")
    results = backtest_strategy(df, fn, name)
    all_results.extend(results)
    if results:
        best = max(results, key=lambda x: (x['r30'], x['win_rate']))
        print(f"    → 最佳持有期{best['hold']}天, 交易{best['n']}笔, 胜率{best['win_rate']}%, r30={best['r30']}%, r20={best['r20']}%")
    else:
        print(f"    → 无有效交易")

# 按 r30 排序
all_results.sort(key=lambda x: (x['r30'], x['r25'], x['win_rate']), reverse=True)

print(f"\n{'=' * 120}")
print("【策略排名 TOP 20】(按30%达标率排序)")
print(f"{'#':^3} {'策略':^20} {'持有':^4} {'交易':^5} {'胜率':^7} {'均最大收益':^9} "
      f"{'50%':^7} {'40%':^7} {'30%':^7} {'25%':^7} {'20%':^7}")
print('-' * 120)

for i, r in enumerate(all_results[:20], 1):
    print(f'{i:^3} {r["strategy"]:^18} {r["hold"]:^4} {r["n"]:^5} {r["win_rate"]:>6.1f}% {r["avg_max"]:>8.1f}% '
          f'{r["r50"]:>6.1f}% {r["r40"]:>6.1f}% {r["r30"]:>6.1f}% {r["r25"]:>6.1f}% {r["r20"]:>6.1f}%')

# ===== 找出当前符合条件的推荐股票 =====
print(f"\n{'=' * 80}")
print("【当前推荐股票】(基于TOP策略)")

top_strategies = all_results[:5]  # 取前5个策略
recommendations = []

for code, grp in df.groupby('code'):
    grp = grp.sort_values('date').reset_index(drop=True)
    if len(grp) < 5:
        continue
    last = grp.iloc[-1]
    prev = grp.iloc[-2]
    
    matched = []
    for r in top_strategies:
        strategy_name = r['strategy']
        hold = r['hold']
        # 找到对应的策略函数
        for name, fn in all_strategies:
            if name == strategy_name:
                try:
                    if fn(grp, len(grp) - 1):
                        matched.append(f"{strategy_name}(h{hold})")
                except:
                    pass
                break
    
    if matched:
        recommendations.append({
            'code': code,
            'close': round(last['close'], 2),
            'chg': round(last['price_chg'], 1) if not pd.isna(last['price_chg']) else 0,
            'rsi14': round(last['rsi14'], 1) if last['rsi14'] else None,
            'vol_ratio': round(last['vol_ratio'], 2) if last['vol_ratio'] else None,
            'k9': round(last['k9'], 1) if last['k9'] else None,
            'd9': round(last['d9'], 1) if last['d9'] else None,
            'j9': round(last['j9'], 1) if last['j9'] else None,
            'matched_strategies': matched,
            'match_count': len(matched),
        })

recommendations.sort(key=lambda x: x['match_count'], reverse=True)

print(f"\n符合条件的股票 ({len(recommendations)} 只):")
if recommendations:
    print(f"{'代码':^8} {'收盘':^7} {'涨幅%':^7} {'RSI':^6} {'量比':^6} {'K/D/J':^10} {'匹配策略':^30}")
    print('-' * 100)
    for r in recommendations[:25]:
        kdj_str = f"{r['k9']}/{r['d9']}/{r['j9']}" if r['k9'] else '-'
        strategies_str = ', '.join(r['matched_strategies'][:2])
        print(f"{r['code']:^8} {r['close']:>6.2f} {r['chg']:>6.1f}% {str(r['rsi14']):>5} "
              f"{str(r['vol_ratio']):>5} {kdj_str:>10} {strategies_str[:30]:^30}")

# ===== 保存结果 =====
output = {
    'timestamp': pd.Timestamp.now().isoformat(),
    'total_stocks': df['code'].nunique(),
    'total_kline_rows': len(df),
    'new_stocks_added': added_count,
    'strategy_results': all_results,
    'top5_strategies': all_results[:5],
    'recommendations': recommendations[:30],
    'best_r30': all_results[0]['r30'] if all_results else 0,
    'best_r20': all_results[0]['r20'] if all_results else 0,
    'best_win_rate': all_results[0]['win_rate'] if all_results else 0,
    'best_strategy_name': all_results[0]['strategy'] if all_results else None,
    'best_hold_days': all_results[0]['hold'] if all_results else None,
}

with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2, default=str)

print(f"\n{'=' * 80}")
print(f"✓ 优化完成!")
print(f"  数据库股票总数: {df['code'].nunique()} (新增 {added_count} 只)")
print(f"  测试策略数: {len(all_strategies)}")
print(f"  有效策略组合: {len(all_results)}")
if all_results:
    print(f"  最佳策略: {all_results[0]['strategy']} (持有{all_results[0]['hold']}天)")
    print(f"  最佳30%达标率: {all_results[0]['r30']}%")
    print(f"  最佳20%达标率: {all_results[0]['r20']}%")
    print(f"  最佳胜率: {all_results[0]['win_rate']}%")
    print(f"  推荐股票数: {len(recommendations)}")
print(f"  结果保存: {OUTPUT}")
