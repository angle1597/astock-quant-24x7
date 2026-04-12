# -*- coding: utf-8 -*-
"""
回测验证系统 v3 - 简化版
"""
import os
import sys
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List

# 设置编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class BacktestSimulator:
    """回测模拟器"""
    
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.trades = []
    
    def buy(self, code, name, price):
        value = self.cash * 0.1
        shares = int(value / price)
        if shares > 0:
            self.cash -= shares * price
            self.positions[code] = {'name': name, 'shares': shares, 'buy_price': price}
            self.trades.append({'action': 'BUY', 'code': code, 'price': price})
            return True
        return False
    
    def sell(self, code, price, reason):
        if code not in self.positions:
            return 0
        pos = self.positions[code]
        profit = (price - pos['buy_price']) / pos['buy_price']
        self.cash += pos['shares'] * price
        self.trades.append({'action': 'SELL', 'code': code, 'price': price, 'profit': profit, 'reason': reason})
        del self.positions[code]
        return profit
    
    def run(self, picks, days=30):
        print(f"\n[回测] 初始资金: {self.initial_capital:,.0f}元")
        
        current_date = datetime.strptime('2026-04-09', '%Y-%m-%d')
        
        for day in range(days):
            date_str = current_date.strftime('%Y-%m-%d')
            
            # 随机买入
            if random.random() < 0.3 and picks:
                available = [p for p in picks if p['code'] not in self.positions]
                if available:
                    stock = random.choice(available)
                    self.buy(stock['code'], stock['name'], stock['price'])
                    print(f"  [{date_str}] 买入: {stock['code']}")
            
            # 检查卖出
            for code in list(self.positions.keys()):
                pos = self.positions[code]
                change = random.uniform(-0.05, 0.10)
                price = pos['buy_price'] * (1 + change)
                profit = (price - pos['buy_price']) / pos['buy_price']
                
                if profit >= 0.10 or profit <= -0.05:
                    self.sell(code, price, 'stop' if profit < 0 else 'profit')
                    print(f"  [{date_str}] 卖出: {code} 收益: {profit:.1%}")
            
            current_date += timedelta(days=1)
        
        # 最终权益
        positions_value = sum(p['shares'] * p['buy_price'] for p in self.positions.values())
        final_equity = self.cash + positions_value
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # 统计
        sells = [t for t in self.trades if t['action'] == 'SELL']
        wins = len([t for t in sells if t.get('profit', 0) > 0])
        win_rate = wins / len(sells) * 100 if sells else 0
        qualified = len([t for t in sells if t.get('profit', 0) >= 0.30])
        qualified_rate = qualified / len(sells) * 100 if sells else 0
        
        print(f"\n[结果]")
        print(f"  最终权益: {final_equity:,.0f}元")
        print(f"  总收益: {total_return:+.2%}")
        print(f"  交易次数: {len(sells)}")
        print(f"  胜率: {win_rate:.1f}%")
        print(f"  达标率(>=30%): {qualified_rate:.1f}%")
        
        # 保存
        result = {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return': total_return,
            'trade_count': len(sells),
            'win_rate': win_rate,
            'qualified_rate': qualified_rate
        }
        
        with open('data/backtest_sim_results.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return result


def main():
    # 加载选股结果
    try:
        with open('data/picks_2026-04-09.json', 'r', encoding='utf-8') as f:
            picks = json.load(f).get('picks', [])
    except:
        picks = []
    
    sim = BacktestSimulator(100000)
    sim.run(picks, 30)


if __name__ == '__main__':
    main()
