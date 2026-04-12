# -*- coding: utf-8 -*-
"""
市场环境判断模块
Market Environment Filter Module
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import pandas as pd
import numpy as np

# 导入数据采集
sys.path.insert(0, os.path.dirname(__file__))
from data_collector import DataCollector

logger = logging.getLogger('MarketFilter')


class MarketEnvironment:
    """
    市场环境判断
    
    判断大盘环境是否适合操作:
    1. 趋势判断 - MA位置关系
    2. 动量判断 - 涨跌幅
    3. 情绪判断 - 涨跌停数量
    4. 资金判断 - 北向资金流向
    """
    
    def __init__(self):
        self.collector = DataCollector()
        self.index_codes = {
            'sh': '000001',  # 上证指数
            'sz': '399001',  # 深证成指
            'cyb': '399006',  # 创业板指
        }
    
    def get_index_data(self, code: str, days: int = 60) -> Optional[pd.DataFrame]:
        """
        获取指数数据
        
        Args:
            code: 指数代码
            days: 天数
        
        Returns:
            DataFrame: 指数数据
        """
        try:
            # 使用东方财富接口
            df = self.collector.get_index_kline(code, days)
            return df
        except Exception as e:
            logger.error(f"获取指数数据失败: {e}")
            return None
    
    def check_trend(self, df: pd.DataFrame) -> Dict:
        """
        趋势判断
        
        Args:
            df: 指数数据
        
        Returns:
            Dict: 趋势状态
        """
        if df is None or len(df) < 60:
            return {'trend': 'unknown', 'score': 0}
        
        closes = df['close'].values
        current = closes[-1]
        
        # 计算均线
        ma5 = np.mean(closes[-5:])
        ma10 = np.mean(closes[-10:])
        ma20 = np.mean(closes[-20:])
        ma60 = np.mean(closes[-60:])
        
        # 判断趋势
        if current > ma5 > ma10 > ma20 > ma60:
            trend = 'strong_up'
            score = 100
        elif current > ma20 > ma60:
            trend = 'up'
            score = 80
        elif current > ma20:
            trend = 'weak_up'
            score = 60
        elif current < ma5 < ma10 < ma20 < ma60:
            trend = 'strong_down'
            score = 0
        elif current < ma20 < ma60:
            trend = 'down'
            score = 20
        elif current < ma20:
            trend = 'weak_down'
            score = 40
        else:
            trend = 'sideways'
            score = 50
        
        return {
            'trend': trend,
            'score': score,
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'ma60': ma60,
            'current': current
        }
    
    def check_momentum(self, df: pd.DataFrame) -> Dict:
        """
        动量判断
        
        Args:
            df: 指数数据
        
        Returns:
            Dict: 动量状态
        """
        if df is None or len(df) < 5:
            return {'momentum': 'unknown', 'score': 0}
        
        closes = df['close'].values
        
        # 计算涨跌幅
        change_1d = (closes[-1] / closes[-2] - 1) * 100
        change_3d = (closes[-1] / closes[-4] - 1) * 100
        change_5d = (closes[-1] / closes[-6] - 1) * 100
        
        # 判断动量
        if change_1d > 1:
            momentum = 'strong_up'
            score = 100
        elif change_1d > 0:
            momentum = 'up'
            score = 70
        elif change_1d > -1:
            momentum = 'neutral'
            score = 50
        elif change_1d > -2:
            momentum = 'down'
            score = 30
        else:
            momentum = 'strong_down'
            score = 0
        
        return {
            'momentum': momentum,
            'score': score,
            'change_1d': change_1d,
            'change_3d': change_3d,
            'change_5d': change_5d
        }
    
    def check_sentiment(self) -> Dict:
        """
        情绪判断
        
        Returns:
            Dict: 情绪状态
        """
        try:
            # 获取涨跌停数据
            limit_up = self.collector.get_limit_up_count()
            limit_down = self.collector.get_limit_down_count()
            
            total = limit_up + limit_down
            if total == 0:
                return {'sentiment': 'unknown', 'score': 50}
            
            # 涨跌停比
            ratio = limit_up / total
            
            # 判断情绪
            if ratio > 0.7:
                sentiment = 'very_bullish'
                score = 100
            elif ratio > 0.55:
                sentiment = 'bullish'
                score = 75
            elif ratio > 0.45:
                sentiment = 'neutral'
                score = 50
            elif ratio > 0.3:
                sentiment = 'bearish'
                score = 25
            else:
                sentiment = 'very_bearish'
                score = 0
            
            return {
                'sentiment': sentiment,
                'score': score,
                'limit_up': limit_up,
                'limit_down': limit_down,
                'ratio': ratio
            }
            
        except Exception as e:
            logger.error(f"情绪判断失败: {e}")
            return {'sentiment': 'unknown', 'score': 50}
    
    def get_market_status(self) -> Dict:
        """
        获取市场综合状态
        
        Returns:
            Dict: 市场状态
        """
        # 获取上证指数数据
        sh_data = self.get_index_data(self.index_codes['sh'])
        
        # 趋势判断
        trend = self.check_trend(sh_data)
        
        # 动量判断
        momentum = self.check_momentum(sh_data)
        
        # 情绪判断
        sentiment = self.check_sentiment()
        
        # 综合评分 (权重: 趋势40%, 动量30%, 情绪30%)
        total_score = (
            trend['score'] * 0.4 +
            momentum['score'] * 0.3 +
            sentiment['score'] * 0.3
        )
        
        # 判断是否适合操作
        if total_score >= 60:
            action = 'buy'
            confidence = 'high'
        elif total_score >= 40:
            action = 'hold'
            confidence = 'medium'
        else:
            action = 'sell'
            confidence = 'low'
        
        return {
            'trend': trend,
            'momentum': momentum,
            'sentiment': sentiment,
            'total_score': total_score,
            'action': action,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()
        }
    
    def is_good_market(self) -> Tuple[bool, str]:
        """
        判断市场环境是否适合操作
        
        Returns:
            Tuple[bool, str]: (是否适合, 原因)
        """
        status = self.get_market_status()
        
        # 总分低于40不适合操作
        if status['total_score'] < 40:
            return False, f"市场环境不佳 (评分: {status['total_score']:.0f})"
        
        # 趋势向下不适合操作
        if status['trend']['trend'] in ['strong_down', 'down']:
            return False, f"趋势向下 ({status['trend']['trend']})"
        
        # 单日跌幅过大不适合操作
        if status['momentum']['change_1d'] < -2:
            return False, f"单日跌幅过大 ({status['momentum']['change_1d']:.2f}%)"
        
        return True, f"市场环境良好 (评分: {status['total_score']:.0f})"


# 测试
if __name__ == '__main__':
    market = MarketEnvironment()
    
    # 获取市场状态
    status = market.get_market_status()
    
    print("\n=== 市场环境分析 ===")
    print(f"趋势: {status['trend']['trend']} (评分: {status['trend']['score']})")
    print(f"动量: {status['momentum']['momentum']} (评分: {status['momentum']['score']})")
    print(f"情绪: {status['sentiment']['sentiment']} (评分: {status['sentiment']['score']})")
    print(f"综合评分: {status['total_score']:.0f}")
    print(f"建议操作: {status['action']} (置信度: {status['confidence']})")
    
    # 判断是否适合操作
    is_good, reason = market.is_good_market()
    print(f"\n是否适合操作: {'✅' if is_good else '❌'} {reason}")
