# -*- coding: utf-8 -*-
"""快速采集和回测"""
import os, sys, time, random

os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')
sys.path.insert(0, os.getcwd())

from data_collector import DataCollector
from backtest_engine import StrategyRunner

collector = DataCollector()
print('采集行情...')
df = collector.get_realtime_quotes_eastmoney()
codes = df['code'].tolist()[:20]

print('采集 K线...')
for i, code in enumerate(codes):
    sys.stdout.write('%d/%d %s\r' % (i+1, len(codes), code))
    sys.stdout.flush()
    market = '1' if code.startswith('6') else '0'
    klines = collector.get_kline_eastmoney(code)
    if not klines.empty:
        collector.save_klines(klines)
    time.sleep(0.5)

print('\n运行回测...')
runner = StrategyRunner()
results = runner.run_backtest(codes)

print('\n=== TOP 3 ===')
for i, r in enumerate(results['results'][:3], 1):
    s = r['strategy']
    wr = r['win_rate']
    ap = r['avg_profit']
    print('%d. %s: 胜率%.1f%%, 平均收益%.2f%%' % (i, s, wr, ap))
