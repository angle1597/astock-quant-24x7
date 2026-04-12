# -*- coding: utf-8 -*-
from auto_engine import AutoEngine

e = AutoEngine()

print('采集数据...')
e.collect_realtime_data()

print('筛选股票...')
candidates = e.screen_stocks()
print(f'候选股: {len(candidates)}只')

if candidates:
    best = candidates[0]
    print('\n=== 最佳股票 ===')
    print('代码:', best['code'])
    print('价格:', best['price'], '元')
    print('评分:', best['score'], '分')
    print('\nTOP 5:')
    for i, s in enumerate(candidates[:5], 1):
        print(i, '.', s['code'], '评分', s['score'])
