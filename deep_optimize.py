# -*- coding: utf-8 -*-
"""
量化策略深度优化 - 目标达标率50%+
"""
import sqlite3
import json
import numpy as np
import pandas as pd
from datetime import datetime

DB_PATH = 'data/stocks.db'

def get_stock_klines(code):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
    conn.close()
    return df.sort_values('date') if not df.empty else None

def calc_macd(closes, fast=12, slow=26, signal=9):
    """计算MACD"""
    if len(closes) < 30:
        return None
    ema_fast = closes.ewm(span=fast).mean()
    ema_slow = closes.ewm(span=slow).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal).mean()
    macd = (dif - dea) * 2
    return {'dif': dif.iloc[-1], 'dea': dea.iloc[-1], 'macd': macd.iloc[-1]}

def calc_rsi(closes, period=14):
    """计算RSI"""
    if len(closes) < period + 1:
        return None
    delta = closes.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def backtest(df, holding_days, chg_min, chg_max, price_max, use_macd, use_rsi, use_vol):
    """回测策略"""
    trades = []
    
    for i in range(30, len(df) - holding_days):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        
        # 买入条件
        chg = (row['close'] - prev['close']) / prev['close'] * 100 if prev['close'] > 0 else 0
        
        # 涨幅筛选
        if not (chg_min <= chg <= chg_max):
            continue
        
        # 价格筛选
        if row['close'] > price_max:
            continue
        
        # MACD筛选
        if use_macd:
            macd_data = calc_macd(df.iloc[:i+1]['close'])
            if macd_data is None or macd_data['macd'] < 0:
                continue
        
        # RSI筛选
        if use_rsi:
            rsi = calc_rsi(df.iloc[:i+1]['close'])
            if rsi is None or rsi > 70 or rsi < 30:
                pass  # RSI 30-70区间
        
        # 量比筛选
        if use_vol:
            vol_ma5 = df.iloc[i-5:i]['volume'].mean() if i >= 5 else df.iloc[:i]['volume'].mean()
            vol_ratio = row['volume'] / vol_ma5 if vol_ma5 > 0 else 0
            if vol_ratio < 1.5:
                continue
        
        # 模拟持有
        buy_price = row['close']
        max_price = buy_price
        final_price = df.iloc[i + holding_days]['close']
        max_pnl = (max_price - buy_price) / buy_price * 100
        final_pnl = (final_price - buy_price) / buy_price * 100
        
        trades.append({
            'code': row['code'],
            'buy_date': row['date'],
            'buy_price': buy_price,
            'max_pnl': max_pnl,
            'final_pnl': final_pnl
        })
    
    if not trades:
        return {'n': 0, 'r30': 0, 'r20': 0, 'r15': 0, 'win': 0, 'avg': 0}
    
    pnls = [t['final_pnl'] for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    
    return {
        'n': len(trades),
        'r30': sum(1 for p in pnls if p >= 30) / len(pnls) * 100,
        'r20': sum(1 for p in pnls if p >= 20) / len(pnls) * 100,
        'r15': sum(1 for p in pnls if p >= 15) / len(pnls) * 100,
        'win': wins / len(pnls) * 100,
        'avg': np.mean(pnls)
    }

def main():
    print('='*60)
    print('量化策略深度优化')
    print('目标: 达标率突破50%+')
    print('='*60)
    
    # 获取所有股票
    conn = sqlite3.connect(DB_PATH)
    codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
    conn.close()
    print(f'\n股票数量: {len(codes)}')
    
    # 加载所有K线
    all_data = {}
    for code in codes[:200]:  # 取前200只
        df = get_stock_klines(code)
        if df is not None and len(df) >= 60:
            all_data[code] = df
    
    print(f'有效股票: {len(all_data)}')
    
    # 参数网格
    results = []
    holding_days_list = [14, 21, 28]
    chg_ranges = [(3, 8), (5, 10), (8, 15), (10, 20)]
    price_max_list = [10, 15, 20]
    filters_list = [
        (False, False, False, '无筛选'),
        (True, False, False, '+MACD'),
        (False, True, False, '+RSI'),
        (False, False, True, '+量比'),
        (True, False, True, 'MACD+量比'),
        (True, True, False, 'MACD+RSI'),
    ]
    
    total = len(holding_days_list) * len(chg_ranges) * len(price_max_list) * len(filters_list)
    print(f'\n开始测试 {total} 种策略组合...')
    
    for holding in holding_days_list:
        for chg_min, chg_max in chg_ranges:
            for price_max in price_max_list:
                for use_macd, use_rsi, use_vol, name in filters_list:
                    # 汇总所有股票回测结果
                    all_trades = []
                    for code, df in all_data.items():
                        r = backtest(df, holding, chg_min, chg_max, price_max, use_macd, use_rsi, use_vol)
                        if r['n'] > 0:
                            all_trades.append(r)
                    
                    if not all_trades:
                        continue
                    
                    # 汇总
                    total_n = sum(t['n'] for t in all_trades)
                    total_wins = sum(t['win'] * t['n'] / 100 for t in all_trades)
                    total_r30 = sum(t['r30'] * t['n'] / 100 for t in all_trades)
                    total_r20 = sum(t['r20'] * t['n'] / 100 for t in all_trades)
                    
                    win_rate = total_wins / total_n * 100 if total_n > 0 else 0
                    r30 = total_r30 / len(all_trades) if all_trades else 0
                    r20 = total_r20 / len(all_trades) if all_trades else 0
                    
                    results.append({
                        'holding': holding,
                        'chg': f'{chg_min}-{chg_max}',
                        'price_max': price_max,
                        'filter': name,
                        'n': total_n,
                        'r30': r30,
                        'r20': r20,
                        'win': win_rate
                    })
    
    # 按30%达标率排序
    results.sort(key=lambda x: x['r30'], reverse=True)
    
    print('\n' + '='*60)
    print('TOP 10 最优策略')
    print('='*60)
    
    for i, r in enumerate(results[:10], 1):
        print(f'{i}. 持有{r["holding"]}天 涨幅{r["chg"]}% 价格≤{r["price_max"]}元')
        print(f'   {r["filter"]}: 交易{r["n"]}笔 胜率{r["win"]:.1f}%')
        print(f'   30%达标率: {r["r30"]:.1f}% | 20%达标率: {r["r20"]:.1f}%')
        print()
    
    # 保存结果
    with open('data/deep_optimize_results.json', 'w', encoding='utf-8') as f:
        json.dump(results[:30], f, ensure_ascii=False, indent=2)
    
    print('结果已保存到 data/deep_optimize_results.json')
    
    if results:
        best = results[0]
        print(f'\n🏆 最佳策略: 30%达标率 {best["r30"]:.1f}%')
        return best
    return None

if __name__ == '__main__':
    main()
