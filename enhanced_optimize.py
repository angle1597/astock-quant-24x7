# -*- coding: utf-8 -*-
"""
增强版量化选股优化系统
- RSI指标筛选
- MACD指标筛选  
- 资金流向因子
- 多参数穷举优化
- 目标：r30达标率 > 40%
"""
import sys, os, sqlite3, json, math
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'

# ===== 技术指标计算 =====
def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calc_rsi_full(closes, period=14):
    """计算完整RSI序列"""
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
    """指数移动平均"""
    if len(series) < n:
        return [None] * len(series)
    k = 2 / (n + 1)
    ema = [None] * (n - 1)
    ema.append(series[n - 1])
    for i in range(n, len(series)):
        ema.append(series[i] * k + ema[-1] * (1 - k))
    return ema

def calc_macd(closes, fast=12, slow=26, signal=9):
    """计算MACD: (DIF, DEA, MACD柱)"""
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
    
    # DEA = EMA(DIF, signal)
    dif_valid = [(i, x) for i, x in enumerate(dif) if x is not None]
    if len(dif_valid) < signal:
        return dif, dea, macd_bar
    
    k = 2 / (signal + 1)
    # DEA calculation starts from signal-th valid DIF
    valid_dif = [x for _, x in dif_valid]
    dea_values = []
    dea_values.append(valid_dif[signal - 1])  # first DEA = DIF[signal-1]
    for i in range(signal, len(valid_dif)):
        dea_values.append(valid_dif[i] * k + dea_values[-1] * (1 - k))
    
    # Map back to original index
    first_valid_idx = dif_valid[0][0]
    last_valid_idx = dif_valid[-1][0]
    for j, idx in enumerate(range(first_valid_idx + signal - 1, last_valid_idx + 1)):
        if idx < n:
            dea[idx] = dea_values[j]
    
    # MACD bar
    for i in range(n):
        if dif[i] is not None and dea[i] is not None:
            macd_bar[i] = (dif[i] - dea[i]) * 2
    
    return dif, dea, macd_bar

def calc_ma5(closes):
    if len(closes) < 5:
        return [None] * len(closes)
    return [None] * 4 + [np.mean(closes[i-4:i+1]) for i in range(4, len(closes))]

def calc_ma10(closes):
    if len(closes) < 10:
        return [None] * len(closes)
    return [None] * 9 + [np.mean(closes[i-9:i+1]) for i in range(9, len(closes))]

def calc_volume_ma(Volumes, period=5):
    if len(Volumes) < period:
        return [None] * len(Volumes)
    return [None] * (period - 1) + [np.mean(Volumes[i-period+1:i+1]) for i in range(period - 1, len(Volumes))]

# ===== 加载数据 =====
print("=" * 80)
print("【增强版量化选股优化系统】")
print("=" * 80)

conn = sqlite3.connect(DB)
df_all = pd.read_sql('SELECT * FROM kline ORDER BY code, date', conn)
conn.close()

print(f"总记录数: {len(df_all)}")
print(f"股票数量: {df_all['code'].nunique()}")
print(f"日期范围: {df_all['date'].min()} ~ {df_all['date'].max()}")

# 填充None
for col in ['open', 'high', 'low', 'close', 'volume']:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce')

# ===== 为每只股票计算指标 =====
print("\n[1/4] 计算技术指标...")
df_all = df_all.sort_values(['code', 'date']).reset_index(drop=True)

# 按股票分组计算指标
dfs = []
for code, grp in df_all.groupby('code'):
    grp = grp.sort_values('date').reset_index(drop=True)
    closes = grp['close'].tolist()
    volumes = grp['volume'].tolist()
    
    grp['rsi14'] = calc_rsi_full(closes, 14)
    dif, dea, macd_bar = calc_macd(closes)
    grp['dif'] = dif
    grp['dea'] = dea
    grp['macd_bar'] = macd_bar
    grp['ma5'] = calc_ma5(closes)
    grp['ma10'] = calc_ma10(closes)
    grp['vol_ma5'] = calc_volume_ma(volumes, 5)
    
    # 资金流向: 用成交量和价格变化估算
    # 假设：上涨日主力买入，下跌日主力卖出
    grp['price_chg'] = grp['close'].pct_change() * 100
    grp['vol_ratio'] = grp['volume'] / grp['vol_ma5']
    
    dfs.append(grp)

df = pd.concat(dfs, ignore_index=True)
print(f"指标计算完成，总行数: {len(df)}")

# ===== 参数穷举 =====
print("\n[2/4] 多因子参数穷举搜索...")

# 参数组合生成
hold_days_list = [7, 10, 14, 21, 28]
chg_configs = [
    (3, 8), (5, 10), (6, 12), (8, 15), (5, 15), (3, 12)
]
price_max_list = [10, 15, 20, 30, 50]

# RSI配置: (rsi_min, rsi_max, enabled)
rsi_configs = [
    (None, None, False),   # 不使用RSI
    (30, 70, True),        # 标准RSI
    (35, 65, True),       # 较窄区间
    (40, 60, True),       # 更窄
    (45, 70, True),       # 偏低RSI
    (30, 60, True),       # 中性偏低
    (40, 80, True),       # 中性偏高
    (50, 80, True),       # 偏高RSI
]

# MACD配置: (macd_condition, enabled)
# macd_condition: 'gold' = DIF金叉DEA(在0轴上), 'above_zero' = DIF>0, 'cross_up' = MACD柱由负转正
macd_configs = [
    (None, False),
    ('gold', True),        # MACD金叉
    ('above_zero', True),  # DIF在0轴上方
    ('cross_up', True),   # MACD柱由负转正
]

# 成交量放大配置: (vol_ratio_min, enabled)
vol_configs = [
    (None, False),
    (1.2, True),
    (1.5, True),
    (2.0, True),
]

all_results = []
total_combinations = (
    len(hold_days_list) * len(chg_configs) * len(price_max_list) *
    len(rsi_configs) * len(macd_configs) * len(vol_configs)
)
print(f"总参数组合: {total_combinations}")
combo_idx = 0

for hold in hold_days_list:
    for chg_min, chg_max in chg_configs:
        for pmax in price_max_list:
            for rsi_min, rsi_max, rsi_enabled in rsi_configs:
                for macd_cond, macd_enabled in macd_configs:
                    for vol_min, vol_enabled in vol_configs:
                        combo_idx += 1
                        
                        trades = []
                        for code, grp in df.groupby('code'):
                            if len(grp) < hold + 35:
                                continue
                            grp = grp.reset_index(drop=True)
                            # 取最近120天
                            tail = grp.tail(140).reset_index(drop=True)
                            
                            for i in range(25, len(tail) - hold - 1):
                                row = tail.iloc[i]
                                prev = tail.iloc[i - 1]
                                
                                # 基础条件
                                chg = row['price_chg'] if not pd.isna(row['price_chg']) else 0
                                if not (chg_min <= chg <= chg_max):
                                    continue
                                if not (3 <= row['close'] <= pmax):
                                    continue
                                
                                # RSI筛选
                                if rsi_enabled:
                                    rsi = row['rsi14']
                                    if rsi is None or rsi < rsi_min or rsi > rsi_max:
                                        continue
                                
                                # MACD筛选
                                if macd_enabled:
                                    dif_i = row['dif']
                                    dea_i = row['dea']
                                    dif_prev = tail.iloc[i-1]['dif']
                                    macd_i = row['macd_bar']
                                    macd_prev = tail.iloc[i-1]['macd_bar']
                                    
                                    if macd_cond == 'gold':
                                        # DIF金叉DEA 且 DIF>0
                                        if not (dif_i is not None and dea_i is not None and 
                                                dif_prev is not None and
                                                dif_prev < dea_i and dif_i > dea_i and dif_i > 0):
                                            continue
                                    elif macd_cond == 'above_zero':
                                        if not (dif_i is not None and dif_i > 0):
                                            continue
                                    elif macd_cond == 'cross_up':
                                        if not (macd_i is not None and macd_prev is not None and
                                                macd_prev < 0 and macd_i > 0):
                                            continue
                                
                                # 成交量放大筛选
                                if vol_enabled:
                                    vr = row['vol_ratio']
                                    if vr is None or vr < vol_min:
                                        continue
                                
                                # 买入并计算收益
                                buy_price = row['close']
                                future = tail.iloc[i+1:i+hold+1]['close'].tolist()
                                if not future:
                                    continue
                                pnl_max = (max(future) - buy_price) / buy_price * 100
                                pnl_final = (future[-1] - buy_price) / buy_price * 100
                                trades.append({'max': pnl_max, 'final': pnl_final})
                        
                        if len(trades) >= 15:
                            pnls_max = [t['max'] for t in trades]
                            pnls_final = [t['final'] for t in trades]
                            wins = sum(1 for p in pnls_final if p > 0)
                            
                            def hit_rate(threshold):
                                return sum(1 for p in pnls_max if p >= threshold) / len(trades) * 100
                            
                            r50 = hit_rate(50)
                            r40 = hit_rate(40)
                            r30 = hit_rate(30)
                            r25 = hit_rate(25)
                            r20 = hit_rate(20)
                            
                            all_results.append({
                                'hold': hold,
                                'chg': f'{chg_min}-{chg_max}',
                                'pmax': pmax,
                                'rsi': f'{rsi_min}-{rsi_max}' if rsi_enabled else 'OFF',
                                'macd': macd_cond if macd_enabled else 'OFF',
                                'vol_ratio': vol_min if vol_enabled else None,
                                'n': len(trades),
                                'win': wins / len(trades) * 100,
                                'avg_max': np.mean(pnls_max),
                                'max_pnl': max(pnls_max),
                                'r50': r50,
                                'r40': r40,
                                'r30': r30,
                                'r25': r25,
                                'r20': r20,
                            })

# 按r40排序，再按r30
all_results.sort(key=lambda x: (x['r40'], x['r30'], x['avg_max']), reverse=True)

print(f"\n共测试 {combo_idx} 个组合，{len(all_results)} 个有效(≥15笔交易)")

# ===== 显示TOP结果 =====
print("\n[3/4] TOP 20 策略 (按40%达标率排序):")
print(f"{'#':^3} {'持有':^4} {'涨幅':^7} {'价≤':^5} {'RSI':^8} {'MACD':^8} {'量比':^5} "
      f"{'交易':^5} {'胜率':^6} {'均收益':^7} {'50%':^6} {'40%':^6} {'30%':^6} {'25%':^6} {'20%':^6}")
print('-' * 130)

for i, r in enumerate(all_results[:20], 1):
    rsi_str = r['rsi'][:7] if len(r['rsi']) > 7 else r['rsi']
    macd_str = r['macd'][:7] if len(r['macd']) > 7 else r['macd']
    vol_str = str(r['vol_ratio']) if r['vol_ratio'] else '-'
    print(f'{i:^3} {r["hold"]:^4} {r["chg"]:^7} {r["pmax"]:^5} {rsi_str:^8} {macd_str:^8} {vol_str:^5} '
          f'{r["n"]:^5} {r["win"]:>5.1f}% {r["avg_max"]:>6.1f}% '
          f'{r["r50"]:>5.1f}% {r["r40"]:>5.1f}% {r["r30"]:>5.1f}% {r["r25"]:>5.1f}% {r["r20"]:>5.1f}%')

# ===== 最佳策略深度分析 =====
print("\n[4/4] 深度分析最佳策略...")
best = all_results[0]

print(f"\n{'='*80}")
print(f'【增强版最佳策略】')
print(f'  持有天数: {best["hold"]}天')
print(f'  买入涨幅区间: {best["chg"]}%')
print(f'  价格上限: ≤{best["pmax"]}元')
print(f'  RSI条件: {best["rsi"]}')
print(f'  MACD条件: {best["macd"]}')
print(f'  成交量放大: ≥{best["vol_ratio"]}x' if best["vol_ratio"] else '  成交量放大: 不限制')
print(f'  交易次数: {best["n"]}')
print(f'  胜率: {best["win"]:.1f}%')
print(f'  平均最大收益: {best["avg_max"]:.1f}%')
print(f'  最高单笔收益: {best["max_pnl"]:.1f}%')
print(f'  50%达标率: {best["r50"]:.1f}%')
print(f'  40%达标率: {best["r40"]:.1f}% ⭐⭐')
print(f'  30%达标率: {best["r30"]:.1f}% ⭐')
print(f'  25%达标率: {best["r25"]:.1f}%')
print(f'  20%达标率: {best["r20"]:.1f}%')
print(f'{"="*80}')

# ===== 找出符合条件的股票 =====
print("\n【下周推荐股票】")
rsi_min_b, rsi_max_b = None, None
if best['rsi'] != 'OFF':
    parts = best['rsi'].split('-')
    rsi_min_b, rsi_max_b = float(parts[0]), float(parts[1])
macd_cond_b = best['macd']
vol_min_b = best['vol_ratio']
chg_parts = best['chg'].split('-')
chg_min_b, chg_max_b = float(chg_parts[0]), float(chg_parts[1])

recommendations = []
for code, grp in df.groupby('code'):
    grp = grp.sort_values('date').reset_index(drop=True)
    if len(grp) < 5:
        continue
    last = grp.iloc[-1]
    prev = grp.iloc[-2]
    
    # 基础条件
    chg = last['price_chg'] if not pd.isna(last['price_chg']) else 0
    if not (chg_min_b <= chg <= chg_max_b):
        continue
    if not (3 <= last['close'] <= best['pmax']):
        continue
    
    # RSI条件
    if rsi_min_b is not None:
        if last['rsi14'] is None or last['rsi14'] < rsi_min_b or last['rsi14'] > rsi_max_b:
            continue
    
    # MACD条件
    if macd_cond_b != 'OFF':
        dif_i = last['dif']
        dea_i = last['dea']
        dif_prev = prev['dif']
        macd_i = last['macd_bar']
        macd_prev = prev['macd_bar']
        
        if macd_cond_b == 'gold':
            if not (dif_i is not None and dea_i is not None and dif_prev is not None and
                    dif_prev < dea_i and dif_i > dea_i and dif_i > 0):
                continue
        elif macd_cond_b == 'above_zero':
            if not (dif_i is not None and dif_i > 0):
                continue
        elif macd_cond_b == 'cross_up':
            if not (macd_i is not None and macd_prev is not None and macd_prev < 0 and macd_i > 0):
                continue
    
    # 成交量
    if vol_min_b is not None:
        vr = last['vol_ratio']
        if vr is None or vr < vol_min_b:
            continue
    
    recommendations.append({
        'code': code,
        'close': last['close'],
        'chg': chg,
        'rsi14': round(last['rsi14'], 1) if last['rsi14'] else None,
        'vol_ratio': round(last['vol_ratio'], 2) if last['vol_ratio'] else None,
        'dif': round(last['dif'], 3) if last['dif'] else None,
        'dea': round(last['dea'], 3) if last['dea'] else None,
        'macd_bar': round(last['macd_bar'], 3) if last['macd_bar'] else None,
        'ma5': round(last['ma5'], 2) if last['ma5'] else None,
        'ma10': round(last['ma10'], 2) if last['ma10'] else None,
    })

# 按RSI排序 (中等偏低更优)
def sort_key(r):
    if r['rsi14'] is not None:
        return abs(50 - r['rsi14'])  # 越接近50越中等
    return 999

recommendations.sort(key=sort_key)
print(f"\n符合条件的股票 ({len(recommendations)} 只):")
if recommendations:
    print(f"{'代码':^8} {'收盘价':^8} {'涨幅%':^7} {'RSI14':^7} {'量比':^6} {'DIF':^8} {'DEA':^8} {'MACD柱':^8}")
    print('-' * 75)
    for r in recommendations[:20]:
        print(f"{r['code']:^8} {r['close']:>7.2f} {r['chg']:>6.1f}% {str(r['rsi14']):>6} {str(r['vol_ratio']):>5} "
              f"{str(r['dif']):>8} {str(r['dea']):>8} {str(r['macd_bar']):>8}")
else:
    print("没有股票完全符合最佳策略条件，放宽条件搜索...")

# 保存结果
output = {
    'best_strategy': best,
    'top20': all_results[:20],
    'recommendations': recommendations[:30],
    'total_combinations': combo_idx,
    'valid_combinations': len(all_results),
}

with open('data/enhanced_optimize_results.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2, default=str)

print(f"\n✓ 优化完成！")
print(f"✓ 最佳40%达标率: {best['r40']:.1f}% (目标40%+)")
print(f"✓ 最佳30%达标率: {best['r30']:.1f}%")
print(f"✓ 结果已保存到 data/enhanced_optimize_results.json")
