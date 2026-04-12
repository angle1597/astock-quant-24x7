# -*- coding: utf-8 -*-
"""
多策略组合评分系统
Multi-Strategy Ensemble Scoring
"""
import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

# 设置编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class StrategyEnsemble:
    """
    多策略组合评分系统
    
    将多个策略的信号组合，计算综合评分
    """
    
    def __init__(self):
        # 策略权重配置
        self.weights = {
            'golden_cross': 0.15,      # 趋势跟踪
            'macd_cross': 0.15,       # 趋势跟踪
            'rsi_oversold': 0.20,     # 均值回归
            'bollinger_bounce': 0.15, # 均值回归
            'volume_breakout': 0.20,  # 动量
            'multi_factor': 0.15,     # 综合因子
        }
        
        # 策略信号映射
        self.signal_map = {
            'strong_buy': 1.0,
            'buy': 0.75,
            'weak_buy': 0.5,
            'hold': 0.25,
            'weak_sell': 0,
            'sell': 0,
            'strong_sell': 0,
        }
    
    def calculate_ensemble_score(self, signals: Dict[str, str]) -> float:
        """
        计算组合评分
        
        Args:
            signals: 各策略的信号 {'golden_cross': 'buy', ...}
        
        Returns:
            float: 组合评分 0-100
        """
        total_score = 0
        total_weight = 0
        
        for strategy, signal in signals.items():
            weight = self.weights.get(strategy, 0)
            signal_score = self.signal_map.get(signal, 0)
            
            if weight > 0:
                total_score += signal_score * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0
        
        # 归一化到0-100
        normalized_score = (total_score / total_weight) * 100
        
        return round(normalized_score, 1)
    
    def get_top_picks(self, stocks: List[Dict], top_n: int = 5) -> List[Dict]:
        """
        获取组合评分最高的股票
        
        Args:
            stocks: 股票列表，每个包含策略信号
            top_n: 返回数量
        
        Returns:
            List[Dict]: TOP N 股票
        """
        # 计算组合评分
        for stock in stocks:
            signals = stock.get('signals', {})
            stock['ensemble_score'] = self.calculate_ensemble_score(signals)
        
        # 按组合评分排序
        sorted_stocks = sorted(stocks, key=lambda x: x['ensemble_score'], reverse=True)
        
        return sorted_stocks[:top_n]
    
    def generate_signals_from_metrics(self, stock: Dict) -> Dict[str, str]:
        """
        从股票指标生成各策略信号
        
        Args:
            stock: 股票数据
        
        Returns:
            Dict: 各策略信号
        """
        signals = {}
        
        # 获取关键指标
        price = stock.get('price', 0)
        change_pct = stock.get('change_pct', 0)
        volume = stock.get('volume', 0)
        turnover = stock.get('turnover', 0)
        pe = stock.get('pe', 0)
        mv = stock.get('market_cap', 0)
        
        # 1. 趋势判断 (简化版)
        if change_pct >= 5:
            signals['golden_cross'] = 'strong_buy'
            signals['macd_cross'] = 'buy'
        elif change_pct >= 2:
            signals['golden_cross'] = 'buy'
            signals['macd_cross'] = 'weak_buy'
        elif change_pct >= 0:
            signals['golden_cross'] = 'weak_buy'
            signals['macd_cross'] = 'hold'
        else:
            signals['golden_cross'] = 'hold'
            signals['macd_cross'] = 'hold'
        
        # 2. RSI判断 (用跌幅代替)
        if change_pct <= -5:
            signals['rsi_oversold'] = 'strong_buy'  # 超跌反弹
        elif change_pct <= -3:
            signals['rsi_oversold'] = 'buy'
        elif change_pct <= -1:
            signals['rsi_oversold'] = 'weak_buy'
        else:
            signals['rsi_oversold'] = 'hold'
        
        # 3. 布林带 (用换手率判断)
        if turnover >= 10:
            signals['bollinger_bounce'] = 'strong_buy'
        elif turnover >= 5:
            signals['bollinger_bounce'] = 'buy'
        elif turnover >= 3:
            signals['bollinger_bounce'] = 'weak_buy'
        else:
            signals['bollinger_bounce'] = 'hold'
        
        # 4. 成交量突破
        if turnover >= 8:
            signals['volume_breakout'] = 'strong_buy'
        elif turnover >= 5:
            signals['volume_breakout'] = 'buy'
        elif turnover >= 3:
            signals['volume_breakout'] = 'weak_buy'
        else:
            signals['volume_breakout'] = 'hold'
        
        # 5. 多因子综合
        factor_score = 0
        if 0 < pe <= 20: factor_score += 25
        elif 0 < pe <= 40: factor_score += 15
        if 20 <= mv <= 100: factor_score += 25
        elif 100 <= mv <= 200: factor_score += 15
        if turnover >= 5: factor_score += 25
        elif turnover >= 3: factor_score += 15
        if change_pct >= 3: factor_score += 25
        elif change_pct >= 0: factor_score += 15
        
        if factor_score >= 75:
            signals['multi_factor'] = 'strong_buy'
        elif factor_score >= 50:
            signals['multi_factor'] = 'buy'
        elif factor_score >= 25:
            signals['multi_factor'] = 'weak_buy'
        else:
            signals['multi_factor'] = 'hold'
        
        return signals
    
    def analyze_portfolio(self, stocks: List[Dict]) -> Dict:
        """
        分析组合表现
        
        Args:
            stocks: 股票列表
        
        Returns:
            Dict: 组合分析结果
        """
        # 为每只股票生成信号
        for stock in stocks:
            stock['signals'] = self.generate_signals_from_metrics(stock)
            stock['ensemble_score'] = self.calculate_ensemble_score(stock['signals'])
        
        # 按组合评分排序
        sorted_stocks = sorted(stocks, key=lambda x: x['ensemble_score'], reverse=True)
        
        # TOP 5
        top5 = sorted_stocks[:5]
        
        # 策略一致性分析
        strategy_consensus = {}
        for strategy in self.weights.keys():
            buy_count = sum(1 for s in sorted_stocks if s['signals'].get(strategy) in ['buy', 'strong_buy'])
            strategy_consensus[strategy] = {
                'buy_ratio': buy_count / len(stocks) if stocks else 0,
                'buy_count': buy_count
            }
        
        return {
            'all_stocks': sorted_stocks,
            'top5': top5,
            'strategy_consensus': strategy_consensus,
            'avg_score': np.mean([s['ensemble_score'] for s in stocks]) if stocks else 0,
        }


def main():
    """测试运行"""
    print("\n" + "="*60)
    print("【多策略组合评分系统】")
    print("="*60)
    
    ensemble = StrategyEnsemble()
    
    # 测试数据
    test_stocks = [
        {'code': '603138', 'name': '海量数据', 'price': 19.91, 'change_pct': 10.0, 'turnover': 10.1, 'pe': 45, 'market_cap': 58.5},
        {'code': '600654', 'name': '中安科', 'price': 4.40, 'change_pct': 10.0, 'turnover': 11.3, 'pe': -5, 'market_cap': 126.6},
        {'code': '603538', 'name': '美诺华', 'price': 43.24, 'change_pct': 10.0, 'turnover': 7.8, 'pe': 35, 'market_cap': 95.3},
        {'code': '600114', 'name': '东睦股份', 'price': 30.04, 'change_pct': 10.0, 'turnover': 3.8, 'pe': 28, 'market_cap': 189.7},
        {'code': '603045', 'name': '福达合金', 'price': 31.35, 'change_pct': 10.0, 'turnover': 3.5, 'pe': 52, 'market_cap': 42.5},
    ]
    
    # 分析组合
    result = ensemble.analyze_portfolio(test_stocks)
    
    print("\n【组合分析结果】")
    print("-"*60)
    
    print("\nTOP 5 推荐:")
    print("| 排名 | 代码 | 名称 | 组合评分 | 主要信号 |")
    print("|:---:|:---:|:---:|:---:|:---:|")
    
    for i, stock in enumerate(result['top5'], 1):
        signals = stock['signals']
        main_signal = max(signals.items(), key=lambda x: ensemble.signal_map.get(x[1], 0))
        print(f"| {i} | {stock['code']} | {stock['name']} | {stock['ensemble_score']} | {main_signal[0]} |")
    
    print("\n策略一致性分析:")
    for strategy, data in result['strategy_consensus'].items():
        bar = "=" * int(data['buy_ratio'] * 20)
        print(f"  {strategy:20s} [{bar:<20}] {data['buy_ratio']:.0%}")
    
    print(f"\n平均组合评分: {result['avg_score']:.1f}")
    
    # 保存结果
    output = {
        'timestamp': datetime.now().isoformat(),
        'top5': result['top5'],
        'avg_score': result['avg_score'],
        'strategy_consensus': result['strategy_consensus']
    }
    
    with open('data/ensemble_results.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    
    print("\n结果已保存: data/ensemble_results.json")


if __name__ == '__main__':
    main()
