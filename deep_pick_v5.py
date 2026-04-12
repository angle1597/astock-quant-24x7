# -*- coding: utf-8 -*-
"""
深度优化选股 v5 - 放宽筛选条件 + 止损机制 + 市场过滤
"""
import requests
import json
import sys
import os
from datetime import datetime

# 设置输出编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 导入优化模块
sys.path.insert(0, os.path.dirname(__file__))
from stop_loss import StopLossStrategy
from market_filter import MarketEnvironment

def get_main_board():
    """获取主板A股数据"""
    # 上证A股
    url1 = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:1+t:2,m:1+t:23&fields=f12,f14,f2,f3,f5,f6,f8,f20,f23,f24'
    # 深证A股
    url2 = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80&fields=f12,f14,f2,f3,f5,f6,f8,f20,f23,f24'

    headers = {'User-Agent': 'Mozilla/5.0'}

    all_stocks = []

    for url in [url1, url2]:
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            data = resp.json()
            all_stocks.extend(data['data']['diff'])
        except:
            pass

    return all_stocks

def screen_stocks(stocks, relaxed=False):
    """
    筛选股票
    
    Args:
        stocks: 股票列表
        relaxed: 是否放宽条件
    
    Returns:
        list: 筛选后的股票
    """
    candidates = []
    
    for s in stocks:
        code = s['f12']
        name = s['f14']

        # 排除科创板、创业板、北交所
        if code.startswith('688') or code.startswith('300') or code.startswith('8') or code.startswith('4'):
            continue
        if 'ST' in name or '退' in name or name.startswith('N'):
            continue

        try:
            price = float(s['f2']) if s['f2'] != '-' else 0
            chg = float(s['f3']) if s['f3'] != '-' else 0
            volume = float(s['f5']) if s['f5'] != '-' else 0
            mv = float(s['f20']) / 1e8 if s['f20'] != '-' else 0
            pe = float(s['f23']) if s['f23'] != '-' else 0
            turnover = float(s['f8']) if s['f8'] != '-' else 0
            chg_5d = float(s['f24']) if s['f24'] != '-' else 0
            amount = float(s['f6']) / 1e8 if s['f6'] != '-' else 0  # 成交额(亿)
        except:
            continue

        # 筛选条件 (放宽版)
        if relaxed:
            # 放宽价格限制
            if price <= 2 or price > 50:
                continue
            # 放宽市值限制
            if mv < 20 or mv > 200:
                continue
            # 放宽涨幅限制
            if chg < -3 or chg > 10:
                continue
            # 增加量比要求
            if turnover < 2:
                continue
        else:
            # 原始条件
            if price <= 2 or price > 25:
                continue
            if chg <= 0 or chg > 10:
                continue
            if mv < 30 or mv > 150:
                continue

        # 评分
        score = 0

        # 涨幅 (30分)
        if 4 <= chg <= 8:
            score += 30
        elif 2 <= chg <= 9:
            score += 20
        elif chg > 0:
            score += 10
        else:
            # 负涨幅但跌幅不大 (抄底机会)
            if chg > -3:
                score += 5

        # 量比 (30分)
        if turnover >= 8:
            score += 30
        elif turnover >= 5:
            score += 25
        elif turnover >= 3:
            score += 20
        elif turnover >= 2:
            score += 15
        else:
            score += 5

        # 换手率 (20分)
        if 3 <= turnover <= 10:
            score += 20
        elif 2 <= turnover <= 15:
            score += 15
        else:
            score += 5

        # 市盈率 (20分)
        if 0 < pe <= 20:
            score += 20
        elif 0 < pe <= 40:
            score += 15
        elif pe > 0:
            score += 5
        else:
            score += 10  # 亏损股也给机会

        # 额外加分项
        # 5日涨幅为负 (超跌反弹机会)
        if chg_5d < -5:
            score += 10
        
        # 成交额大 (关注度高)
        if amount > 5:
            score += 5

        candidates.append({
            'code': code,
            'name': name,
            'price': price,
            'change_pct': chg,
            'volume': volume,
            'amount': amount,
            'market_cap': mv,
            'pe': pe,
            'turnover': turnover,
            'change_5d': chg_5d,
            'score': score
        })

    # 按评分排序
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    return candidates

def main():
    print('='*60)
    print('【深度优化选股 v5】放宽条件 + 止损 + 市场过滤')
    print('='*60)
    print('')
    
    # 1. 市场环境判断
    print('1. 检查市场环境...')
    market = MarketEnvironment()
    is_good, reason = market.is_good_market()
    print(f'   结果: {"✅" if is_good else "❌"} {reason}')
    
    if not is_good:
        print('\n⚠️ 市场环境不佳，建议观望')
        # 仍然继续，但给出警告
    
    # 2. 获取股票数据
    print('\n2. 扫描主板A股...')
    stocks = get_main_board()
    print(f'   扫描: {len(stocks)}只')
    
    # 3. 筛选 (放宽条件)
    print('\n3. 筛选股票 (放宽条件)...')
    candidates = screen_stocks(stocks, relaxed=True)
    print(f'   符合条件: {len(candidates)}只')
    
    if not candidates:
        print('\n无符合条件的股票')
        return
    
    # 4. 输出TOP10
    print('\n' + '='*60)
    print('【TOP 10 选股结果】')
    print('='*60)
    print('')
    print('| 排名 | 代码 | 名称 | 现价 | 涨幅 | 市值 | 换手 | 评分 |')
    print('|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|')
    
    for i, s in enumerate(candidates[:10], 1):
        print(f"| {i} | {s['code']} | {s['name']} | {s['price']:.2f} | {s['change_pct']:+.2f}% | {s['market_cap']:.1f}亿 | {s['turnover']:.1f}% | {s['score']} |")
    
    # 5. 止损建议
    print('\n' + '='*60)
    print('【止损建议】')
    print('='*60)
    print('')
    stop_loss = StopLossStrategy()
    
    for s in candidates[:3]:
        stop_prices = stop_loss.calculate_stop_price(s['price'])
        print(f"{s['code']} {s['name']}:")
        print(f"  买入价: {s['price']:.2f}")
        print(f"  固定止损: {stop_prices['fixed_stop']:.2f} ({stop_loss.fixed_stop:.0%})")
        print(f"  移动止盈: 从最高点回落 {stop_loss.trailing_stop:.0%}")
        print(f"  时间止损: 持仓超过 {stop_loss.max_hold_days} 天")
        print('')
    
    # 6. 保存结果
    date_str = datetime.now().strftime('%Y-%m-%d')
    output_file = f'data/picks_{date_str}.json'
    
    import json
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'date': date_str,
            'market_status': {'is_good': is_good, 'reason': reason},
            'picks': candidates[:10]
        }, f, ensure_ascii=False, indent=2)
    
    print(f'结果已保存: {output_file}')

if __name__ == '__main__':
    main()
