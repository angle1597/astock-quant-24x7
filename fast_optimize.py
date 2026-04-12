# -*- coding: utf-8 -*-
"""
极速优化 - 核心策略测试
"""
import sys, sqlite3, numpy as np, pandas as pd
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'
conn = sqlite3.connect(DB)
codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
conn.close()

print(f'股票数量: {len(codes)}')
print('=' * 80)

# 核心策略参数
params = [
    # (hold_days, chg_min, chg_max, price_max)
    (7, 3, 8, 10), (7, 3, 8, 15), (7, 3, 8, 20),
    (7, 5, 10, 10), (7, 5, 10, 15), (7, 5, 10, 20),
    (7, 6, 12, 10), (7, 6, 12, 15), (7, 6, 12, 20),
    (10, 3, 8, 10), (10, 3, 8, 15), (10, 3, 8, 20),
    (10, 5, 10, 10), (10, 5, 10, 15), (10, 5, 10, 20),
    (10, 6, 12, 10), (10, 6, 12, 15), (10, 6, 12, 20),
    (14, 3, 8, 10), (14, 3, 8, 15), (14, 3, 8, 20),
    (14, 5, 10, 10), (14, 5, 10, 15), (14, 5, 10, 20),
    (14, 6, 12, 10), (14, 6, 12, 15), (14, 6, 12, 20),
    (21, 5, 10, 10), (21, 5, 10, 15), (21, 5, 10, 20),
    (21, 6, 12, 10), (21, 6, 12, 15), (21, 6, 12, 20),
    (21, 8, 15, 10), (21, 8, 15, 15), (21, 8, 15, 20),
]

results = []
for hold, chg_min, chg_max, pmax in params:
    trades = []
    for code in codes:
        conn = sqlite3.connect(DB)
        df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
        conn.close()
        if df is None or len(df) < hold + 30:
            continue
        df = df.tail(120).reset_index(drop=True)
        
        for i in range(20, len(df)-hold-1):
            row, prev = df.iloc[i], df.iloc[i-1]
            chg = (row['close']-prev['close'])/prev['close']*100 if prev['close']>0 else 0
            
            if chg_min <= chg <= chg_max and 3 <= row['close'] <= pmax:
                buy = row['close']
                future = df.iloc[i+1:i+hold+1]['close'].tolist()
                if future:
                    pnl_max = (max(future)-buy)/buy*100
                    pnl_final = (future[-1]-buy)/buy*100
                    trades.append({'max': pnl_max, 'final': pnl_final})
    
    if len(trades) >= 10:
        pnls_max = [t['max'] for t in trades]
        pnls_final = [t['final'] for t in trades]
        wins = sum(1 for p in pnls_final if p > 0)
        r30 = sum(1 for p in pnls_max if p >= 30) / len(trades) * 100
        r25 = sum(1 for p in pnls_max if p >= 25) / len(trades) * 100
        r20 = sum(1 for p in pnls_max if p >= 20) / len(trades) * 100
        r15 = sum(1 for p in pnls_max if p >= 15) / len(trades) * 100
        r10 = sum(1 for p in pnls_max if p >= 10) / len(trades) * 100
        
        results.append({
            'hold': hold, 'chg': f'{chg_min}-{chg_max}', 'pmax': pmax,
            'n': len(trades), 'win': wins/len(trades)*100,
            'avg_max': np.mean(pnls_max), 'max_pnl': max(pnls_max),
            'r30': r30, 'r25': r25, 'r20': r20, 'r15': r15, 'r10': r10
        })

# 排序
results.sort(key=lambda x: (x['r30'], x['avg_max']), reverse=True)

print(f'\nTOP 15 策略 (按30%达标率排序):')
print(f'{"#":^3} {"持有":^4} {"涨幅区间":^8} {"价格≤":^6} {"交易":^5} {"胜率":^6} {"平均收益":^8} {"最高收益":^8} {"30%":^6} {"25%":^6} {"20%":^6} {"15%":^6} {"10%":^6}')
print('-' * 110)
for i, r in enumerate(results[:15], 1):
    print(f'{i:^3} {r["hold"]:^4} {r["chg"]:^8} {r["pmax"]:^6} {r["n"]:^5} '
          f'{r["win"]:>5.1f}% {r["avg_max"]:>7.1f}% {r["max_pnl"]:>7.1f}% '
          f'{r["r30"]:>5.1f}% {r["r25"]:>5.1f}% {r["r20"]:>5.1f}% {r["r15"]:>5.1f}% {r["r10"]:>5.1f}%')

# 最佳策略
best = results[0] if results else None
if best:
    print(f'\n{"="*80}')
    print(f'【最佳策略】')
    print(f'  持有天数: {best["hold"]}天')
    print(f'  买入涨幅区间: {best["chg"]}%')
    print(f'  价格上限: ≤{best["pmax"]}元')
    print(f'  交易次数: {best["n"]}')
    print(f'  胜率: {best["win"]:.1f}%')
    print(f'  平均最大收益: {best["avg_max"]:.1f}%')
    print(f'  最高单笔收益: {best["max_pnl"]:.1f}%')
    print(f'  30%达标率: {best["r30"]:.1f}% ⭐')
    print(f'  25%达标率: {best["r25"]:.1f}%')
    print(f'  20%达标率: {best["r20"]:.1f}%')
    print(f'  15%达标率: {best["r15"]:.1f}%')
    print(f'  10%达标率: {best["r10"]:.1f}%')
    print(f'{"="*80}')

# 保存
import json
with open('data/fast_optimize.json', 'w', encoding='utf-8') as f:
    json.dump({'best': best, 'top15': results[:15]}, f, ensure_ascii=False, indent=2)

print('\n✓ 优化完成，结果已保存到 data/fast_optimize.json')
