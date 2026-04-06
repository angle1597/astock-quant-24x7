# -*- coding: utf-8 -*-
"""测试选股"""
import os
os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')

from data_collector import DataCollector
from auto_runner import StockPicker

# 初始化
collector = DataCollector()
picker = StockPicker(collector)

# 采集数据
print('采集数据...')
df = collector.collect_all_realtime()
print(f'采集到 {len(df)} 只股票')

# 筛选
print('\n筛选股票...')
picks = picker.screen_stocks(df)

print(f'\n符合条件: {len(picks)} 只')
print('\n=== TOP 5 ===')

for i, p in enumerate(picks[:5], 1):
    print(f'{i}. {p["code"]} {p["name"]}')
    print(f'   Price: {p["price"]} | Change: {p["change_pct"]}%')
    print(f'   VR: {p["vr"]} | Turnover: {p["turnover"]}%')
    print(f'   PE: {p["pe"]} | PB: {p["pb"]}')
    print(f'   MV: {p["mv"]}B | Score: {p["score"]}')
    print()
