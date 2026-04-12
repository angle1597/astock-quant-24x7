# -*- coding: utf-8 -*-
"""
优化回测运行器 v2 - 集成止损和市场过滤
"""
import os
import sys

# 设置输出编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd
import numpy as np

# 导入优化模块
sys.path.insert(0, os.path.dirname(__file__))
from stop_loss import StopLossStrategy, PositionManager
from market_filter import MarketEnvironment
from backtest_engine import BacktestEngine, StrategyRunner


class OptimizedBacktestRunner:
    """优化版回测运行器"""
    
    def __init__(self):
        self.backtester = BacktestEngine()
        self.stop_loss = StopLossStrategy(
            fixed_stop=-0.05,
            trailing_stop=0.03,
            max_hold_days=5
        )
        self.market_filter = MarketEnvironment()
        self.position_manager = None
    
    def run_with_optimizations(self, codes: List[str] = None) -> Dict:
        """运行带优化的回测"""
        
        # 1. 市场环境判断
        print("\n" + "="*60)
        print("Step 1: 检查市场环境")
        print("="*60)
        
        is_good_market, market_reason = self.market_filter.is_good_market()
        market_status = self.market_filter.get_market_status()
        
        print(f"市场状态: {market_status['action']} (置信度: {market_status['confidence']})")
        print(f"综合评分: {market_status['total_score']:.0f}")
        print(f"是否适合操作: {'✅' if is_good_market else '❌'} {market_reason}")
        
        # 2. 获取股票列表
        print("\n" + "="*60)
        print("Step 2: 获取测试股票")
        print("="*60)
        
        if codes is None:
            conn = sqlite3.connect(self.backtester.db_path)
            df = pd.read_sql_query('''
                SELECT DISTINCT code FROM realtime_quote 
                ORDER BY updated_at DESC LIMIT 100
            ''', conn)
            conn.close()
            codes = df['code'].tolist()
        
        print(f"测试股票: {len(codes)}只")
        
        # 3. 运行原始回测
        print("\n" + "="*60)
        print("Step 3: 运行基础回测")
        print("="*60)
        
        base_results = self.backtester.backtest_all(codes)
        
        # 4. 应用止损优化
        print("\n" + "="*60)
        print("Step 4: 应用止损优化")
        print("="*60)
        
        optimized_results = self.apply_stop_loss(base_results)
        
        # 5. 市场过滤调整
        print("\n" + "="*60)
        print("Step 5: 市场过滤调整")
        print("="*60)
        
        # 如果市场环境不好，增加一倍止损阈值
        if not is_good_market:
            self.stop_loss.fixed_stop = -0.03  # 更严格的止损
            print("⚠️ 市场环境不佳，收紧止损至-3%")
        
        # 6. 输出对比结果
        print("\n" + "="*60)
        print("回测结果对比")
        print("="*60)
        
        print("\n【原始结果】")
        print(f"最佳策略: {base_results['best_strategy']}")
        print(f"胜率: {base_results['best_win_rate']:.1f}%")
        print(f"平均收益: {base_results['best_avg_profit']:.2f}%")
        
        print("\n【优化后】")
        print(f"调整后止损: {self.stop_loss.fixed_stop:.0%}")
        print(f"移动止盈: {self.stop_loss.trailing_stop:.0%}")
        print(f"最大持仓: {self.stop_loss.max_hold_days}天")
        
        # 7. 保存结果
        output = {
            'test_date': datetime.now().strftime('%Y-%m-%d'),
            'market_status': {
                'is_good': is_good_market,
                'reason': market_reason,
                'score': market_status['total_score']
            },
            'base_results': {
                'best_strategy': base_results['best_strategy'],
                'win_rate': base_results['best_win_rate'],
                'avg_profit': base_results['best_avg_profit']
            },
            'optimizations': {
                'stop_loss': self.stop_loss.fixed_stop,
                'trailing_stop': self.stop_loss.trailing_stop,
                'max_hold_days': self.stop_loss.max_hold_days
            }
        }
        
        with open('data/backtest_v2_results.json', 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n结果已保存: data/backtest_v2_results.json")
        
        return output
    
    def apply_stop_loss(self, results: Dict) -> Dict:
        """应用止损策略到回测结果"""
        
        optimized = results.copy()
        
        # 统计止损效果
        total_trades = 0
        stopped_trades = 0
        saved_profit = 0
        
        for strategy_result in results.get('results', []):
            for trade in strategy_result.get('trades', []):
                total_trades += 1
                
                buy_price = trade.get('buy_price', 0)
                sell_price = trade.get('sell_price', 0)
                
                # 模拟止损
                stop_price = buy_price * (1 + self.stop_loss.fixed_stop)
                
                if sell_price < stop_price and sell_price < buy_price:
                    # 止损会触发
                    stopped_trades += 1
                    original_loss = (sell_price - buy_price) / buy_price
                    stopped_loss = (stop_price - buy_price) / buy_price
                    saved_profit += (original_loss - stopped_loss)
        
        print(f"止损触发次数: {stopped_trades}/{total_trades}")
        print(f"止损节省亏损: {saved_profit:.2%}")
        
        return optimized


def main():
    """主函数"""
    print("\n" + "="*60)
    print("【优化回测运行器 v2】")
    print("集成: 止损机制 + 市场环境判断")
    print("="*60)
    
    runner = OptimizedBacktestRunner()
    results = runner.run_with_optimizations()
    
    print("\n" + "="*60)
    print("回测完成")
    print("="*60)


if __name__ == '__main__':
    main()
