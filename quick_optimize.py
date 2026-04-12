# -*- coding: utf-8 -*-
"""
快速优化回测 - 测试多种策略组合 + RSI/MACD筛选
"""
import sys, sqlite3, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'
conn = sqlite3.connect(DB)
codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
conn.close()

print(f'股票数量: {len(codes)}')
print('=' * 80)

# 计算RSI和MACD
def calc_rsi(prices, period=14):
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calc_macd(prices, fast=12, slow=26, signal=9):
    ema_fast = pd.Series(prices).ewm(span=fast).mean().values
    ema_slow = pd.Series(prices).ewm(span=slow).mean().values
    macd = ema_fast - ema_slow
    signal_line = pd.Series(macd).ewm(span=signal).mean().values
    return macd[-1] - signal_line[-1] if len(macd) >= signal else 0

# 策略参数组合
strategies = []
for hold in [7, 10, 14, 21]:
    for chg_min, chg_max in [(3, 8), (5, 10), (6, 12), (8, 15)]:
        for pmax in [10, 15, 20]:
            strategies.append({
                'hold': hold, 'chg_min': chg_min, 'chg_max': chg_max, 
                'pmax': pmax, 'use_rsi': False, 'use_macd': False
            })
            # 加入RSI筛选
            strategies.append({
                'hold': hold, 'chg_min': chg_min, 'chg_max': chg_max, 
                'pmax': pmax, 'use_rsi': True, 'rsi_min': 30, 'rsi_max': 70,
                'use_macd': False
            })
            # 加入MACD筛选
            strategies.append({
                'hold': hold, 'chg_min': chg_min, 'chg_max': chg_max, 
                'pmax': pmax, 'use_rsi': False, 'use_macd': True
            })

print(f'测试策略数: {len(strategies)}')
print('-' * 80)

results = []
for s in strategies:
    trades = []
    for code in codes:
        conn = sqlite3.connect(DB)
        df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
        conn.close()
        if df is None or len(df) < 50:
            continue
        df = df.tail(150).reset_index(drop=True)
        df['vol_ma5'] = df['volume'].rolling(5).mean()
        df['vol_ratio'] = df['volume'] / df['vol_ma5']
        
        for i in range(30, len(df)-s['hold']-1):
            row, prev = df.iloc[i], df.iloc[i-1]
            chg = (row['close']-prev['close'])/prev['close']*100 if prev['close']>0 else 0
            
            # 基础条件
            if not (s['chg_min'] <= chg <= s['chg_max'] and 3 <= row['close'] <= s['pmax']):
                continue
            
            # RSI筛选
            if s['use_rsi']:
                prices = df['close'].iloc[max(0,i-20):i+1].values
                if len(prices) < 15:
                    continue
                rsi = calc_rsi(prices)
                if not (s['rsi_min'] <= rsi <= s['rsi_max']):
                    continue
            
            # MACD筛选
            if s['use_macd']:
                prices = df['close'].iloc[max(0,i-30):i+1].values
                if len(prices) < 26:
                    continue
                macd_diff = calc_macd(prices)
                if macd_diff <= 0:
                    continue
            
            buy = row['close']
            future = df.iloc[i+1:i+s['hold']+1]['close'].tolist()
            if future:
                pnl_max = (max(future)-buy)/buy*100
                pnl_final = (future[-1]-buy)/buy*100
                trades.append({'max': pnl_max, 'final': pnl_final})
    
    if len(trades) >= 15:
        pnls_max = [t['max'] for t in trades]
        pnls_final = [t['final'] for t in trades]
        wins = sum(1 for p in pnls_final if p > 0)
        r30 = sum(1 for p in pnls_max if p >= 30) / len(trades) * 100
        r20 = sum(1 for p in pnls_max if p >= 20) / len(trades) * 100
        r15 = sum(1 for p in pnls_max if p >= 15) / len(trades) * 100
        r10 = sum(1 for p in pnls_max if p >= 10) / len(trades) * 100
        
        rsi_tag = '+RSI' if s['use_rsi'] else ''
        macd_tag = '+MACD' if s['use_macd'] else ''
        
        results.append({
            'hold': s['hold'], 'chg': f"{s['chg_min']}-{s['chg_max']}", 
            'pmax': s['pmax'], 'filters': rsi_tag + macd_tag,
            'n': len(trades), 'win': wins/len(trades)*100,
            'avg_max': np.mean(pnls_max), 'avg_final': np.mean(pnls_final),
            'max_pnl': max(pnls_max), 'r30': r30, 'r20': r20, 'r15': r15, 'r10': r10
        })

# 排序
results.sort(key=lambda x: (x['r30'], x['avg_max']), reverse=True)

print(f'\nTOP 20 策略 (按30%达标率排序):')
print(f'{"#":^3} {"持有":^4} {"涨幅区间":^8} {"价格≤":^6} {"筛选":^8} {"交易":^5} {"胜率":^6} {"平均收益":^8} {"30%":^6} {"25%":^6} {"20%":^6} {"15%":^6} {"10%":^6}')
print('-' * 110)
for i, r in enumerate(results[:20], 1):
    print(f'{i:^3} {r["hold"]:^4} {r["chg"]:^8} {r["pmax"]:^6} {r["filters"]:^8} {r["n"]:^5} '
          f'{r["win"]:>5.1f}% {r["avg_max"]:>7.1f}% {r["r30"]:>5.1f}% {r["r20"]:>5.1f}% '
          f'{r["r15"]:>5.1f}% {r["r10"]:>5.1f}%')

# 找出最佳参数组合
best = results[0] if results else None
if best:
    print(f'\n{"="*80}')
    print(f'【最佳策略】')
    print(f'  持有天数: {best["hold"]}天')
    print(f'  买入涨幅区间: {best["chg"]}%')
    print(f'  价格上限: ≤{best["pmax"]}元')
    print(f'  技术指标: {best["filters"] if best["filters"] else "无"}')
    print(f'  交易次数: {best["n"]}')
    print(f'  胜率: {best["win"]:.1f}%')
    print(f'  平均最大收益: {best["avg_max"]:.1f}%')
    print(f'  30%达标率: {best["r30"]:.1f}%')
    print(f'  20%达标率: {best["r20"]:.1f}%')
    print(f'  15%达标率: {best["r15"]:.1f}%')
    print(f'  10%达标率: {best["r10"]:.1f}%')
    print(f'{"="*80}')

# 保存结果
import json
with open('data/optimization_results.json', 'w', encoding='utf-8') as f:
    json.dump(results[:30], f, ensure_ascii=False, indent=2)
