# -*- coding: utf-8 -*-
"""
深度量化策略优化系统 V2
目标: 达标率突破50%
策略: 多因子组合 + 止损止盈 + 市场环境筛选 + 时点选择
"""
import sys, os, sqlite3, json, time, math
import numpy as np
import pandas as pd
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'

# ==================== 指标计算 ====================
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
            rsi.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100.0 - (100.0 / (1 + rs)))
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

def calc_ma(closes, n):
    if len(closes) < n:
        return [None] * len(closes)
    return [None] * (n - 1) + [np.mean(closes[i-n+1:i+1]) for i in range(n-1, len(closes))]

def calc_vol_ma(volumes, n=5):
    if len(volumes) < n:
        return [None] * len(volumes)
    return [None] * (n - 1) + [np.mean(volumes[i-n+1:i+1]) for i in range(n-1, len(volumes))]

def calc_kdj(highs, lows, closes, n=9, m1=3, m2=3):
    """计算KDJ"""
    n_h = len(highs)
    kdj_k = [None] * n_h
    kdj_d = [None] * n_h
    kdj_j = [None] * n_h
    
    if n_h < n:
        return kdj_k, kdj_d, kdj_j
    
    rsv = []
    for i in range(n - 1, n_h):
        h = max(highs[i-n+1:i+1])
        l = min(lows[i-n+1:i+1])
        c = closes[i]
        if h == l:
            rsv.append(50)
        else:
            rsv.append((c - l) / (h - l) * 100)
    
    k = 50.0
    d = 50.0
    for i, r in enumerate(rsv):
        k = (2/3) * k + (1/3) * r
        d = (2/3) * d + (1/3) * k
        j = 3 * k - 2 * d
        idx = i + n - 1
        kdj_k[idx] = k
        kdj_d[idx] = d
        kdj_j[idx] = j
    return kdj_k, kdj_d, kdj_j

def calc_bollinger(closes, n=20, k=2):
    """布林带"""
    ma = calc_ma(closes, n)
    bb_up = [None] * len(closes)
    bb_low = [None] * len(closes)
    for i in range(n - 1, len(closes)):
        if ma[i] is not None:
            std = np.std(closes[i-n+1:i+1])
            bb_up[i] = ma[i] + k * std
            bb_low[i] = ma[i] - k * std
    return bb_up, ma, bb_low

def calc_atr(highs, lows, closes, n=14):
    """ATR真实波幅"""
    m = len(closes)
    trs = [0.0] * m
    for i in range(1, m):
        trs[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
    
    atr = [None] * m
    if m > n:
        sm = sum(trs[1:n+1]) / n
        atr[n] = sm
        for i in range(n+1, m):
            sm = (sm * (n - 1) + trs[i]) / n
            atr[i] = sm
    return atr

# ==================== 加载数据 ====================
print("=" * 90)
print("【深度量化策略优化系统 V2】")
print("=" * 90)

t0 = time.time()
conn = sqlite3.connect(DB)
df_all = pd.read_sql('SELECT * FROM kline ORDER BY code, date', conn)
conn.close()

for col in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce')
df_all = df_all.dropna(subset=['close', 'volume']).sort_values(['code', 'date']).reset_index(drop=True)

print(f"数据: {len(df_all)}条, {df_all['code'].nunique()}只股, {df_all['date'].min()}~{df_all['date'].max()}")

# ==================== 计算指标 ====================
print("\n[1/5] 计算技术指标...")
df_list = []
for code, grp in df_all.groupby('code'):
    grp = grp.sort_values('date').reset_index(drop=True)
    closes = grp['close'].tolist()
    volumes = grp['volume'].tolist()
    highs = grp['high'].tolist()
    lows = grp['low'].tolist()
    
    # 价格变化
    grp['price_chg'] = grp['close'].pct_change() * 100
    
    # RSI
    grp['rsi14'] = calc_rsi_full(closes, 14)
    grp['rsi6'] = calc_rsi_full(closes, 6)
    
    # MACD
    dif, dea, macd_bar = calc_macd(closes)
    grp['dif'] = dif
    grp['dea'] = dea
    grp['macd_bar'] = macd_bar
    
    # 均线
    grp['ma5'] = calc_ma(closes, 5)
    grp['ma10'] = calc_ma(closes, 10)
    grp['ma20'] = calc_ma(closes, 20)
    grp['ma60'] = calc_ma(closes, 60)
    
    # 量比
    grp['vol_ma5'] = calc_vol_ma(volumes, 5)
    grp['vol_ma10'] = calc_vol_ma(volumes, 10)
    grp['vol_ratio'] = grp['volume'] / grp['vol_ma5']
    grp['vol_ratio10'] = grp['volume'] / grp['vol_ma10']
    
    # KDJ
    kdj_k, kdj_d, kdj_j = calc_kdj(highs, lows, closes)
    grp['kdj_k'] = kdj_k
    grp['kdj_d'] = kdj_d
    grp['kdj_j'] = kdj_j
    
    # 布林带
    bb_up, ma20, bb_low = calc_bollinger(closes, 20)
    grp['bb_up'] = bb_up
    grp['bb_mid'] = ma20
    grp['bb_low'] = bb_low
    
    # ATR
    atr = calc_atr(highs, lows, closes)
    grp['atr14'] = atr
    
    # 换手率(使用turnover列)
    grp['turnover_rate'] = grp['turnover']
    
    # 相对位置
    bb_poses = []
    for i, c in enumerate(closes):
        if bb_up[i] and bb_low[i] and bb_up[i] != bb_low[i]:
            bb_poses.append((c - bb_low[i]) / (bb_up[i] - bb_low[i]))
        else:
            bb_poses.append(0.5)
    grp['bb_pos'] = bb_poses
    
    # 5日均线多头排列
    ma_goldens = []
    for i in range(len(grp)):
        if grp['ma5'].iloc[i] and grp['ma10'].iloc[i] and grp['ma5'].iloc[i] > grp['ma10'].iloc[i]:
            ma_goldens.append(1)
        else:
            ma_goldens.append(0)
    grp['ma_golden'] = ma_goldens
    
    # 连续上涨天数
    up_streaks = [0]
    for i in range(1, len(grp)):
        if grp['price_chg'].iloc[i] > 0:
            up_streaks.append(up_streaks[-1] + 1)
        else:
            up_streaks.append(0)
    grp['up_streak'] = up_streaks
    
    # 成交量趋势
    vol_trends = [0.0] * len(grp)
    for i in range(5, len(grp)):
        recent = grp['volume'].iloc[i-4:i+1].mean()
        older = grp['volume'].iloc[i-9:i-4].mean()
        if older > 0:
            vol_trends[i] = recent / older - 1
    grp['vol_trend'] = vol_trends
    
    df_list.append(grp)

df = pd.concat(df_list, ignore_index=True)
print(f"指标计算完成, 总行: {len(df)}, 耗时: {time.time()-t0:.1f}s")

# 构建大盘指数(用所有股票平均)
daily_index = df.groupby('date').agg({
    'close': 'mean',
    'volume': 'sum'
}).reset_index().sort_values('date')
daily_index['index_chg'] = daily_index['close'].pct_change() * 100
index_map = dict(zip(daily_index['date'], daily_index['index_chg']))
df['index_chg'] = df['date'].map(index_map)
df['rel_strength'] = df['price_chg'] - df['index_chg']  # 相对大盘强弱

# ==================== 策略回测引擎 ====================
def backtest(params, df_data):
    """
    返回: (达标率字典, 交易列表)
    """
    hold_days = params['hold_days']
    chg_min = params['chg_min']
    chg_max = params['chg_max']
    price_max = params['price_max']
    price_min = params.get('price_min', 0)
    turnover_min = params.get('turnover_min', 0)
    
    # 因子开关
    factor_rsi = params.get('factor_rsi', None)  # (min, max) or None
    factor_macd = params.get('factor_macd', None)  # 'gold','above_zero','cross_up','bar_pos','none'
    factor_vol = params.get('factor_vol', None)  # min ratio
    factor_kdj = params.get('factor_kdj', None)  # 'golden','above_20','below_80'
    factor_bb = params.get('factor_bb', None)  # 'lower_third','middle','none'
    factor_up = params.get('factor_up', None)  # max up_streak
    
    # 止损止盈
    stop_loss = params.get('stop_loss', None)  # e.g. -0.05
    stop_win = params.get('stop_win', None)     # e.g. 0.20
    use_stop = stop_loss is not None or stop_win is not None
    
    # 市场环境
    market_filter = params.get('market_filter', None)  # 'up'/'down'/'any'
    
    # 时点选择
    timing_filter = params.get('timing', None)  # 'month_start','week_start','none'
    
    trades = []
    
    for code, grp in df_data.groupby('code'):
        grp = grp.reset_index(drop=True)
        if len(grp) < hold_days + 40:
            continue
        
        tail = grp.tail(200).reset_index(drop=True)
        
        for i in range(30, len(tail) - hold_days - 2):
            row = tail.iloc[i]
            prev = tail.iloc[i-1]
            date = row['date']
            
            # 日期格式检查
            if not isinstance(date, str):
                date_str = str(date)
            else:
                date_str = date
            
            # 时点筛选
            if timing_filter == 'month_start':
                day = int(date_str[-2:]) if len(date_str) >= 2 else 0
                if day > 5:
                    continue
            elif timing_filter == 'week_start':
                try:
                    from datetime import datetime
                    d = datetime.strptime(date_str[:10], '%Y-%m-%d')
                    if d.weekday() not in [0, 1]:
                        continue
                except:
                    pass
            
            # 市场环境筛选
            idx_chg = row['index_chg'] if not pd.isna(row.get('index_chg')) else 0
            if market_filter == 'up' and idx_chg < 0:
                continue
            elif market_filter == 'down' and idx_chg > 0:
                continue
            
            # 基础条件
            chg = row['price_chg'] if not pd.isna(row['price_chg']) else 0
            close = row['close']
            
            if not (chg_min <= chg <= chg_max):
                continue
            if close < price_min or close > price_max:
                continue
            
            # 换手率筛选
            tr = row.get('turnover_rate', None)
            if turnover_min > 0 and (tr is None or pd.isna(tr) or tr < turnover_min):
                continue
            
            # RSI因子
            if factor_rsi is not None:
                rsi = row['rsi14']
                if rsi is None or rsi < factor_rsi[0] or rsi > factor_rsi[1]:
                    continue
            
            # MACD因子
            if factor_macd and factor_macd != 'none':
                dif_i = row['dif']
                dea_i = row['dea']
                dif_p = prev['dif']
                macd_i = row['macd_bar']
                macd_p = prev['macd_bar']
                
                if factor_macd == 'gold':
                    if not (dif_i is not None and dea_i is not None and dif_p is not None and
                            dif_p < dea_i and dif_i > dea_i and dif_i > 0):
                        continue
                elif factor_macd == 'above_zero':
                    if not (dif_i is not None and dif_i > 0):
                        continue
                elif factor_macd == 'cross_up':
                    if not (macd_i is not None and macd_p is not None and macd_p < 0 and macd_i > 0):
                        continue
                elif factor_macd == 'bar_pos':
                    if not (macd_i is not None and macd_i > 0):
                        continue
            
            # KDJ因子
            if factor_kdj and factor_kdj != 'none':
                kdj_k = row['kdj_k']
                kdj_d = row['kdj_d']
                kdj_j = row['kdj_j']
                kdjk_p = prev['kdj_k']
                kdjd_p = prev['kdj_d']
                
                if factor_kdj == 'golden':
                    if not (kdj_k is not None and kdj_d is not None and kdjk_p is not None and kdjd_p is not None and
                            kdjk_p < kdjd_p and kdj_k > kdj_d and kdj_k > 20):
                        continue
                elif factor_kdj == 'above_20':
                    if not (kdj_k is not None and kdj_k > 20):
                        continue
                elif factor_kdj == 'below_80':
                    if not (kdj_k is not None and kdj_k < 80):
                        continue
            
            # 布林带因子
            if factor_bb and factor_bb != 'none':
                bb_pos = row['bb_pos']
                if factor_bb == 'lower_third':
                    if not (bb_pos is not None and bb_pos < 0.33):
                        continue
                elif factor_bb == 'middle':
                    if not (bb_pos is not None and 0.33 <= bb_pos <= 0.66):
                        continue
            
            # 连续上涨
            if factor_up is not None:
                up_s = row['up_streak']
                if up_s > factor_up:
                    continue
            
            # 成交量因子
            if factor_vol is not None:
                vr = row['vol_ratio']
                if vr is None or vr < factor_vol:
                    continue
            
            # ========== 计算收益 ==========
            buy_price = row['close']
            future_closes = tail.iloc[i+1:i+hold_days+1]['close'].tolist()
            if not future_closes:
                continue
            
            # 简单持有收益
            final_ret = (future_closes[-1] - buy_price) / buy_price
            
            # 带止损止盈的收益
            if use_stop:
                actual_ret = 0
                hit_stop = None
                for j, fp in enumerate(future_closes):
                    ret = (fp - buy_price) / buy_price
                    if stop_loss is not None and ret <= stop_loss:
                        actual_ret = stop_loss
                        hit_stop = f'止损-{j+1}天'
                        break
                    if stop_win is not None and ret >= stop_win:
                        actual_ret = stop_win
                        hit_stop = f'止盈-{j+1}天'
                        break
                if hit_stop is None:
                    actual_ret = final_ret
                    hit_stop = f'持有到期'
            else:
                actual_ret = final_ret
                hit_stop = f'持有到期'
            
            # 期间最大收益
            max_ret = (max(future_closes) - buy_price) / buy_price
            
            trades.append({
                'ret_max': max_ret * 100,
                'ret_final': actual_ret * 100,
                'hold': hold_days,
            })
    
    if len(trades) < 10:
        return None, trades
    
    pnls_max = [t['ret_max'] for t in trades]
    pnls_final = [t['ret_final'] for t in trades]
    wins = sum(1 for p in pnls_final if p > 0)
    
    def hit(threshold):
        return sum(1 for p in pnls_max if p >= threshold) / len(trades) * 100
    
    return {
        'n': len(trades),
        'win_rate': wins / len(trades) * 100,
        'avg_max': np.mean(pnls_max),
        'avg_final': np.mean(pnls_final),
        'max_pnl': max(pnls_max),
        'r50': hit(50),
        'r40': hit(40),
        'r30': hit(30),
        'r25': hit(25),
        'r20': hit(20),
        'r15': hit(15),
        'r10': hit(10),
    }, trades

# ==================== 参数网格 ====================
print("\n[2/5] 构建参数网格...")

# 基础参数
hold_days_list = [14, 18, 21, 25, 30]
chg_configs = [
    (3, 8), (5, 10), (6, 12), (8, 12), (8, 15), (10, 15), (3, 12), (5, 12), (5, 15)
]
price_configs = [
    (0, 10), (0, 12), (0, 15), (3, 10), (3, 12)
]
turnover_configs = [0, 2, 3, 5]  # 换手率下限%

# 因子组合
factor_combos = [
    # 基准(无因子)
    {},
    # MACD系列
    {'macd': 'gold'},
    {'macd': 'above_zero'},
    {'macd': 'cross_up'},
    {'macd': 'bar_pos'},
    # RSI系列
    {'rsi': (30, 70)},
    {'rsi': (35, 65)},
    {'rsi': (40, 60)},
    {'rsi': (45, 70)},
    {'rsi': (40, 70)},
    # MACD+RSI组合
    {'macd': 'gold', 'rsi': (30, 70)},
    {'macd': 'gold', 'rsi': (35, 65)},
    {'macd': 'above_zero', 'rsi': (40, 70)},
    {'macd': 'cross_up', 'rsi': (30, 60)},
    # 量比系列
    {'vol': 1.2},
    {'vol': 1.5},
    {'vol': 2.0},
    # MACD+量比
    {'macd': 'gold', 'vol': 1.2},
    {'macd': 'gold', 'vol': 1.5},
    {'macd': 'above_zero', 'vol': 1.5},
    # RSI+量比
    {'rsi': (35, 65), 'vol': 1.2},
    {'rsi': (40, 70), 'vol': 1.5},
    # 三合一
    {'macd': 'gold', 'rsi': (35, 65), 'vol': 1.2},
    {'macd': 'above_zero', 'rsi': (40, 70), 'vol': 1.2},
    {'macd': 'cross_up', 'rsi': (30, 60), 'vol': 1.5},
    {'macd': 'gold', 'rsi': (40, 70), 'vol': 1.0},
    # KDJ系列
    {'kdj': 'golden'},
    {'kdj': 'above_20'},
    {'kdj': 'above_20', 'rsi': (30, 70)},
    {'kdj': 'golden', 'macd': 'gold'},
    # 布林带
    {'bb': 'lower_third'},
    {'bb': 'lower_third', 'vol': 1.2},
    {'bb': 'lower_third', 'macd': 'gold'},
    {'bb': 'lower_third', 'rsi': (35, 65)},
    # 连续上涨过滤
    {'up_limit': 2},
    {'up_limit': 3},
    {'macd': 'gold', 'up_limit': 2},
    # 相对强弱
    {'rel_strength': True},  # 需要rel_strength > 0
    {'macd': 'gold', 'rel_strength': True},
]

# 止损止盈配置
stop_configs = [
    (None, None),          # 无止损止盈
    (-0.05, 0.25),         # -5%止损, +25%止盈
    (-0.05, 0.30),         # -5%止损, +30%止盈
    (-0.03, 0.20),         # -3%止损, +20%止盈
    (-0.03, 0.25),         # -3%止损, +25%止盈
    (-0.08, None),         # -8%止损, 无止盈
    (-0.05, 0.20),         # -5%止损, +20%止盈
    (-0.03, 0.30),         # -3%止损, +30%止盈
]

# 市场环境
market_configs = [None, 'up', 'any']

# 时点选择
timing_configs = [None, 'month_start', 'week_start']

# 生成所有组合
all_configs = []
for hold in hold_days_list:
    for chg_min, chg_max in chg_configs:
        for pmin, pmax in price_configs:
            for turn_min in turnover_configs:
                for factors in factor_combos:
                    for stop_loss, stop_win in stop_configs:
                        for market in market_configs:
                            for timing in timing_configs:
                                params = {
                                    'hold_days': hold,
                                    'chg_min': chg_min,
                                    'chg_max': chg_max,
                                    'price_min': pmin,
                                    'price_max': pmax,
                                    'turnover_min': turn_min / 100.0,
                                    'stop_loss': stop_loss,
                                    'stop_win': stop_win,
                                    'market_filter': market,
                                    'timing': timing,
                                }
                                # 添加因子
                                for k, v in factors.items():
                                    if k == 'macd':
                                        params['factor_macd'] = v
                                    elif k == 'rsi':
                                        params['factor_rsi'] = v
                                    elif k == 'vol':
                                        params['factor_vol'] = v
                                    elif k == 'kdj':
                                        params['factor_kdj'] = v
                                    elif k == 'bb':
                                        params['factor_bb'] = v
                                    elif k == 'up_limit':
                                        params['factor_up'] = v
                                    elif k == 'rel_strength':
                                        params['factor_rel'] = v
                                all_configs.append(params)

print(f"总参数组合: {len(all_configs)}")

# ==================== 批量回测 ====================
print("\n[3/5] 批量回测中...")
t1 = time.time()
all_results = []
batch_size = 200
total = len(all_configs)

for batch_start in range(0, total, batch_size):
    batch_end = min(batch_start + batch_size, total)
    for params in all_configs[batch_start:batch_end]:
        # 快速检查市场+时点+止损止盈的组合
        stats, trades = backtest(params, df)
        if stats and stats['n'] >= 10:
            result = dict(params)
            result.update({
                'n': stats['n'],
                'win': stats['win_rate'],
                'avg_max': stats['avg_max'],
                'avg_final': stats['avg_final'],
                'max_pnl': stats['max_pnl'],
                'r50': stats['r50'],
                'r40': stats['r40'],
                'r30': stats['r30'],
                'r25': stats['r25'],
                'r20': stats['r20'],
            })
            all_results.append(result)
    
    elapsed = time.time() - t1
    pct = batch_end / total * 100
    eta = elapsed / batch_end * (total - batch_end) if batch_end > 0 else 0
    print(f"  进度: {batch_end}/{total} ({pct:.1f}%) | 已找到有效策略: {len(all_results)} | 耗时: {elapsed:.0f}s | ETA: {eta:.0f}s")

print(f"\n回测完成! 有效策略: {len(all_results)}/{total} | 总耗时: {time.time()-t1:.0f}s")

# ==================== 结果分析 ====================
print("\n[4/5] 分析结果...")

# 按不同指标排序
all_results.sort(key=lambda x: (x['r50'], x['r40'], x['avg_max']), reverse=True)

# TOP20 50%达标率
print("\n" + "=" * 100)
print("【TOP20 策略 - 按50%达标率排序】")
print(f"{'#':^3} {'持有':^4} {'涨幅':^8} {'价格':^8} {'换手':^5} {'因子组合':^30} "
      f"{'止损':^8} {'止盈':^8} {'市场':^6} {'时点':^8} "
      f"{'N':^5} {'胜率':^6} {'均收益':^7} "
      f"{'50%':^6} {'40%':^6} {'30%':^6} {'25%':^6} {'20%':^6}")
print('-' * 160)

for i, r in enumerate(all_results[:30], 1):
    # 构建因子字符串
    factor_parts = []
    if r.get('factor_macd'):
        factor_parts.append(f"M{r['factor_macd']}")
    if r.get('factor_rsi'):
        factor_parts.append(f"R{r['factor_rsi']}")
    if r.get('factor_vol'):
        factor_parts.append(f"V{r['factor_vol']}")
    if r.get('factor_kdj'):
        factor_parts.append(f"K{r['factor_kdj']}")
    if r.get('factor_bb'):
        factor_parts.append(f"B{r['factor_bb']}")
    if r.get('factor_up'):
        factor_parts.append(f"U{r['factor_up']}")
    if r.get('factor_rel'):
        factor_parts.append("Rel")
    factor_str = '+'.join(factor_parts) if factor_parts else 'NONE'
    if len(factor_str) > 30:
        factor_str = factor_str[:30]
    
    stop_loss_s = f"{r['stop_loss']*100:.0f}%" if r['stop_loss'] else '-'
    stop_win_s = f"{r['stop_win']*100:.0f}%" if r['stop_win'] else '-'
    market_s = r['market_filter'] or 'ALL'
    timing_s = r['timing'] or 'ANY'
    turn_s = f"{r['turnover_min']*100:.0f}%" if r['turnover_min'] > 0 else '-'
    
    print(f'{i:^3} {r["hold_days"]:^4} {r["chg_min"]}-{r["chg_max"]:^4} {r["price_min"]}-{r["price_max"]:^5} {turn_s:^5} '
          f'{factor_str:^30} {stop_loss_s:^8} {stop_win_s:^8} {market_s:^6} {timing_s:^8} '
          f'{r["n"]:^5} {r["win"]:>5.1f}% {r["avg_max"]:>6.1f}% '
          f'{r["r50"]:>5.1f}% {r["r40"]:>5.1f}% {r["r30"]:>5.1f}% {r["r25"]:>5.1f}% {r["r20"]:>5.1f}%')

# TOP10 40%达标率
all_results.sort(key=lambda x: (x['r40'], x['r30'], x['avg_max']), reverse=True)
print("\n" + "=" * 100)
print("【TOP10 策略 - 按40%达标率排序】")
for i, r in enumerate(all_results[:10], 1):
    print(f"  #{i} 持有{r['hold_days']}天 涨幅{r['chg_min']}-{r['chg_max']}% 价格{r['price_min']}-{r['price_max']}元 "
          f"换手{'>='+str(int(r['turnover_min']*100))+'%' if r['turnover_min']>0 else '无限制'} "
          f"止损{r['stop_loss']} 止盈{r['stop_win']} "
          f"市场{r['market_filter'] or 'ALL'} 时点{r['timing'] or 'ANY'} "
          f"N={r['n']} 胜率{r['win']:.1f}% 均收益{r['avg_max']:.1f}% "
          f"50%={r['r50']:.1f}% 40%={r['r40']:.1f}% 30%={r['r30']:.1f}% 25%={r['r25']:.1f}%")

# 达标率分布
print("\n" + "=" * 80)
print("【达标率分布】")
bins = [(50, '50%+'), (40, '40%+'), (30, '30%+'), (25, '25%+'), (20, '20%+')]
for threshold, label in bins:
    key = f'r{threshold}'
    count = sum(1 for r in all_results if r[key] >= threshold)
    avg_n = np.mean([r['n'] for r in all_results if r[key] >= threshold]) if count > 0 else 0
    print(f"  {label:6} 达标: {count:>4} 个策略 ({count/len(all_results)*100:.1f}%), 平均交易次数: {avg_n:.0f}")

# 最佳策略深度分析
best = all_results[0]
print("\n" + "=" * 80)
print("【🏆 最佳策略详情】")
print(f"  持有天数:    {best['hold_days']}天")
print(f"  买入涨幅:    {best['chg_min']}-{best['chg_max']}%")
print(f"  价格区间:    {best['price_min']}-{best['price_max']}元")
print(f"  换手率:      {'>='+str(int(best['turnover_min']*100))+'%' if best['turnover_min']>0 else '无限制'}")
print(f"  止损:        {best['stop_loss'] if best['stop_loss'] else '无'}")
print(f"  止盈:        {best['stop_win'] if best['stop_win'] else '无'}")
print(f"  市场筛选:    {best['market_filter'] or '无限制'}")
print(f"  时点选择:    {best['timing'] or '无限制'}")
macd_val = best.get('factor_macd', '无')
rsi_val = best.get('factor_rsi', None)
vol_val = best.get('factor_vol', None)
kdj_val = best.get('factor_kdj', None)
bb_val = best.get('factor_bb', None)
up_val = best.get('factor_up', None)
rel_val = best.get('factor_rel', None)
print(f"  MACD因子:    {macd_val}")
print(f"  RSI因子:     {rsi_val if rsi_val else '无'}")
print(f"  量比因子:    {vol_val if vol_val else '无'}")
print(f"  KDJ因子:     {kdj_val if kdj_val else '无'}")
print(f"  布林带因子:  {bb_val if bb_val else '无'}")
print(f"  上涨限制:    {up_val if up_val else '无'}")
print(f"  相对强弱:    {'是' if rel_val else '否'}")
print(f"  交易次数:    {best['n']}")
print(f"  胜率:        {best['win']:.1f}%")
print(f"  平均最大收益:{best['avg_max']:.1f}%")
print(f"  50%达标率:   {best['r50']:.1f}% {'🎯' if best['r50'] >= 50 else ''}")
print(f"  40%达标率:   {best['r40']:.1f}%")
print(f"  30%达标率:   {best['r30']:.1f}%")
print(f"  25%达标率:   {best['r25']:.1f}%")
print(f"  20%达标率:   {best['r20']:.1f}%")

# ==================== 策略对比分析 ====================
print("\n" + "=" * 80)
print("【分维度效果分析】")

# 按持有天数分析
print("\n按持有天数:")
for hold in sorted(set(r['hold_days'] for r in all_results)):
    subset = [r for r in all_results if r['hold_days'] == hold]
    best_s = max(subset, key=lambda x: x['r50'])
    avg_r50 = np.mean([r['r50'] for r in subset])
    print(f"  {hold}天: 最佳50%达标率={best_s['r50']:.1f}%, 平均={avg_r50:.1f}%")

# 按止损止盈分析
print("\n按止损止盈配置:")
for sl, sw in sorted(set((r['stop_loss'], r['stop_win']) for r in all_results)):
    subset = [r for r in all_results if r['stop_loss'] == sl and r['stop_win'] == sw]
    best_s = max(subset, key=lambda x: x['r50'])
    avg_r50 = np.mean([r['r50'] for r in subset])
    sl_s = f"{sl*100:.0f}%" if sl else '无'
    sw_s = f"{sw*100:.0f}%" if sw else '无'
    print(f"  止损{sl_s} 止盈{sw_s}: 最佳50%={best_s['r50']:.1f}%, 平均={avg_r50:.1f}%")

# 按因子组合分析
print("\n按因子组合(TOP10最有效):")
factor_scores = defaultdict(lambda: {'r50_sum': 0, 'count': 0, 'r50_max': 0})
for r in all_results:
    parts = []
    if r.get('factor_macd'): parts.append('M')
    if r.get('factor_rsi'): parts.append('R')
    if r.get('factor_vol'): parts.append('V')
    if r.get('factor_kdj'): parts.append('K')
    if r.get('factor_bb'): parts.append('B')
    key = '+'.join(parts) if parts else 'NONE'
    factor_scores[key]['r50_sum'] += r['r50']
    factor_scores[key]['count'] += 1
    factor_scores[key]['r50_max'] = max(factor_scores[key]['r50_max'], r['r50'])

sorted_factors = sorted(factor_scores.items(), key=lambda x: x[1]['r50_max'], reverse=True)
for name, s in sorted_factors[:10]:
    avg = s['r50_sum'] / s['count'] if s['count'] > 0 else 0
    print(f"  {name}: 最优={s['r50_max']:.1f}%, 平均={avg:.1f}%, 样本数={s['count']}")

# ==================== 保存结果 ====================
print("\n[5/5] 保存结果...")

output = {
    'summary': {
        'total_combinations': total,
        'valid_strategies': len(all_results),
        'best_r50': best['r50'],
        'best_r40': best['r40'],
        'best_r30': best['r30'],
        'best_strategy': best,
        'runtime_seconds': time.time() - t0,
    },
    'top50_by_r50': all_results[:50],
    'top50_by_r40': sorted(all_results, key=lambda x: (x['r40'], x['r30']), reverse=True)[:50],
    'all_results': all_results,
}

with open('data/deep_optimize_v2_results.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2, default=str)

print(f"\n✅ 优化完成!")
print(f"✅ 测试策略数: {total}")
print(f"✅ 有效策略数: {len(all_results)}")
print(f"🏆 最佳50%达标率: {best['r50']:.1f}%")
print(f"🏆 最佳40%达标率: {best['r40']:.1f}%")
print(f"🏆 最佳30%达标率: {best['r30']:.1f}%")
print(f"⏱️ 总耗时: {time.time()-t0:.0f}秒")
print(f"💾 结果已保存到 data/deep_optimize_v2_results.json")

# ==================== 明日推荐 ====================
print("\n" + "=" * 80)
print("【明日推荐股票 - 使用最佳策略】")

# 构建最佳策略参数
best_params = best.copy()
recommendations = []

for code, grp in df.groupby('code'):
    grp = grp.sort_values('date').reset_index(drop=True)
    if len(grp) < 5:
        continue
    last = grp.iloc[-1]
    prev = grp.iloc[-2]
    
    # 基础条件
    chg = last['price_chg'] if not pd.isna(last['price_chg']) else 0
    if not (best_params['chg_min'] <= chg <= best_params['chg_max']):
        continue
    close = last['close']
    if close < best_params['price_min'] or close > best_params['price_max']:
        continue
    
    # 因子筛选
    skip = False
    if best_params.get('factor_macd') == 'gold':
        dif_i = last['dif']
        dea_i = last['dea']
        dif_p = prev['dif']
        if not (dif_i is not None and dea_i is not None and dif_p is not None and
                dif_p < dea_i and dif_i > dea_i and dif_i > 0):
            skip = True
    elif best_params.get('factor_macd') == 'above_zero':
        if not (last['dif'] is not None and last['dif'] > 0):
            skip = True
    elif best_params.get('factor_macd') == 'bar_pos':
        if not (last['macd_bar'] is not None and last['macd_bar'] > 0):
            skip = True
    
    if best_params.get('factor_rsi'):
        rsi_min, rsi_max = best_params['factor_rsi']
        rsi = last['rsi14']
        if rsi is None or rsi < rsi_min or rsi > rsi_max:
            skip = True
    
    if best_params.get('factor_vol'):
        vr = last['vol_ratio']
        if vr is None or vr < best_params['factor_vol']:
            skip = True
    
    if best_params.get('factor_up'):
        if last['up_streak'] > best_params['factor_up']:
            skip = True
    
    if skip:
        continue
    
    recommendations.append({
        'code': code,
        'close': round(float(close), 2),
        'chg': round(float(chg), 2),
        'rsi14': round(float(last['rsi14']), 1) if last['rsi14'] else None,
        'vol_ratio': round(float(last['vol_ratio']), 2) if last['vol_ratio'] else None,
        'dif': round(float(last['dif']), 3) if last['dif'] else None,
        'macd_bar': round(float(last['macd_bar']), 3) if last['macd_bar'] else None,
        'kdj_k': round(float(last['kdj_k']), 1) if last['kdj_k'] else None,
        'up_streak': int(last['up_streak']) if not pd.isna(last.get('up_streak')) else 0,
    })

# 按RSI中等偏低排序
def sort_key(r):
    if r['rsi14'] is not None:
        return abs(50 - r['rsi14'])
    return 999

recommendations.sort(key=sort_key)
print(f"\n符合条件的股票 ({len(recommendations)} 只):")
if recommendations:
    print(f"{'代码':^8} {'收盘':^7} {'涨幅%':^6} {'RSI':^6} {'量比':^6} {'DIF':^7} {'MACD柱':^8} {'KDJ_K':^7} {'连涨':^5}")
    print('-' * 70)
    for r in recommendations[:30]:
        print(f"{r['code']:^8} {r['close']:>6.2f} {r['chg']:>5.1f}% {str(r['rsi14']):>6} "
              f"{str(r['vol_ratio']):>6} {str(r['dif']):>7} {str(r['macd_bar']):>8} "
              f"{str(r['kdj_k']):>7} {r['up_streak']:^5}")
else:
    print("当前无股票完全符合条件，可考虑放宽参数")
    # 放宽条件搜索
    relaxed = []
    for code, grp in df.groupby('code'):
        grp = grp.sort_values('date').reset_index(drop=True)
        if len(grp) < 5:
            continue
        last = grp.iloc[-1]
        chg = last['price_chg'] if not pd.isna(last['price_chg']) else 0
        if 3 <= chg <= 15:
            close = last['close']
            if close <= best_params['price_max']:
                relaxed.append({
                    'code': code,
                    'close': round(float(close), 2),
                    'chg': round(float(chg), 2),
                    'rsi14': round(float(last['rsi14']), 1) if last['rsi14'] else None,
                })
    relaxed.sort(key=lambda x: x['chg'], reverse=True)
    print(f"\n放宽条件后 ({len(relaxed)} 只, 涨幅3-15%, 价格≤{best_params['price_max']}元):")
    for r in relaxed[:20]:
        print(f"  {r['code']}: {r['close']}元, 涨幅{r['chg']}%, RSI={r['rsi14']}")

print("\n" + "=" * 80)
