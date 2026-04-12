# -*- coding: utf-8 -*-
"""
历史回测验证 - 基于真实历史数据
"""
import os
import sys
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def get_historical_data(code: str, days: int = 60) -> List[Dict]:
    """获取历史K线数据"""
    try:
        # 东方财富K线接口
        secid = f'1.{code}' if code.startswith('0') or code.startswith('6') else f'0.{code}'
        url = f'https://push2his.eastmoney.com/api/qt/stock/kline/get'
        params = {
            'secid': secid,
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56',
            'klt': '101',  # 日K
            'fqt': '0',    # 不复权
            'end': '20500000',
            'lmt': str(days)
        }
        
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        
        if data.get('data') and data['data'].get('klines'):
            klines = data['data']['klines']
            result = []
            for kline in klines:
                parts = kline.split(',')
                result.append({
                    'date': parts[0],
                    'open': float(parts[1]),
                    'close': float(parts[2]),
                    'high': float(parts[3]),
                    'low': float(parts[4]),
                    'volume': float(parts[5]),
                })
            return result
    except Exception as e:
        print(f"获取 {code} 数据失败: {e}")
    return []


def backtest_strategy(code: str, name: str, entry_change: float, entry_price: float) -> Dict:
    """
    回测单只股票的策略
    
    Args:
        code: 股票代码
        name: 股票名称
        entry_change: 买入日涨幅 (假设买入后)
        entry_price: 买入价格
    
    Returns:
        回测结果
    """
    # 获取60天历史数据
    klines = get_historical_data(code, 60)
    
    if len(klines) < 20:
        return None
    
    # 模拟: 假设我们在历史某天买入
    # 简单回测: 买入后持有N天，看收益
    
    results = []
    
    # 从第20天开始，每天模拟一次"按涨幅买入"的场景
    for i in range(20, len(klines) - 5):
        buy_day = klines[i]
        buy_price = buy_day['close']  # 以收盘价买入
        
        # 买入条件: 当日涨幅符合筛选条件 (假设)
        if buy_day['close'] / buy_day['open'] - 1 < 0.02:  # 涨幅<2%跳过
            continue
        
        # 模拟止损/止盈
        stop_loss = buy_price * 0.95  # -5%
        take_profit = buy_price * 1.10  # +10%
        
        sold = False
        hold_days = 0
        exit_price = None
        exit_reason = None
        
        for j in range(i + 1, min(i + 6, len(klines))):
            day = klines[j]
            high = day['high']
            low = day['low']
            close = day['close']
            hold_days += 1
            
            # 检查止损
            if low <= stop_loss:
                exit_price = stop_loss
                exit_reason = 'stop_loss'
                sold = True
                break
            
            # 检查止盈
            if high >= take_profit:
                exit_price = take_profit
                exit_reason = 'take_profit'
                sold = True
                break
            
            # 时间止损 (5天)
            if hold_days >= 5:
                exit_price = close
                exit_reason = 'time_stop'
                sold = True
                break
        
        if not sold and i + 5 < len(klines):
            # 最后一天强制卖出
            exit_price = klines[i + 5]['close']
            exit_reason = 'force_sell'
            hold_days = 5
        
        if exit_price:
            profit_pct = (exit_price - buy_price) / buy_price * 100
            results.append({
                'date': buy_day['date'],
                'buy_price': buy_price,
                'exit_price': exit_price,
                'profit_pct': profit_pct,
                'hold_days': hold_days,
                'reason': exit_reason
            })
    
    return {
        'code': code,
        'name': name,
        'total_trades': len(results),
        'results': results
    }


def calculate_stats(results: List[Dict]) -> Dict:
    """计算统计数据"""
    if not results:
        return {
            'total_trades': 0,
            'win_rate': 0,
            'avg_profit': 0,
            'qualified_rate': 0,
            'total_profit': 0
        }
    
    total = len(results)
    wins = len([r for r in results if r['profit_pct'] > 0])
    qualified = len([r for r in results if r['profit_pct'] >= 30])  # 达标30%+
    
    profits = [r['profit_pct'] for r in results]
    
    return {
        'total_trades': total,
        'win_rate': wins / total * 100 if total > 0 else 0,
        'avg_profit': sum(profits) / len(profits) if profits else 0,
        'qualified_rate': qualified / total * 100 if total > 0 else 0,
        'total_profit': sum(profits),
        'max_profit': max(profits) if profits else 0,
        'max_loss': min(profits) if profits else 0
    }


def main():
    print("\n" + "="*60)
    print("【历史回测验证】")
    print("="*60)
    
    # 今日选股
    picks = [
        {'code': '600749', 'name': '西藏旅游'},
        {'code': '603123', 'name': '翠微股份'},
        {'code': '600590', 'name': '泰豪科技'},
        {'code': '002083', 'name': '孚日股份'},
        {'code': '002104', 'name': '恒宝股份'},
    ]
    
    print(f"\n回测 {len(picks)} 只股票...")
    
    all_stats = []
    
    for pick in picks:
        print(f"\n回测: {pick['code']} {pick['name']}")
        
        result = backtest_strategy(pick['code'], pick['name'], 5, 0)
        
        if result and result['total_trades'] > 0:
            stats = calculate_stats(result['results'])
            stats['code'] = pick['code']
            stats['name'] = pick['name']
            all_stats.append(stats)
            
            print(f"  交易次数: {stats['total_trades']}")
            print(f"  胜率: {stats['win_rate']:.1f}%")
            print(f"  平均收益: {stats['avg_profit']:+.2f}%")
            print(f"  达标率(30%+): {stats['qualified_rate']:.1f}%")
        else:
            print(f"  数据不足")
    
    # 汇总
    print("\n" + "="*60)
    print("【汇总统计】")
    print("="*60)
    
    if all_stats:
        total_trades = sum(s['total_trades'] for s in all_stats)
        total_wins = sum(s['win_rate'] * s['total_trades'] / 100 for s in all_stats)
        total_profit = sum(s['avg_profit'] * s['total_trades'] for s in all_stats)
        
        print(f"\n| 股票 | 交易次数 | 胜率 | 平均收益 | 达标率 |")
        print("|:---:|:---:|:---:|:---:|:---:|")
        for s in all_stats:
            print(f"| {s['code']} | {s['total_trades']} | {s['win_rate']:.1f}% | {s['avg_profit']:+.2f}% | {s['qualified_rate']:.1f}% |")
        
        print(f"\n总交易: {total_trades}次")
        print(f"综合胜率: {total_wins / total_trades * 100:.1f}%" if total_trades > 0 else "无交易")
        print(f"综合平均收益: {total_profit / total_trades:+.2f}%" if total_trades > 0 else "无交易")
    else:
        print("\n暂无有效回测数据")
    
    # 保存
    date_str = datetime.now().strftime('%Y-%m-%d')
    output = {
        'date': date_str,
        'picks': picks,
        'stats': all_stats
    }
    
    with open(f'data/backtest_history_{date_str}.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存: data/backtest_history_{date_str}.json")


if __name__ == '__main__':
    main()
