# -*- coding: utf-8 -*-
"""
最终优化 - 基于历史最佳策略
目标: 突破50%达标率
"""
import sqlite3
import pandas as pd
import numpy as np
import json

DB_PATH = 'data/stocks.db'

def calc_macd(closes):
    """计算MACD"""
    if len(closes) < 30:
        return None
    ema12 = closes.ewm(span=12).mean()
    ema26 = closes.ewm(span=26).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9).mean()
    macd = (dif - dea) * 2
    return {'dif': dif.iloc[-1], 'dea': dea.iloc[-1], 'macd': macd.iloc[-1]}

def backtest_macd(codes, holding, chg_min, chg_max, price_max, macd_require=True):
    """MACD策略回测"""
    trades = []
    conn = sqlite3.connect(DB_PATH)
    
    for code in codes:
        df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
        if df.empty or len(df) < 60:
            continue
        
        for i in range(30, len(df) - holding):
            row = df.iloc[i]
            prev = df.iloc[i-1]
            chg = (row['close'] - prev['close']) / prev['close'] * 100 if prev['close'] > 0 else 0
            
            if not (chg_min <= chg <= chg_max):
                continue
            if row['close'] > price_max:
                continue
            
            # MACD筛选
            if macd_require:
                macd = calc_macd(df.iloc[:i+1]['close'])
                if macd is None or macd['macd'] <= 0:
                    continue
            
            buy = row['close']
            sell = df.iloc[i + holding]['close']
            pnl = (sell - buy) / buy * 100
            
            # 计算最大涨幅
            max_price = df.iloc[i+1:i+holding+1]['close'].max()
            max_pnl = (max_price - buy) / buy * 100
            
            trades.append({
                'code': code,
                'buy_date': row['date'],
                'buy_price': buy,
                'pnl': pnl,
                'max_pnl': max_pnl
            })
    
    conn.close()
    return trades

def main():
    print('='*60)
    print('最终优化 - 突破50%达标率')
    print('='*60)
    
    conn = sqlite3.connect(DB_PATH)
    codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
    conn.close()
    print('股票:', len(codes))
    
    results = []
    
    # 测试MACD策略
    params = [
        (21, 8, 15, 10, True),
        (21, 6, 12, 10, True),
        (28, 8, 15, 10, True),
        (30, 8, 15, 10, True),
        (21, 5, 10, 10, True),
        (21, 3, 8, 10, True),
        (14, 5, 10, 10, True),
        (21, 8, 15, 15, True),
        (21, 8, 15, 10, False),  # 无MACD对比
        (28, 5, 15, 10, True),
        (30, 5, 15, 10, True),
        (14, 8, 15, 10, True),
    ]
    
    for holding, chg_min, chg_max, price_max, macd_req in params:
        trades = backtest_macd(codes, holding, chg_min, chg_max, price_max, macd_req)
        
        if trades:
            pnls = [t['pnl'] for t in trades]
            max_pnls = [t['max_pnl'] for t in trades]
            wins = sum(1 for p in pnls if p > 0)
            
            r30 = sum(1 for p in pnls if p >= 30) / len(pnls) * 100
            r20 = sum(1 for p in pnls if p >= 20) / len(pnls) * 100
            r30_max = sum(1 for p in max_pnls if p >= 30) / len(max_pnls) * 100
            
            filter_name = '+MACD' if macd_req else '无'
            results.append({
                'holding': holding,
                'chg': str(chg_min) + '-' + str(chg_max),
                'price_max': price_max,
                'filter': filter_name,
                'n': len(trades),
                'r30': r30,
                'r30_max': r30_max,
                'r20': r20,
                'win': wins / len(pnls) * 100,
                'avg': np.mean(pnls),
                'max': max(pnls)
            })
            
            print('持有' + str(holding) + '天 ' + str(chg_min) + '-' + str(chg_max) + '% <=' + str(price_max) + '元 ' + filter_name + ': ' + str(len(trades)) + '笔 胜率' + str(round(wins/len(pnls)*100, 1)) + '% 30%达标=' + str(round(r30, 1)) + '% 最高=' + str(round(max(pnls), 1)) + '%')
    
    results.sort(key=lambda x: x['r30_max'], reverse=True)
    
    print()
    print('='*60)
    print('TOP 5 最佳策略（按持有期最高收益计）')
    print('='*60)
    for i, r in enumerate(results[:5], 1):
        print(str(i) + '. 持有' + str(r['holding']) + '天 ' + r['chg'] + '% <=' + str(r['price_max']) + '元 ' + r['filter'])
        print('   交易' + str(r['n']) + '笔 胜率' + str(round(r['win'], 1)) + '%')
        print('   最终30%达标=' + str(round(r['r30'], 1)) + '% 最高30%达标=' + str(round(r['r30_max'], 1)) + '%')
        print('   平均收益=' + str(round(r['avg'], 1)) + '% 最高=' + str(round(r['max'], 1)) + '%')
    
    with open('data/best_strategy.json', 'w') as f:
        json.dump(results[:10], f, ensure_ascii=False, indent=2)
    
    print()
    print('最佳策略已保存!')

main()
