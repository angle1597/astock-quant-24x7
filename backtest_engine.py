# -*- coding: utf-8 -*-
"""
策略回测引擎
Strategy Backtesting Engine
集成多个优质策略并进行回测
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import numpy as np

# 导入技术指标
sys.path.insert(0, os.path.dirname(__file__))
from technical_analysis import TechnicalIndicators
from stop_loss import StopLossStrategy, PositionManager
from market_filter import MarketEnvironment

class StrategyBase:
    """策略基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.indicators = TechnicalIndicators()
    
    def should_buy(self, df: pd.DataFrame) -> Dict:
        """判断是否买入"""
        raise NotImplementedError
    
    def should_sell(self, df: pd.DataFrame, position: Dict) -> Dict:
        """判断是否卖出"""
        raise NotImplementedError


class GoldenCrossStrategy(StrategyBase):
    """金叉策略 - MA5上穿MA20"""
    
    def __init__(self):
        super().__init__("GoldenCross")
    
    def should_buy(self, df: pd.DataFrame) -> Dict:
        if len(df) < 25:
            return {'signal': False, 'reason': '数据不足'}
        
        closes = df['close'].tolist()
        ma5 = self.indicators.calculate_ma(closes, 5)
        ma20 = self.indicators.calculate_ma(closes, 20)
        ma60 = self.indicators.calculate_ma(closes, 60) if len(closes) >= 60 else 0
        
        # 当前价格
        current = closes[-1]
        
        # 前一天MA5 < MA20，今天MA5 >= MA20
        ma5_prev = self.indicators.calculate_ma(closes[:-1] + [0], 5) if len(closes) >= 1 else 0
        ma20_prev = self.indicators.calculate_ma(closes[:-1] + [0], 20) if len(closes) >= 1 else 0
        
        if ma5_prev < ma20_prev and ma5 >= ma20:
            return {
                'signal': True,
                'reason': f'金叉形成 MA5={ma5:.2f} > MA20={ma20:.2f}',
                'ma5': ma5,
                'ma20': ma20
            }
        
        return {'signal': False, 'reason': f'MA5={ma5:.2f}, MA20={ma20:.2f} 未形成金叉'}


class MACDCrossStrategy(StrategyBase):
    """MACD金叉策略"""
    
    def __init__(self):
        super().__init__("MACDCross")
    
    def should_buy(self, df: pd.DataFrame) -> Dict:
        if len(df) < 35:
            return {'signal': False, 'reason': '数据不足'}
        
        closes = df['close'].tolist()
        dif, dea, macd = self.indicators.calculate_macd(closes)
        
        # 计算前一天的DIF和DEA
        dif_prev = self.indicators.calculate_macd(closes[:-1] + [closes[-2]] if len(closes) > 1 else closes)[0]
        dea_prev = self.indicators.calculate_macd(closes[:-1] + [closes[-2]] if len(closes) > 1 else closes)[1]
        
        # DIF从下方上穿DEA
        if dif_prev < dea_prev and dif >= dea and dif < 0:
            return {
                'signal': True,
                'reason': f'MACD金叉 DIF={dif:.3f} > DEA={dea:.3f}',
                'dif': dif,
                'dea': dea
            }
        
        return {'signal': False, 'reason': f'DIF={dif:.3f}, DEA={dea:.3f}'}


class RSIStrategy(StrategyBase):
    """RSI超卖策略"""
    
    def __init__(self, oversold: int = 30, overbought: int = 70):
        super().__init__(f"RSI_{oversold}_{overbought}")
        self.oversold = oversold
        self.overbought = overbought
    
    def should_buy(self, df: pd.DataFrame) -> Dict:
        if len(df) < 15:
            return {'signal': False, 'reason': '数据不足'}
        
        closes = df['close'].tolist()
        rsi = self.indicators.calculate_rsi(closes)
        
        # RSI从超卖区域反弹
        if rsi < self.oversold:
            return {
                'signal': True,
                'reason': f'RSI超卖 RSI={rsi:.1f}',
                'rsi': rsi
            }
        
        return {'signal': False, 'reason': f'RSI={rsi:.1f}'}


class BollingerBounceStrategy(StrategyBase):
    """布林带反弹策略"""
    
    def __init__(self):
        super().__init__("BollingerBounce")
    
    def should_buy(self, df: pd.DataFrame) -> Dict:
        if len(df) < 25:
            return {'signal': False, 'reason': '数据不足'}
        
        closes = df['close'].tolist()
        upper, middle, lower = self.indicators.calculate_bollinger(closes)
        
        current = closes[-1]
        
        # 价格触及布林下轨
        if current <= lower:
            return {
                'signal': True,
                'reason': f'触及布林下轨 Price={current:.2f} < Lower={lower:.2f}',
                'upper': upper,
                'middle': middle,
                'lower': lower
            }
        
        return {'signal': False, 'reason': f'Price={current:.2f}, 距下轨{(current-lower)/lower*100:.1f}%'}


class VolumeBreakoutStrategy(StrategyBase):
    """放量突破策略"""
    
    def __init__(self, volume_ratio: float = 2.0):
        super().__init__(f"VolumeBreakout_{volume_ratio}x")
        self.volume_ratio = volume_ratio
    
    def should_buy(self, df: pd.DataFrame) -> Dict:
        if len(df) < 20:
            return {'signal': False, 'reason': '数据不足'}
        
        volumes = df['volume'].tolist()
        closes = df['close'].tolist()
        
        # 计算平均成交量
        avg_vol = sum(volumes[-20:-1]) / 19
        today_vol = volumes[-1]
        
        # 计算均线
        ma5 = self.indicators.calculate_ma(closes, 5)
        ma10 = self.indicators.calculate_ma(closes, 10)
        current = closes[-1]
        
        vol_ratio = today_vol / avg_vol if avg_vol > 0 else 0
        
        # 放量 + 突破MA5 + MA5 > MA10
        if vol_ratio >= self.volume_ratio and current > ma5 and ma5 > ma10:
            return {
                'signal': True,
                'reason': f'放量突破 vol_ratio={vol_ratio:.1f}x, Price>{ma5:.2f}',
                'vol_ratio': vol_ratio,
                'ma5': ma5,
                'ma10': ma10
            }
        
        return {'signal': False, 'reason': f'vol_ratio={vol_ratio:.1f}x, 条件不满足'}


class MultiFactorStrategy(StrategyBase):
    """多因子综合策略"""
    
    def __init__(self):
        super().__init__("MultiFactor")
    
    def should_buy(self, df: pd.DataFrame) -> Dict:
        if len(df) < 30:
            return {'signal': False, 'reason': '数据不足'}
        
        closes = df['close'].tolist()
        highs = df['high'].tolist()
        lows = df['low'].tolist()
        volumes = df['volume'].tolist()
        
        # 计算各项指标
        ma5 = self.indicators.calculate_ma(closes, 5)
        ma10 = self.indicators.calculate_ma(closes, 10)
        ma20 = self.indicators.calculate_ma(closes, 20)
        
        dif, dea, macd = self.indicators.calculate_macd(closes)
        rsi = self.indicators.calculate_rsi(closes)
        k, d, j = self.indicators.calculate_kdj(highs, lows, closes)
        
        upper, middle, lower = self.indicators.calculate_bollinger(closes)
        
        current = closes[-1]
        
        # 评分
        score = 0
        details = []
        
        # 趋势条件 (40分)
        if ma5 > ma10 > ma20:
            score += 40
            details.append('多头排列+40')
        elif ma5 > ma10:
            score += 20
            details.append('MA5>MA10+20')
        
        # MACD条件 (30分)
        if dif > dea and dif < 0:
            score += 30
            details.append('MACD多头+30')
        elif dif > dea:
            score += 15
            details.append('MACD金叉+15')
        
        # RSI条件 (20分)
        if 30 < rsi < 50:
            score += 20
            details.append('RSI适中+20')
        elif rsi < 30:
            score += 25
            details.append('RSI超卖+25')
        
        # KDJ条件 (10分)
        if k > d and k < 80:
            score += 10
            details.append('KDJ金叉+10')
        
        signal = score >= 60
        
        return {
            'signal': signal,
            'reason': f'评分{score}分: {", ".join(details)}' if details else f'评分{score}分, 条件不足',
            'score': score,
            'details': details,
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'rsi': rsi,
            'kdj_k': k,
            'kdj_d': d
        }


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, db_path: str = 'data/stocks.db'):
        self.db_path = db_path
        self.strategies = self._register_strategies()
        self.stop_loss = StopLossStrategy()
        self.market_filter = MarketEnvironment()
    
    def _register_strategies(self) -> List[StrategyBase]:
        """注册所有策略"""
        return [
            GoldenCrossStrategy(),
            MACDCrossStrategy(),
            RSIStrategy(30, 70),
            RSIStrategy(40, 60),
            BollingerBounceStrategy(),
            VolumeBreakoutStrategy(1.5),
            VolumeBreakoutStrategy(2.0),
            MultiFactorStrategy(),
        ]
    
    def get_kline_data(self, code: str, days: int = 60) -> pd.DataFrame:
        """获取K线数据"""
        conn = sqlite3.connect(self.db_path)
        
        df = pd.read_sql_query('''
            SELECT date, open, high, low, close, volume
            FROM daily_kline
            WHERE code = ?
            ORDER BY date DESC
            LIMIT ?
        ''', conn, params=(code, days))
        
        conn.close()
        
        if df.empty:
            return df
        
        # 反转数据，使日期升序
        df = df.iloc[::-1]
        
        return df
    
    def backtest_strategy(self, strategy: StrategyBase, codes: List[str], 
                         holding_days: int = 5) -> Dict:
        """回测单个策略"""
        results = []
        
        for code in codes:
            df = self.get_kline_data(code)
            
            if df.empty or len(df) < 30:
                continue
            
            # 模拟每日检查
            for i in range(20, len(df)):
                window = df.iloc[:i+1]
                
                # 检查买入信号
                buy_signal = strategy.should_buy(window)
                
                if buy_signal['signal']:
                    buy_price = window.iloc[-1]['close']
                    buy_date = window.iloc[-1]['date']
                    
                    # 模拟持有
                    sell_idx = min(i + holding_days, len(df) - 1)
                    sell_price = df.iloc[sell_idx]['close']
                    sell_date = df.iloc[sell_idx]['date']
                    
                    profit_pct = (sell_price - buy_price) / buy_price * 100
                    
                    results.append({
                        'code': code,
                        'buy_date': buy_date,
                        'sell_date': sell_date,
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'profit_pct': profit_pct,
                        'holding_days': sell_idx - i,
                        'reason': buy_signal.get('reason', ''),
                        'strategy': strategy.name
                    })
        
        return {
            'strategy': strategy.name,
            'total_trades': len(results),
            'trades': results,
            'win_rate': sum(1 for r in results if r['profit_pct'] > 0) / len(results) * 100 if results else 0,
            'avg_profit': np.mean([r['profit_pct'] for r in results]) if results else 0,
            'max_profit': max([r['profit_pct'] for r in results]) if results else 0,
            'max_loss': min([r['profit_pct'] for r in results]) if results else 0,
        }
    
    def backtest_all(self, codes: List[str], holding_days: int = 5) -> Dict:
        """回测所有策略"""
        all_results = []
        
        for strategy in self.strategies:
            result = self.backtest_strategy(strategy, codes, holding_days)
            all_results.append(result)
            print(f"  {strategy.name}: {result['total_trades']}次交易, 胜率{result['win_rate']:.1f}%, 平均收益{result['avg_profit']:.2f}%")
        
        # 排序
        all_results.sort(key=lambda x: x['avg_profit'], reverse=True)
        
        return {
            'test_date': datetime.now().isoformat(),
            'test_codes': len(codes),
            'holding_days': holding_days,
            'results': all_results,
            'best_strategy': all_results[0]['strategy'] if all_results else None,
            'best_win_rate': all_results[0]['win_rate'] if all_results else 0,
            'best_avg_profit': all_results[0]['avg_profit'] if all_results else 0,
        }


class StrategyRunner:
    """策略运行器"""
    
    def __init__(self):
        self.backtester = BacktestEngine()
    
    def run_backtest(self, codes: List[str] = None) -> Dict:
        """运行回测"""
        if codes is None:
            # 从数据库获取所有股票
            conn = sqlite3.connect(self.backtester.db_path)
            df = pd.read_sql_query('''
                SELECT DISTINCT code FROM realtime_quote 
                ORDER BY updated_at DESC LIMIT 100
            ''', conn)
            conn.close()
            codes = df['code'].tolist()
        
        print(f"\n{'='*60}")
        print(f"开始回测 {len(codes)} 只股票")
        print(f"{'='*60}\n")
        
        results = self.backtester.backtest_all(codes)
        
        # 打印结果
        print(f"\n{'='*60}")
        print("回测结果汇总")
        print(f"{'='*60}")
        print(f"测试日期: {results['test_date']}")
        print(f"测试股票: {results['test_codes']}只")
        print(f"持有周期: {results['holding_days']}天")
        print(f"\n最佳策略: {results['best_strategy']}")
        print(f"胜率: {results['best_win_rate']:.1f}%")
        print(f"平均收益: {results['best_avg_profit']:.2f}%")
        
        return results


def main():
    """主函数"""
    runner = StrategyRunner()
    results = runner.run_backtest()
    
    # 保存结果
    with open('data/backtest_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到 data/backtest_results.json")


if __name__ == '__main__':
    main()
