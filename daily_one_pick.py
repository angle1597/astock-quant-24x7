# -*- coding: utf-8 -*-
"""
每日精选一股策略
目标：周涨幅30%+
"""
import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime

def main():
    bs.login()
    
    # 获取全市场主板股票
    print('正在扫描全市场...')
    rs = bs.query_all_stock(day='2026-04-08')
    all_stocks = []
    while rs.error_code == '0' and rs.next():
        row = rs.get_row_data()
        code = row[0]
        name = row[1]
        if code.startswith('sh.6') or code.startswith('sz.00') or code.startswith('sz.002'):
            if 'ST' not in name and '退' not in name:
                all_stocks.append((code, name))
    
    print(f'主板股票总数: {len(all_stocks)}')
    
    # 筛选
    candidates = []
    
    for idx, (code, name) in enumerate(all_stocks[:500]):  # 扫描500只
        if idx % 100 == 0:
            print(f'扫描进度: {idx}/{min(500, len(all_stocks))}')
        
        try:
            rs = bs.query_history_k_data_plus(
                code, 'date,close,pctChg,volume,turn',
                start_date='2026-03-01', end_date='2026-04-08',
                frequency='d', adjustflag='2'
            )
            rows = []
            while rs.error_code == '0' and rs.next():
                rows.append(rs.get_row_data())
            
            if len(rows) < 25:
                continue
            
            df = pd.DataFrame(rows, columns=['date','close','pctChg','volume','turn'])
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['pctChg'] = pd.to_numeric(df['pctChg'], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            
            latest = df.iloc[-1]
            price = latest['close']
            chg = latest['pctChg']
            vol = latest['volume']
            
            # 基本筛选
            if price <= 2 or price > 25:
                continue
            if chg < 3 or chg > 9.5:
                continue
            
            closes = df['close'].tolist()
            volumes = df['volume'].tolist()
            
            ma5 = np.mean(closes[-5:])
            ma10 = np.mean(closes[-10:])
            ma20 = np.mean(closes[-20:])
            
            # 多头排列
            if not (ma5 > ma10 > ma20):
                continue
            
            # 放量
            avg_vol = np.mean(volumes[-20:-1])
            if avg_vol <= 0:
                continue
            vol_ratio = vol / avg_vol
            if vol_ratio < 1.5:
                continue
            
            # 过去5天涨幅不能太大
            chg_5d = (closes[-1] - closes[-5]) / closes[-5] * 100
            if chg_5d > 20:
                continue
            
            # 评分
            score = 0
            
            # 趋势强度 (35分)
            trend = (ma5 - ma20) / ma20 * 100
            if trend > 8:
                score += 35
            elif trend > 5:
                score += 30
            elif trend > 3:
                score += 20
            
            # 突破 (30分)
            high_20 = max(closes[-20:-1])
            if closes[-1] > high_20:
                score += 30
            elif closes[-1] > high_20 * 0.98:
                score += 20
            
            # 量能 (20分)
            if vol_ratio > 3:
                score += 20
            elif vol_ratio > 2:
                score += 15
            elif vol_ratio > 1.5:
                score += 10
            
            # 启动位置 (15分)
            low_20 = min(closes[-20:])
            high_range = max(closes[-20:]) - low_20
            if high_range > 0:
                position = (closes[-1] - low_20) / high_range
                if 0.4 < position < 0.8:
                    score += 15
                elif 0.3 < position < 0.9:
                    score += 10
            
            candidates.append({
                'code': code,
                'name': name,
                'price': round(price, 2),
                'chg': round(chg, 2),
                'score': score,
                'vol_ratio': round(vol_ratio, 2),
                'trend': round(trend, 2),
                'chg_5d': round(chg_5d, 2),
            })
            
        except Exception as e:
            pass
    
    bs.logout()
    
    # 排序
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    print('')
    print('='*60)
    print('【每日精选一股】')
    print('目标: 周涨幅30%+')
    print('='*60)
    print('')
    
    if candidates:
        best = candidates[0]
        print('唯一推荐:')
        print(f'  代码: {best["code"]}')
        print(f'  名称: {best["name"]}')
        print(f'  价格: {best["price"]}元')
        print(f'  今日涨幅: {best["chg"]}%')
        print(f'  5日涨幅: {best["chg_5d"]}%')
        print(f'  综合评分: {best["score"]}分')
        print(f'  量比: {best["vol_ratio"]}x')
        print(f'  趋势强度: {best["trend"]}%')
        print('')
        print('选股逻辑:')
        print('  1. 多头排列确认上涨趋势')
        print('  2. 放量突破或接近新高')
        print('  3. 涨幅适中避免追高')
        print('  4. 量价配合完美')
        print('')
        print('持仓建议: 持有5-7天')
        print('止损位: -5%')
        print('止盈位: +30%')
    else:
        print('今日无符合条件股票')
    
    print('')
    print(f'扫描: {min(500, len(all_stocks))}只')
    print(f'候选: {len(candidates)}只')

if __name__ == '__main__':
    main()
