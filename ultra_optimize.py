# -*- coding: utf-8 -*-
"""
量化系统极限优化 - 目标突破50%达标率
探索更宽泛参数空间:
1. 无量比筛选（扩大样本）
2. 更宽涨幅区间
3. 多RSI窗口组合
4. 多MACD条件组合
5. 极低价格筛选
6. 持有天数细分
"""
import sys, os, sqlite3, json, math
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'

# ===== 技术指标 =====
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

def calc_rsi6(closes):
    return calc_rsi_full(closes, 6)

def calc_rsi9(closes):
    return calc_rsi_full(closes, 9)

def calc_ema(series, n):
    if len(series) < n:
        return [None] * len(series)
    k = 2.0 / (n + 1)
    ema = [None] * (n - 1)
    ema.append(float(series[n - 1]))
    for i in range(n, len(series)):
        ema.append(float(series[i]) * k + ema[-1] * (1 - k))
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
    
    k = 2.0 / (signal + 1)
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
            macd_bar[i] = (dif[i] - dea[i]) * 2.0
    return dif, dea, macd_bar

def calc_ma(closes, n):
    if len(closes) < n:
        return [None] * len(closes)
    return [None] * (n - 1) + [float(np.mean(closes[i-n+1:i+1])) for i in range(n-1, len(closes))]

def calc_vol_ma(volumes, n=5):
    if len(volumes) < n:
        return [None] * len(volumes)
    return [None] * (n - 1) + [float(np.mean(volumes[i-n+1:i+1])) for i in range(n-1, len(volumes))]

# ===== 加载数据 =====
print("=" * 80)
print("【量化系统极限优化】 - 目标突破50%达标率")
print("=" * 80)

conn = sqlite3.connect(DB)
df_raw = pd.read_sql('SELECT code, date, open, high, low, close, volume, turnover FROM kline ORDER BY code, date', conn)
conn.close()

for col in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
    df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')

df_raw = df_raw.sort_values(['code', 'date']).reset_index(drop=True)
print(f"总记录: {len(df_raw)} | 股票数: {df_raw['code'].nunique()} | 日期: {df_raw['date'].min()} ~ {df_raw['date'].max()}")

# ===== 计算指标 =====
print("\n[1/5] 计算技术指标...")
dfs = []
for code, grp in df_raw.groupby('code'):
    grp = grp.sort_values('date').reset_index(drop=True)
    closes = grp['close'].tolist()
    volumes = grp['volume'].tolist()
    
    grp['rsi14'] = calc_rsi_full(closes, 14)
    grp['rsi6'] = calc_rsi6(closes)
    grp['rsi9'] = calc_rsi9(closes)
    dif, dea, macd_bar = calc_macd(closes)
    grp['dif'] = dif
    grp['dea'] = dea
    grp['macd_bar'] = macd_bar
    grp['ma5'] = calc_ma(closes, 5)
    grp['ma10'] = calc_ma(closes, 10)
    grp['ma20'] = calc_ma(closes, 20)
    grp['vol_ma5'] = calc_vol_ma(volumes, 5)
    grp['vol_ma10'] = calc_vol_ma(volumes, 10)
    grp['price_chg'] = grp['close'].pct_change() * 100
    grp['vol_ratio'] = grp['volume'] / grp['vol_ma5']
    grp['vol_ratio10'] = grp['volume'] / grp['vol_ma10']
    
    # MA多头排列
    grp['ma_bull'] = ((grp['ma5'] > grp['ma10']) & (grp['ma10'] > grp['ma20']))
    
    dfs.append(grp)

df = pd.concat(dfs, ignore_index=True)
print(f"指标计算完成: {len(df)} 行")

# ===== 策略回测函数 =====
def backtest(params, df):
    hold = params['hold']
    chg_min = params['chg_min']
    chg_max = params['chg_max']
    pmax = params['pmax']
    pmin = params.get('pmin', 1)
    rsi_enabled = params.get('rsi_enabled', False)
    rsi_min = params.get('rsi_min', 30)
    rsi_max = params.get('rsi_max', 70)
    rsi_period = params.get('rsi_period', 14)
    macd_cond = params.get('macd', None)  # None, 'gold', 'above_zero', 'cross_up', 'gold_above_zero'
    vol_min = params.get('vol_min', None)  # None = no filter
    ma_bull_req = params.get('ma_bull', False)
    rsi6_max = params.get('rsi6_max', None)
    dif_above_req = params.get('dif_above', None)  # e.g. 0.05
    
    trades = []
    for code, grp in df.groupby('code'):
        grp = grp.reset_index(drop=True)
        if len(grp) < hold + 35:
            continue
        tail = grp.tail(150).reset_index(drop=True)
        
        for i in range(25, len(tail) - hold - 1):
            row = tail.iloc[i]
            
            # 基础条件
            chg = row['price_chg'] if not pd.isna(row['price_chg']) else 0.0
            if not (chg_min <= chg <= chg_max):
                continue
            price = row['close']
            if not (pmin <= price <= pmax):
                continue
            
            # RSI条件
            if rsi_enabled:
                rsi_col = f'rsi{rsi_period}'
                rsi_val = row[rsi_col]
                if rsi_val is None or rsi_val < rsi_min or rsi_val > rsi_max:
                    continue
            
            # RSI6上限
            if rsi6_max is not None:
                rsi6 = row['rsi6']
                if rsi6 is None or rsi6 > rsi6_max:
                    continue
            
            # MACD条件
            if macd_cond is not None:
                dif_i = row['dif']
                dea_i = row['dea']
                dif_prev = tail.iloc[i-1]['dif']
                dea_prev = tail.iloc[i-1]['dea']
                macd_i = row['macd_bar']
                macd_prev = tail.iloc[i-1]['macd_bar']
                
                if macd_cond == 'gold':
                    if not (dif_i is not None and dea_i is not None and dif_prev is not None and
                            dif_prev < dea_i and dif_i > dea_i and dif_i > 0):
                        continue
                elif macd_cond == 'above_zero':
                    if not (dif_i is not None and dif_i > 0):
                        continue
                elif macd_cond == 'cross_up':
                    if not (macd_i is not None and macd_prev is not None and
                            macd_prev < 0 and macd_i > 0):
                        continue
                elif macd_cond == 'gold_above_zero':
                    # DIF金叉DEA且DIF>0更严格
                    if not (dif_i is not None and dea_i is not None and dif_prev is not None and
                            dif_prev < dea_i and dif_i > dea_i and dif_i > 0):
                        continue
                elif macd_cond == 'dea_above_zero':
                    # DEA>0 在0轴上方
                    if not (dea_i is not None and dea_i > 0):
                        continue
                elif macd_cond == 'dif_above_macd':
                    # DIF从下方接近DEA但未金叉
                    if not (dif_i is not None and dea_i is not None and
                            0 < dif_i - dea_i < 0.1):
                        continue
                elif macd_cond == 'macd_strong':
                    # MACD柱>0 且 DIF>DEA
                    if not (macd_i is not None and macd_i > 0):
                        continue
            
            # DIF绝对值过滤
            if dif_above_req is not None:
                if dif_i is None or dif_i < dif_above_req:
                    continue
            
            # 成交量放大
            if vol_min is not None:
                vr = row['vol_ratio']
                if vr is None or vr < vol_min:
                    continue
            
            # MA多头排列
            if ma_bull_req:
                if not row['ma_bull']:
                    continue
            
            # 计算收益
            buy_price = row['close']
            future = tail.iloc[i+1:i+hold+1]['close'].tolist()
            if not future:
                continue
            pnl_max = (max(future) - buy_price) / buy_price * 100
            pnl_final = (future[-1] - buy_price) / buy_price * 100
            trades.append({'max': pnl_max, 'final': pnl_final, 'buy_price': buy_price,
                           'future_max': max(future), 'code': code})
    
    return trades

def analyze_trades(trades):
    if len(trades) < 15:
        return None
    pnls_max = [t['max'] for t in trades]
    pnls_final = [t['final'] for t in trades]
    wins = sum(1 for p in pnls_final if p > 0)
    
    def hit_rate(threshold):
        return sum(1 for p in pnls_max if p >= threshold) / len(trades) * 100
    
    return {
        'n': len(trades),
        'win': wins / len(trades) * 100,
        'avg_max': float(np.mean(pnls_max)),
        'avg_final': float(np.mean(pnls_final)),
        'max_pnl': max(pnls_max),
        'min_pnl': min(pnls_max),
        'r50': hit_rate(50),
        'r40': hit_rate(40),
        'r35': hit_rate(35),
        'r30': hit_rate(30),
        'r25': hit_rate(25),
        'r20': hit_rate(20),
        'r15': hit_rate(15),
        'r10': hit_rate(10),
    }

# ===== 参数穷举搜索 =====
print("\n[2/5] 极限参数穷举搜索...")

all_results = []
combo_idx = 0

# 持有天数
hold_days = [7, 10, 14, 18, 21, 24, 28, 35, 42]

# 涨幅区间
chg_ranges = [
    (3, 10), (5, 12), (5, 15), (6, 12), (6, 15),
    (3, 15), (3, 20), (2, 15), (1, 20),
    (8, 15), (8, 20), (10, 20),
    (3, 8), (5, 10), (2, 10), (1, 10),
]

# 价格区间
price_ranges = [
    (1, 10), (1, 15), (1, 20), (1, 30),
    (3, 10), (3, 15), (3, 20),
    (2, 8), (2, 10), (2, 15),
    (5, 10), (5, 15),
    (1, 5), (1, 8), (3, 8),
]

# RSI配置
rsi_setups = [
    None,
    (14, 30, 70),
    (14, 35, 65),
    (14, 40, 70),
    (14, 30, 60),
    (14, 20, 60),
    (14, 25, 55),
    (14, 30, 55),
    (14, 35, 60),
    (14, 30, 50),
    (14, 25, 50),
    (14, 40, 60),
    (6, 20, 80),
    (6, 30, 80),
    (9, 25, 70),
    (9, 30, 65),
]

# MACD配置
macd_setups = [
    None,
    'gold',
    'above_zero',
    'cross_up',
    'gold_above_zero',
    'dea_above_zero',
    'macd_strong',
    'dif_above_macd',
]

# 成交量配置 (None = 无过滤)
vol_setups = [None, 1.0, 1.2, 1.5]

# MA多头排列
ma_bull_setups = [False, True]

# RSI6上限
rsi6_max_setups = [None, 70, 75, 80, 85]

# 预计算总组合数
total = (len(hold_days) * len(chg_ranges) * len(price_ranges) *
         len(rsi_setups) * len(macd_setups) * len(vol_setups) *
         len(ma_bull_setups) * len(rsi6_max_setups))
print(f"总参数组合: {total}")

for hold in hold_days:
    for chg_min, chg_max in chg_ranges:
        for pmin, pmax in price_ranges:
            for rsi_setup in rsi_setups:
                for macd_cond in macd_setups:
                    for vol_min in vol_setups:
                        for ma_bull in ma_bull_setups:
                            for rsi6_max in rsi6_max_setups:
                                combo_idx += 1
                                
                                params = {
                                    'hold': hold,
                                    'chg_min': chg_min,
                                    'chg_max': chg_max,
                                    'pmax': pmax,
                                    'pmin': pmin,
                                    'macd': macd_cond,
                                    'vol_min': vol_min,
                                    'ma_bull': ma_bull,
                                    'rsi6_max': rsi6_max,
                                }
                                if rsi_setup is not None:
                                    params['rsi_enabled'] = True
                                    params['rsi_period'] = rsi_setup[0]
                                    params['rsi_min'] = rsi_setup[1]
                                    params['rsi_max'] = rsi_setup[2]
                                
                                trades = backtest(params, df)
                                stats = analyze_trades(trades)
                                
                                if stats and stats['n'] >= 15:
                                    rsi_desc = 'OFF' if rsi_setup is None else f"R{rsi_setup[0]}:{rsi_setup[1]}-{rsi_setup[2]}"
                                    vol_desc = '∞' if vol_min is None else f'{vol_min}x'
                                    macd_desc = 'OFF' if macd_cond is None else macd_cond
                                    
                                    result = {
                                        'hold': hold,
                                        'chg': f'{chg_min}-{chg_max}',
                                        'pmin': pmin,
                                        'pmax': pmax,
                                        'rsi': rsi_desc,
                                        'macd': macd_desc,
                                        'vol': vol_desc,
                                        'vol_raw': vol_min,
                                        'ma_bull': ma_bull,
                                        'rsi6_max': rsi6_max,
                                        **stats,
                                    }
                                    all_results.append(result)

print(f"进度: {combo_idx}/{total} 组合已测试 | 有效策略: {len(all_results)}")

# ===== 多维度排序分析 =====
print("\n[3/5] 多维度策略排名...")

# TOP by r50
by_r50 = sorted(all_results, key=lambda x: (-x['r50'], -x['r40'], -x['avg_max']))
# TOP by r40
by_r40 = sorted(all_results, key=lambda x: (-x['r40'], -x['r30'], -x['avg_max']))
# TOP by r35
by_r35 = sorted(all_results, key=lambda x: (-x['r35'], -x['r30'], -x['avg_max']))
# TOP by r30
by_r30 = sorted(all_results, key=lambda x: (-x['r30'], -x['avg_max'], -x['win']))
# TOP by 综合分数 (r40 + r30/2 + win/3)
for r in all_results:
    r['composite'] = r['r40'] + r['r30'] * 0.5 + r['win'] * 0.3
by_composite = sorted(all_results, key=lambda x: -x['composite'])

print("\n" + "=" * 100)
print("【TOP 20 策略 - 40%达标率排序】")
print("=" * 100)
print(f"{'#':^3} {'持有':^4} {'涨幅':^7} {'价格':^7} {'RSI':^10} {'MACD':^10} {'量比':^5} {'MA多头':^6} "
      f"{'交易':^5} {'胜率':^6} {'均收益':^7} {'r50':^6} {'r40':^6} {'r35':^6} {'r30':^6}")
print('-' * 130)

for i, r in enumerate(by_r40[:20], 1):
    rsi_str = r['rsi'][:9] if len(r['rsi']) > 9 else r['rsi']
    macd_str = r['macd'][:9] if len(r['macd']) > 9 else r['macd']
    price_str = f"{r['pmin']}-{r['pmax']}"
    ma_str = '是' if r['ma_bull'] else '否'
    print(f'{i:^3} {r["hold"]:^4} {r["chg"]:^7} {price_str:^7} {rsi_str:^10} {macd_str:^10} {r["vol"]:^5} {ma_str:^6} '
          f'{r["n"]:^5} {r["win"]:>5.1f}% {r["avg_max"]:>6.1f}% '
          f'{r["r50"]:>5.1f}% {r["r40"]:>5.1f}% {r["r35"]:>5.1f}% {r["r30"]:>5.1f}%')

print("\n" + "=" * 100)
print("【TOP 20 策略 - 35%达标率排序】")
print("=" * 100)
for i, r in enumerate(by_r35[:20], 1):
    rsi_str = r['rsi'][:9] if len(r['rsi']) > 9 else r['rsi']
    macd_str = r['macd'][:9] if len(r['macd']) > 9 else r['macd']
    price_str = f"{r['pmin']}-{r['pmax']}"
    ma_str = '是' if r['ma_bull'] else '否'
    print(f'{i:^3} {r["hold"]:^4} {r["chg"]:^7} {price_str:^7} {rsi_str:^10} {macd_str:^10} {r["vol"]:^5} {ma_str:^6} '
          f'{r["n"]:^5} {r["win"]:>5.1f}% {r["avg_max"]:>6.1f}% '
          f'{r["r50"]:>5.1f}% {r["r40"]:>5.1f}% {r["r35"]:>5.1f}% {r["r30"]:>5.1f}%')

print("\n" + "=" * 100)
print("【TOP 20 策略 - 综合评分排序】")
print("=" * 100)
for i, r in enumerate(by_composite[:20], 1):
    rsi_str = r['rsi'][:9] if len(r['rsi']) > 9 else r['rsi']
    macd_str = r['macd'][:9] if len(r['macd']) > 9 else r['macd']
    price_str = f"{r['pmin']}-{r['pmax']}"
    ma_str = '是' if r['ma_bull'] else '否'
    print(f'{i:^3} {r["hold"]:^4} {r["chg"]:^7} {price_str:^7} {rsi_str:^10} {macd_str:^10} {r["vol"]:^5} {ma_str:^6} '
          f'{r["n"]:^5} {r["win"]:>5.1f}% {r["avg_max"]:>6.1f}% '
          f'{r["r50"]:>5.1f}% {r["r40"]:>5.1f}% {r["r35"]:>5.1f}% {r["r30"]:>5.1f}%')

# ===== 最佳策略深度分析 =====
print("\n[4/5] 深度分析最佳策略...")

# 最佳策略（综合评分）
best = by_composite[0]
best_r40 = by_r40[0]
best_r30 = by_r30[0]

print(f"\n{'='*80}")
print(f'【综合最佳策略】')
print(f'  持有天数: {best["hold"]}天')
print(f'  买入涨幅: {best["chg"]}%')
print(f'  价格区间: {best["pmin"]}-{best["pmax"]}元')
print(f'  RSI条件: {best["rsi"]}')
print(f'  MACD条件: {best["macd"]}')
print(f'  成交量: ≥{best["vol"]}' if best["vol"] != '∞' else '  成交量: 无限制')
print(f'  MA多头排列: {"是" if best["ma_bull"] else "否"}')
if best.get('rsi6_max'):
    print(f'  RSI6上限: {best["rsi6_max"]}')
print(f'  交易次数: {best["n"]}')
print(f'  胜率: {best["win"]:.1f}%')
print(f'  平均最大收益: {best["avg_max"]:.1f}%')
print(f'  平均最终收益: {best["avg_final"]:.1f}%')
print(f'  最高单笔: {best["max_pnl"]:.1f}%')
print(f'  最低单笔: {best["min_pnl"]:.1f}%')
print(f'  50%达标率: {best["r50"]:.1f}%')
print(f'  40%达标率: {best["r40"]:.1f}%')
print(f'  35%达标率: {best["r35"]:.1f}%')
print(f'  30%达标率: {best["r30"]:.1f}% ⭐')
print(f'  25%达标率: {best["r25"]:.1f}%')
print(f'  20%达标率: {best["r20"]:.1f}%')
print(f'  综合评分: {best["composite"]:.1f}')
print(f'{"="*80}')

# ===== 选股：应用最佳策略 =====
print("\n[5/5] 应用最佳策略选股...")

def apply_strategy(best_params, df):
    trades = backtest(best_params, df)
    
    # 按未来最大收益排序
    trades.sort(key=lambda x: -x['max'])
    
    return trades

# 构建最佳策略参数
best_params = {
    'hold': best['hold'],
    'chg_min': int(best['chg'].split('-')[0]),
    'chg_max': int(best['chg'].split('-')[1]),
    'pmax': best['pmax'],
    'pmin': best['pmin'],
    'macd': None if best['macd'] == 'OFF' else best['macd'],
    'vol_min': best['vol_raw'],
    'ma_bull': best['ma_bull'],
    'rsi6_max': best.get('rsi6_max'),
    'rsi_enabled': best['rsi'] != 'OFF',
}
if best_params['rsi_enabled']:
    parts = best['rsi'].replace('R', '').split(':')[1].split('-')
    best_params['rsi_period'] = int(best['rsi'].replace('R', '').split(':')[0])
    best_params['rsi_min'] = float(parts[0])
    best_params['rsi_max'] = float(parts[1])

top_trades = apply_strategy(best_params, df)
print(f"\n符合最佳策略的历史机会: {len(top_trades)} 次")
print(f"\nTOP 15 机会（按未来最大收益排序）:")
print(f"{'排名':^4} {'代码':^8} {'买入价':^8} {'持有{max}%':^10} {'最终%':^8} {'天数':^5}")
print('-' * 55)
for i, t in enumerate(top_trades[:15], 1):
    print(f'{i:^4} {t["code"]:^8} {t["buy_price"]:>7.2f} {t["max"]:>9.1f}% {t["final"]:>7.1f}% {best["hold"]:^5}天')

# ===== 明日股票推荐（从实时数据）=====
print("\n【明日推荐股票分析】")
# 尝试从 realtime_quote 读取实时数据
conn = sqlite3.connect(DB)
try:
    df_rt = pd.read_sql('SELECT * FROM realtime_quote ORDER BY code', conn)
    conn.close()
    print(f"实时数据股票数: {len(df_rt)}")
    
    # 对实时数据进行策略匹配
    recommendations = []
    for _, row in df_rt.iterrows():
        code = row['code']
        name = row.get('name', code)
        price = row['price']
        change_pct = row.get('change_pct', 0)
        vol_ratio = row.get('vr', None)
        
        # 基础筛选
        chg_min_b = best_params['chg_min']
        chg_max_b = best_params['chg_max']
        if not (chg_min_b <= change_pct <= chg_max_b):
            continue
        if not (best_params['pmin'] <= price <= best_params['pmax']):
            continue
        if best_params['vol_min'] is not None:
            if vol_ratio is None or vol_ratio < best_params['vol_min']:
                continue
        
        # 获取该股票历史计算指标
        stock_hist = df[df['code'] == code].sort_values('date')
        if len(stock_hist) == 0:
            continue
        last_row = stock_hist.iloc[-1]
        
        # RSI
        rsi_col = f"rsi{best_params.get('rsi_period', 14)}"
        rsi_val = last_row.get(rsi_col)
        
        recommendations.append({
            'code': code,
            'name': name,
            'price': price,
            'change_pct': change_pct,
            'vol_ratio': vol_ratio,
            'rsi': round(rsi_val, 1) if rsi_val else None,
            'dif': round(last_row['dif'], 3) if last_row['dif'] else None,
            'dea': round(last_row['dea'], 3) if last_row['dea'] else None,
            'macd_bar': round(last_row['macd_bar'], 3) if last_row['macd_bar'] else None,
        })
    
    if recommendations:
        # 排序: 优先RSI适中，然后量比
        def rec_sort(r):
            rsi = r['rsi'] if r['rsi'] else 50
            return abs(45 - rsi) - (r['vol_ratio'] or 0) * 0.5
        recommendations.sort(key=rec_sort)
        
        print(f"\n符合最佳策略的股票 ({len(recommendations)} 只):")
        print(f"{'代码':^8} {'名称':^10} {'价格':^7} {'涨幅':^7} {'量比':^6} {'RSI14':^7} {'DIF':^8} {'DEA':^8}")
        print('-' * 80)
        for r in recommendations[:20]:
            print(f"{r['code']:^8} {r['name'][:8]:^10} {r['price']:>6.2f} {r['change_pct']:>6.1f}% "
                  f"{str(r['vol_ratio']):>5} {str(r['rsi']):>6} {str(r['dif']):>8} {str(r['dea']):>8}")
    else:
        print("实时数据中无完全符合策略的股票")
        
except Exception as e:
    conn.close()
    print(f"实时数据加载失败: {e}")

# ===== 特殊策略探索：突破50% =====
print("\n\n" + "=" * 80)
print("【特殊策略深度探索】")
print("=" * 80)

# 探索：无量比 + 严格价格 + RSI超卖 + MACD
special_configs = []

# 配置1: 极低价(1-10元) + RSI超卖(20-55) + MACD金叉
for hold in [14, 18, 21]:
    for chg in [(3, 8), (3, 10), (5, 10), (2, 8), (1, 10)]:
        for rsi_setup in [(14, 20, 55), (14, 25, 60), (14, 30, 65), (6, 20, 70)]:
            for macd in ['gold', 'above_zero', 'cross_up']:
                params = {
                    'hold': hold,
                    'chg_min': chg[0],
                    'chg_max': chg[1],
                    'pmax': 10,
                    'pmin': 1,
                    'rsi_enabled': True,
                    'rsi_period': rsi_setup[0],
                    'rsi_min': rsi_setup[1],
                    'rsi_max': rsi_setup[2],
                    'macd': macd,
                    'vol_min': None,  # 无量比过滤
                    'ma_bull': False,
                    'rsi6_max': None,
                }
                trades = backtest(params, df)
                stats = analyze_trades(trades)
                if stats and stats['n'] >= 15:
                    special_configs.append({**params, **stats})

# 配置2: 无量比 + 宽涨幅 + 无RSI + MACD
for hold in [14, 18, 21, 24, 28]:
    for chg in [(3, 15), (5, 15), (3, 20), (6, 15)]:
        for macd in ['gold', 'above_zero', 'macd_strong']:
            for pmin, pmax in [(1, 10), (1, 15), (3, 15)]:
                params = {
                    'hold': hold,
                    'chg_min': chg[0],
                    'chg_max': chg[1],
                    'pmax': pmax,
                    'pmin': pmin,
                    'rsi_enabled': False,
                    'macd': macd,
                    'vol_min': None,
                    'ma_bull': False,
                    'rsi6_max': None,
                }
                trades = backtest(params, df)
                stats = analyze_trades(trades)
                if stats and stats['n'] >= 15:
                    special_configs.append({**params, **stats})

# 按r40排序
special_sorted = sorted(special_configs, key=lambda x: (-x.get('r40', 0), -x.get('r30', 0), -x.get('avg_max', 0)))

print(f"\n特殊策略测试 {len(special_configs)} 个有效结果:")
print(f"{'#':^3} {'持有':^4} {'涨幅':^7} {'价格':^7} {'RSI':^12} {'MACD':^12} {'交易':^5} {'胜率':^6} {'r50':^6} {'r40':^6} {'r35':^6} {'r30':^6}")
print('-' * 100)
for i, r in enumerate(special_sorted[:30], 1):
    rsi_desc = 'OFF' if not r.get('rsi_enabled') else f"R{r.get('rsi_period')}:{r.get('rsi_min')}-{r.get('rsi_max')}"
    price_str = f"{r['pmin']}-{r['pmax']}"
    print(f'{i:^3} {r["hold"]:^4} {r["chg_min"]}-{r["chg_max"]:^4} {price_str:^7} {rsi_desc:^12} {str(r["macd"]):^12} '
          f'{r["n"]:^5} {r["win"]:>5.1f}% {r["r50"]:>5.1f}% {r["r40"]:>5.1f}% {r["r35"]:>5.1f}% {r["r30"]:>5.1f}%')

# ===== 找出突破50%的策略 =====
r50_above = [r for r in all_results + special_configs if r.get('r50', 0) >= 50]
r40_above = [r for r in all_results + special_configs if r.get('r40', 0) >= 40]
r35_above = [r for r in all_results + special_configs if r.get('r35', 0) >= 35]

print(f"\n\n{'='*80}")
print(f'【极限达标率统计】')
print(f'  50%+达标率策略数: {len(r50_above)}')
print(f'  40%+达标率策略数: {len(r40_above)}')
print(f'  35%+达标率策略数: {len(r35_above)}')
print(f'{"="*80}')

if r50_above:
    print("\n【突破50%达标率的策略！】")
    r50_sorted = sorted(r50_above, key=lambda x: -x['r50'])
    for r in r50_sorted[:5]:
        print(f"  {r.get('hold')}天持有 | {r.get('chg')}涨幅 | {r.get('pmax')}元以下 | r50={r.get('r50'):.1f}%")

# ===== 保存结果 =====
print("\n\n[保存结果]")
output = {
    'best_strategy': best,
    'best_by_r40': best_r40,
    'best_by_r30': best_r30,
    'top20_by_r40': [{k: v for k, v in r.items() if k != 'composite'} for r in by_r40[:20]],
    'top20_by_r35': [{k: v for k, v in r.items() if k != 'composite'} for r in by_r35[:20]],
    'top20_composite': [{k: v for k, v in r.items() if k != 'composite'} for r in by_composite[:20]],
    'top_special': special_sorted[:20],
    'all_stats': {
        'total_combinations': combo_idx,
        'valid_strategies': len(all_results),
        'r50_above_count': len(r50_above),
        'r40_above_count': len(r40_above),
        'r35_above_count': len(r35_above),
    },
    'top_trades': [
        {'rank': i+1, 'code': t['code'], 'buy_price': t['buy_price'],
         'future_max_pct': round(t['max'], 1), 'final_pct': round(t['final'], 1)}
        for i, t in enumerate(top_trades[:20])
    ],
}

with open('data/ultra_optimize.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2, default=str)

print(f"✓ 已保存到 data/ultra_optimize.json")
print(f"✓ 最佳策略: {best['hold']}天持有 | r30={best['r30']:.1f}% | r40={best['r40']:.1f}% | r50={best['r50']:.1f}%")
print(f"✓ 特殊策略突破40%: {len([r for r in special_sorted if r.get('r40', 0) >= 40])} 个")
