# -*- coding: utf-8 -*-
"""采集K线数据并回测"""
import os
import sys
import time
import random

os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')
sys.path.insert(0, os.getcwd())

from data_collector import DataCollector
from backtest_engine import StrategyRunner

def main():
    print("=" * 60)
    print("采集K线数据并进行回测")
    print("=" * 60)
    
    collector = DataCollector()
    
    # 获取股票列表
    print("\n[1/3] 获取股票列表...")
    df = collector.get_realtime_quotes_eastmoney()
    
    if df.empty:
        print("无数据")
        return
    
    codes = df['code'].tolist()[:50]  # 取前50只
    print(f"选取 {len(codes)} 只股票")
    
    # 采集K线
    print("\n[2/3] 采集K线数据...")
    for i, code in enumerate(codes):
        print(f"  {i+1}/{len(codes)}: {code}", end='\r')
        
        market = '1' if code.startswith('6') else '0'
        klines = collector.get_kline_eastmoney(code, period='101')
        
        if not klines.empty:
            collector.save_klines(klines)
        
        time.sleep(0.3 + random.uniform(0, 0.3))
    
    print("\nK线采集完成")
    
    # 运行回测
    print("\n[3/3] 运行回测...")
    runner = StrategyRunner()
    results = runner.run_backtest(codes)
    
    print("\n" + "=" * 60)
    print("TOP 3 策略")
    print("=" * 60)
    
    for i, r in enumerate(results['results'][:3], 1):
        print(f"{i}. {r['strategy']}")
        print(f"   胜率: {r['win_rate']:.1f}%")
        print(f"   平均收益: {r['avg_profit']:.2f}%")
        print(f"   交易次数: {r['total_trades']}")
        print()

if __name__ == '__main__':
    main()
