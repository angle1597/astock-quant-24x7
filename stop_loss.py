# -*- coding: utf-8 -*-
"""
止损策略模块
Stop Loss Strategy Module
"""

from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger('StopLoss')


class StopLossStrategy:
    """
    止损策略
    
    支持多种止损方式:
    1. 固定止损 - 亏损超过阈值
    2. 移动止盈 - 从最高点回落超过阈值
    3. 时间止损 - 持仓超过天数
    4. ATR止损 - 基于波动率的动态止损
    """
    
    def __init__(self, 
                 fixed_stop: float = -0.05,
                 trailing_stop: float = 0.03,
                 max_hold_days: int = 5,
                 atr_multiplier: float = 2.0):
        """
        初始化止损策略
        
        Args:
            fixed_stop: 固定止损比例 (默认-5%)
            trailing_stop: 移动止盈比例 (默认3%)
            max_hold_days: 最大持仓天数 (默认5天)
            atr_multiplier: ATR止损倍数 (默认2倍)
        """
        self.fixed_stop = fixed_stop
        self.trailing_stop = trailing_stop
        self.max_hold_days = max_hold_days
        self.atr_multiplier = atr_multiplier
    
    def check_stop(self, 
                   position: Dict, 
                   current_price: float,
                   current_atr: Optional[float] = None) -> Tuple[bool, str]:
        """
        检查是否触发止损
        
        Args:
            position: 持仓信息
                - buy_price: 买入价格
                - buy_date: 买入日期
                - max_price: 持仓期间最高价
            current_price: 当前价格
            current_atr: 当前ATR (可选)
        
        Returns:
            Tuple[bool, str]: (是否止损, 止损原因)
        """
        buy_price = position.get('buy_price', current_price)
        buy_date = position.get('buy_date', datetime.now())
        max_price = position.get('max_price', buy_price)
        
        # 更新最高价
        if current_price > max_price:
            position['max_price'] = current_price
            max_price = current_price
        
        # 1. 固定止损
        return_pct = (current_price / buy_price - 1)
        if return_pct < self.fixed_stop:
            logger.info(f"固定止损触发: {return_pct:.2%} < {self.fixed_stop:.2%}")
            return True, f'fixed_stop ({return_pct:.2%})'
        
        # 2. 移动止盈
        if max_price > buy_price:
            drawdown = (current_price / max_price - 1)
            if drawdown < -self.trailing_stop:
                logger.info(f"移动止盈触发: 从最高点回落 {drawdown:.2%}")
                return True, f'trailing_stop (drawdown: {drawdown:.2%})'
        
        # 3. 时间止损
        if isinstance(buy_date, str):
            buy_date = datetime.fromisoformat(buy_date)
        hold_days = (datetime.now() - buy_date).days
        if hold_days > self.max_hold_days:
            logger.info(f"时间止损触发: 持仓 {hold_days} 天")
            return True, f'time_stop ({hold_days} days)'
        
        # 4. ATR止损
        if current_atr is not None:
            atr_stop = buy_price - self.atr_multiplier * current_atr
            if current_price < atr_stop:
                logger.info(f"ATR止损触发: 价格 {current_price} < ATR止损线 {atr_stop:.2f}")
                return True, f'atr_stop (price < {atr_stop:.2f})'
        
        return False, None
    
    def calculate_stop_price(self, 
                             buy_price: float,
                             atr: Optional[float] = None) -> Dict[str, float]:
        """
        计算止损价格
        
        Args:
            buy_price: 买入价格
            atr: ATR值 (可选)
        
        Returns:
            Dict: 各种止损价格
        """
        stop_prices = {
            'fixed_stop': buy_price * (1 + self.fixed_stop),
            'trailing_stop': None,  # 动态计算
            'time_stop': None,  # 不适用
        }
        
        if atr is not None:
            stop_prices['atr_stop'] = buy_price - self.atr_multiplier * atr
        
        return stop_prices


class PositionManager:
    """
    持仓管理器
    
    管理多个持仓的止损状态
    """
    
    def __init__(self, stop_loss_strategy: StopLossStrategy):
        self.stop_loss = stop_loss_strategy
        self.positions = {}  # code -> position
    
    def add_position(self, 
                     code: str, 
                     name: str,
                     buy_price: float,
                     shares: int,
                     buy_date: Optional[datetime] = None):
        """添加持仓"""
        self.positions[code] = {
            'code': code,
            'name': name,
            'buy_price': buy_price,
            'shares': shares,
            'buy_date': buy_date or datetime.now(),
            'max_price': buy_price,
            'status': 'holding'
        }
        logger.info(f"添加持仓: {code} {name} @ {buy_price:.2f} x {shares}")
    
    def update_position(self, code: str, current_price: float, atr: Optional[float] = None):
        """更新持仓状态"""
        if code not in self.positions:
            return
        
        position = self.positions[code]
        
        # 更新最高价
        if current_price > position['max_price']:
            position['max_price'] = current_price
        
        # 检查止损
        should_stop, reason = self.stop_loss.check_stop(position, current_price, atr)
        
        if should_stop:
            position['status'] = 'stop_triggered'
            position['stop_reason'] = reason
            position['stop_price'] = current_price
            logger.info(f"止损触发: {code} {reason}")
    
    def get_positions_to_sell(self) -> list:
        """获取需要卖出的持仓"""
        return [
            pos for pos in self.positions.values()
            if pos['status'] == 'stop_triggered'
        ]
    
    def remove_position(self, code: str):
        """移除持仓"""
        if code in self.positions:
            del self.positions[code]
            logger.info(f"移除持仓: {code}")


# 测试
if __name__ == '__main__':
    # 创建止损策略
    stop_loss = StopLossStrategy(
        fixed_stop=-0.05,
        trailing_stop=0.03,
        max_hold_days=5
    )
    
    # 创建持仓管理器
    manager = PositionManager(stop_loss)
    
    # 添加持仓
    manager.add_position('000001', '平安银行', 10.0, 1000)
    
    # 模拟价格变化
    prices = [10.0, 10.5, 11.0, 10.8, 10.6, 10.3, 9.8]  # 最后触发止损
    
    for i, price in enumerate(prices):
        print(f"\nDay {i+1}: Price = {price}")
        manager.update_position('000001', price)
        
        position = manager.positions['000001']
        print(f"  Max Price: {position['max_price']:.2f}")
        print(f"  Status: {position['status']}")
        
        if position['status'] == 'stop_triggered':
            print(f"  Stop Reason: {position['stop_reason']}")
            break
