# -*- coding: utf-8 -*-
"""
技术指标计算器
Technical Indicators Calculator
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional


class TechnicalIndicators:
    """技术指标计算"""
    
    @staticmethod
    def calculate_ma(closes: List[float], period: int) -> float:
        """计算移动平均"""
        if len(closes) < period:
            return 0
        return sum(closes[-period:]) / period
    
    @staticmethod
    def calculate_ema(closes: List[float], period: int) -> float:
        """计算指数移动平均"""
        if len(closes) < period:
            return 0
        
        multiplier = 2 / (period + 1)
        ema = sum(closes[:period]) / period
        
        for price in closes[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    @staticmethod
    def calculate_macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
        """计算MACD"""
        if len(closes) < slow:
            return 0, 0, 0
        
        ema_fast = TechnicalIndicators.calculate_ema(closes, fast)
        ema_slow = TechnicalIndicators.calculate_ema(closes, slow)
        
        dif = ema_fast - ema_slow
        dea = TechnicalIndicators.calculate_ema([dif] * signal, signal) if dif != 0 else 0
        
        # MACD柱 = (DIF - DEA) * 2
        macd = (dif - dea) * 2
        
        return dif, dea, macd
    
    @staticmethod
    def calculate_rsi(closes: List[float], period: int = 14) -> float:
        """计算RSI"""
        if len(closes) < period + 1:
            return 50
        
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_kdj(highs: List[float], lows: List[float], closes: List[float], 
                      n: int = 9, m1: int = 3, m2: int = 3) -> Tuple[float, float, float]:
        """计算KDJ"""
        if len(closes) < n:
            return 50, 50, 50
        
        # 计算RSV
        recent_high = max(highs[-n:])
        recent_low = min(lows[-n:])
        
        if recent_high == recent_low:
            rsv = 50
        else:
            rsv = (closes[-1] - recent_low) / (recent_high - recent_low) * 100
        
        # 计算K, D, J
        # 简化计算
        k = 50
        d = 50
        
        for _ in range(n):
            k = (2/3) * k + (1/3) * rsv
            d = (2/3) * d + (1/3) * k
        
        j = 3 * k - 2 * d
        
        return k, d, j
    
    @staticmethod
    def calculate_bollinger(closes: List[float], period: int = 20, std_dev: int = 2) -> Tuple[float, float, float]:
        """计算布林带"""
        if len(closes) < period:
            return 0, 0, 0
        
        recent = closes[-period:]
        ma = sum(recent) / period
        
        variance = sum((x - ma) ** 2 for x in recent) / period
        std = variance ** 0.5
        
        upper = ma + std_dev * std
        lower = ma - std_dev * std
        
        return upper, ma, lower
    
    @staticmethod
    def calculate_turnover_rate(volumes: List[float], outstanding: float) -> float:
        """计算换手率"""
        if outstanding == 0 or len(volumes) == 0:
            return 0
        
        # 今日换手率 = 成交量 / 流通股本 * 100
        today_vol = volumes[-1]
        return (today_vol / outstanding) * 100


class StockAnalyzer:
    """股票分析器"""
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
    
    def analyze(self, klines: pd.DataFrame) -> dict:
        """综合分析"""
        if klines.empty or len(klines) < 30:
            return {}
        
        closes = klines['close'].tolist()
        highs = klines['high'].tolist()
        lows = klines['low'].tolist()
        volumes = klines['volume'].tolist()
        
        # 计算各项指标
        ma5 = self.indicators.calculate_ma(closes, 5)
        ma10 = self.indicators.calculate_ma(closes, 10)
        ma20 = self.indicators.calculate_ma(closes, 20)
        ma60 = self.indicators.calculate_ma(closes, 60) if len(closes) >= 60 else 0
        
        dif, dea, macd = self.indicators.calculate_macd(closes)
        rsi = self.indicators.calculate_rsi(closes)
        k, d, j = self.indicators.calculate_kdj(highs, lows, closes)
        upper, ma, lower = self.indicators.calculate_bollinger(closes)
        
        # 当前价格位置
        current_price = closes[-1]
        
        # 趋势判断
        trend = 'NEUTRAL'
        if ma5 > ma10 > ma20:
            trend = 'BULLISH'
        elif ma5 < ma10 < ma20:
            trend = 'BEARISH'
        
        # 买入信号
        signals = []
        
        # MACD金叉
        if dif > dea and dif < 0:
            signals.append('MACD_GOLDEN')
        
        # KDJ超卖
        if k < 20 or j < 0:
            signals.append('KDJ_OVERSOLD')
        
        # RSI超卖
        if rsi < 30:
            signals.append('RSI_OVERSOLD')
        
        # 布林下轨
        if current_price < lower:
            signals.append('BOLL_LOWER')
        
        # 放量突破
        if len(volumes) >= 5:
            avg_vol = sum(volumes[-5:]) / 5
            if volumes[-1] > avg_vol * 1.5:
                signals.append('VOLUME_BREAKOUT')
        
        return {
            'price': current_price,
            'ma5': round(ma5, 2),
            'ma10': round(ma10, 2),
            'ma20': round(ma20, 2),
            'ma60': round(ma60, 2),
            'macd': {
                'dif': round(dif, 3),
                'dea': round(dea, 3),
                'macd': round(macd, 3)
            },
            'rsi': round(rsi, 1),
            'kdj': {
                'k': round(k, 1),
                'd': round(d, 1),
                'j': round(j, 1)
            },
            'bollinger': {
                'upper': round(upper, 2),
                'middle': round(ma, 2),
                'lower': round(lower, 2)
            },
            'trend': trend,
            'signals': signals
        }
    
    def score_by_indicators(self, analysis: dict, current_change: float) -> dict:
        """根据指标评分"""
        if not analysis:
            return {'score': 0, 'details': {}}
        
        score = 50  # 基础分
        details = {}
        
        # 趋势加分
        if analysis['trend'] == 'BULLISH':
            score += 20
            details['trend'] = '+20 (多头排列)'
        elif analysis['trend'] == 'BEARISH':
            score -= 10
            details['trend'] = '-10 (空头排列)'
        
        # MACD
        macd = analysis['macd']
        if macd['dif'] > macd['dea']:
            score += 10
            details['macd'] = '+10 (MACD多头)'
        
        # RSI
        rsi = analysis['rsi']
        if 40 <= rsi <= 70:
            score += 10
            details['rsi'] = '+10 (RSI适中)'
        elif rsi < 30:
            score += 15
            details['rsi'] = '+15 (RSI超卖)'
        elif rsi > 80:
            score -= 10
            details['rsi'] = '-10 (RSI超买)'
        
        # KDJ
        kdj = analysis['kdj']
        if kdj['k'] > kdj['d'] and kdj['k'] < 80:
            score += 10
            details['kdj'] = '+10 (KDJ金叉)'
        
        # 买入信号
        signals = analysis.get('signals', [])
        if 'MACD_GOLDEN' in signals:
            score += 10
            details['signal'] = '+10 (MACD金叉)'
        if 'VOLUME_BREAKOUT' in signals:
            score += 10
            details['volume'] = '+10 (放量突破)'
        
        return {'score': score, 'details': details}
