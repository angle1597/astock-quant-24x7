# -*- coding: utf-8 -*-
"""
回测验证系统 v3 - 模拟真实交易
"""
import os
import sys
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# 设置编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class BacktestSimulator:
    """回测模拟器 - 模拟真实交易场景"""
    
    def __init__(self, 
                 initial_capital: float = 100000,
                 position_size: float = 0.1,  # 10%仓位
                 stop_loss: float = -0.05,
                 take_profit: float = 0.10,
                 max_hold_days: int = 5):
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.max_hold_days = max_hold_days
        
        # 持仓状态
        self.cash = initial_capital
        self.positions = {}  # code -> {'shares': int, 'buy_price': float, 'buy_date': str}
        self.trades = []  # 交易记录
        self.equity_curve = []  # 权益曲线
    
    def simulate_buy(self, code: str, name: str, price: float, date: str) -> bool:
        """模拟买入"""
        # 检查资金
        position_value = self.cash * self.position_size
        shares = int(position_value / price)
        
        if shares <= 0:
            return False
        
        cost = shares * price
        if cost > self.cash:
            return False
        
        # 执行买入
        self.cash -= cost
        self.positions[code] = {
            'name': name,
            'shares': shares,
            'buy_price': price,
            'buy_date': date,
            'buy_value': cost
        }
        
        self.trades.append({
            'date': date,
            'action': 'BUY',
            'code': code,
            'name': name,
            'price': price,
            'shares': shares,
            'value': cost
        })
        
        return True
    
    def simulate_sell(self, code: str, price: float, date: str, reason: str) -> float:
        """模拟卖出"""
        if code not in self.positions:
            return 0
        
        position = self.positions[code]
        shares = position['shares']
        
        # 计算收益
        sell_value = shares * price
        profit = (price - position['buy_price']) / position['buy_price']
        
        # 记录卖出
        self.trades.append({
            'date': date,
            'action': 'SELL',
            'code': code,
            'name': position['name'],
            'price': price,
            'shares': shares,
            'value': sell_value,
            'profit_pct': profit * 100,
            'reason': reason
        })
        
        # 更新资金
        self.cash += sell_value
        
        # 移除持仓
        del self.positions[code]
        
        return profit
    
    def check_positions(self, stock_prices: Dict[str, float], date: str) -> List[Tuple[str, str]]:
        """检查持仓是否触发卖出条件"""
        to_sell = []
        
        for code, position in self.positions.items():
            if code not in stock_prices:
                continue
            
            current_price = stock_prices[code]
            buy_price = position['buy_price']
            buy_date = position['buy_date']
            
            # 计算收益率
            profit_pct = (current_price - buy_price) / buy_price
            
            # 1. 止盈触发
            if profit_pct >= self.take_profit:
                to_sell.append((code, f"take_profit ({profit_pct:.1%})"))
                continue
            
            # 2. 止损触发
            if profit_pct <= self.stop_loss:
                to_sell.append((code, f"stop_loss ({profit_pct:.1%})"))
                continue
            
            # 3. 时间止损
            try:
                buy_dt = datetime.strptime(buy_date, '%Y-%m-%d')
                hold_days = (datetime.strptime(date, '%Y-%m-%d') - buy_dt).days
                if hold_days >= self.max_hold_days:
                    to_sell.append((code, f"time_stop ({hold_days} days)"))
            except:
                pass
        
        return to_sell
    
    def get_equity(self) -> float:
        """获取当前权益"""
        positions_value = sum(
            pos['shares'] * pos['buy_price'] 
            for pos in self.positions.values()
        )
        return self.cash + positions_value
    
    def run_backtest(self, 
                    picks: List[Dict], 
                    start_date: str, 
                    days: int = 30) -> Dict:
        """
        运行回测
        
        Args:
            picks: 选股结果列表
            start_date: 开始日期
            days: 回测天数
        
        Returns:
            Dict: 回测结果
        """
        print("\n" + "="*60)
        print(f"【回测模拟】初始资金: {self.initial_capital:,.0f}元")
        print("="*60)
        
        # 模拟每日行情 (简化版: 随机波动)
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        
        for day in range(days):
            date_str = current_date.strftime('%Y-%m-%d')
            
            # 1. 买入信号: 每日选股结果中随机选一只买入
            if not picks or len(self.positions) >= 5:  # 最多5只持仓
                pass
            else:
                # 随机选一只未持仓的股票买入
                available = [p for p in picks if p['code'] not in self.positions]
                if available and random.random() < 0.3:  # 30%概率买入
                    stock = random.choice(available)
                    self.simulate_buy(
                        stock['code'], 
                        stock['name'], 
                        stock['price'], 
                        date_str
                    )
                    print(f"  [{date_str}] 买入: {stock['code']} {stock['name']} @ {stock['price']:.2f}")
            
            # 2. 检查卖出条件
            if self.positions:
                # 模拟当前价格 (买入价 ± 随机波动)
                stock_prices = {}
                for code, pos in self.positions.items():
                    # 随机波动 -5% ~ +10%
                    change = random.uniform(-0.05, 0.10)
                    stock_prices[code] = pos['buy_price'] * (1 + change)
                
                # 检查卖出
                to_sell = self.check_positions(stock_prices, date_str)
                
                for code, reason in to_sell:
                    price = stock_prices[code]
                    profit = self.simulate_sell(code, price, date_str, reason)
                    pos = self.positions[code]  # 这是卖出后的引用，会被删除
                    print(f"  [{date_str}] 卖出: {code} @{price:.2f} 原因:{reason} 收益:{profit:.1%}")
            
            # 3. 记录权益
            self.equity_curve.append({
                'date': date_str,
                'equity': self.get_equity()
            })
            
            # 下一天
            current_date += timedelta(days=1)
        
        # 回测结束
        final_equity = self.get_equity()
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # 统计
        buy_count = len([t for t in self.trades if t['action'] == 'BUY'])
        sell_trades = [t for t in self.trades if t['action'] == 'SELL']
        sell_count = len(sell_trades)
        
        winning_trades = [t for t in sell_trades if t.get('profit_pct', 0) > 0]
        losing_trades = [t for t in sell_trades if t.get('profit_pct', 0) <= 0]
        
        win_rate = len(winning_trades) / sell_count * 100 if sell_count > 0 else 0
        
        avg_profit = sum(t.get('profit_pct', 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t.get('profit_pct', 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        # 达标统计 (>=30%)
        qualified_trades = [t for t in sell_trades if t.get('profit_pct', 0) >= 30]
        qualified_rate = len(qualified_trades) / sell_count * 100 if sell_count > 0 else 0
        
        print("\n" + "="*60)
        print("【回测结果】")
        print("="*60)
        print(f"回测期间: {start_date} ~ {current_date.strftime('%Y-%m-%d')}")
        print(f"初始资金: {self.initial_capital:,.0f}元")
        print(f"最终权益: {final_equity:,.0f}元")
        print(f"总收益: {total_return:+.2%}")
        print(f"\n交易统计:")
        print(f"  买入次数: {buy_count}")
        print(f"  卖出次数: {sell_count}")
        print(f"  胜率: {win_rate:.1f}%")
        print(f"  达标率(>=30%): {qualified_rate:.1f}%")
        print(f"  平均盈利: {avg_profit:+.2f}%")
        print(f"  平均亏损: {avg_loss:.2f}%")
        
        # 保存结果
        result = {
            'start_date': start_date,
            'end_date': current_date.strftime('%Y-%m-%d'),
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return': total_return,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'win_rate': win_rate,
            'qualified_rate': qualified_rate,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
        
        with open('data/backtest_sim_results.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n结果已保存: data/backtest_sim_results.json")
        
        return result


def main():
    """主函数"""
    # 加载选股结果
    try:
        with open('data/picks_2026-04-09.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            picks = data.get('picks', [])
    except:
        # 测试数据
        picks = [
            {'code': '000823', 'name': '超声电子', 'price': 14.58},
            {'code': '002906', 'name': '华阳集团', 'price': 30.10},
            {'code': '603158', 'name': '腾龙股份', 'price': 13.06},
        ]
    
    # 创建模拟器
    simulator = BacktestSimulator(
        initial_capital=100000,
        position_size=0.1,  # 10%仓位
        stop_loss=-0.05,   # -5%止损
        take_profit=0.10,  # 10%止盈
        max_hold_days=5    # 5天强制平仓
    )
    
    # 运行回测
    result = simulator.run_backtest(
        picks=picks,
        start_date='2026-04-09',
        days=30
    )


if __name__ == '__main__':
    main()

