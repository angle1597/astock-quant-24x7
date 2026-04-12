# -*- coding: utf-8 -*-
"""
深度优化选股策略 v2
- 加入更多技术指标
- 更严格的筛选条件
- 目标: 周涨幅30%+
"""
import requests
import json
import numpy as np

def get_realtime_data():
    """获取实时行情"""
    url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f12,f14,f2,f3,f5,f6,f8,f15,f16,f20,f23,f24'
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=15)
    return resp.json()

def analyze_stock(stock):
    """深度分析单只股票"""
    code = stock['f12']
    name = stock['f14']
    
    # 排除条件
    if code.startswith('688') or code.startswith('300') or code.startswith('8') or code.startswith('4'):
        return None
    if 'ST' in name or '退' in name or name.startswith('N'):
        return None
    
    try:
        price = float(stock['f2']) if stock['f2'] != '-' else 0
        chg = float(stock['f3']) if stock['f3'] != '-' else 0
        volume = float(stock['f5']) if stock['f5'] != '-' else 0
        amount = float(stock['f6']) if stock['f6'] != '-' else 0
        turnover = float(stock['f8']) if stock['f8'] != '-' else 0
        high = float(stock['f15']) if stock['f15'] != '-' else price
        low = float(stock['f16']) if stock['f16'] != '-' else price
        mv = float(stock['f20']) / 1e8 if stock['f20'] != '-' else 0
        pe = float(stock['f23']) if stock['f23'] != '-' else 0
        chg_5d = float(stock['f24']) if stock['f24'] != '-' else 0
    except:
        return None
    
    # 基本筛选
    if price <= 3 or price > 20:  # 价格3-20元
        return None
    if chg < 4 or chg > 9:  # 今日涨幅4-9%
        return None
    if mv < 30 or mv > 100:  # 市值30-100亿
        return None
    if volume < 100000:  # 成交量 > 10万手
        return None
    if turnover < 3:  # 换手率 > 3%
        return None
    
    # 高级评分
    score = 0
    reasons = []
    
    # 1. 涨幅质量 (25分)
    if 5 < chg < 8:
        score += 25
        reasons.append(f'涨幅完美 {chg}%')
    elif 4 < chg < 9:
        score += 18
        reasons.append(f'涨幅良好 {chg}%')
    
    # 2. 市值弹性 (20分)
    if 30 < mv < 60:
        score += 20
        reasons.append(f'小市值高弹性 {mv}亿')
    elif 30 < mv < 80:
        score += 15
        reasons.append(f'中小市值 {mv}亿')
    
    # 3. 换手率活跃度 (20分)
    if turnover > 10:
        score += 20
        reasons.append(f'超高换手 {turnover}%')
    elif turnover > 5:
        score += 15
        reasons.append(f'活跃换手 {turnover}%')
    elif turnover > 3:
        score += 10
        reasons.append(f'换手适中 {turnover}%')
    
    # 4. 估值安全 (15分)
    if 0 < pe < 5:
        score += 15
        reasons.append(f'超低估值 PE{pe}')
    elif 0 < pe < 15:
        score += 12
        reasons.append(f'低估值 PE{pe}')
    elif 0 < pe < 30:
        score += 8
        reasons.append(f'估值合理 PE{pe}')
    elif pe < 0:
        score += 5
        reasons.append(f'亏损股 PE{pe}')
    
    # 5. 趋势强度 (10分)
    if 0 < chg_5d < 10:
        score += 10
        reasons.append(f'趋势向上 5日+{chg_5d}%')
    elif -5 < chg_5d < 15:
        score += 5
        reasons.append(f'趋势平稳 5日{chg_5d}%')
    
    # 6. 日内强度 (10分) - 收盘价接近最高价
    if high > 0:
        intraday_pos = (price - low) / (high - low) if high > low else 1
        if intraday_pos > 0.9:
            score += 10
            reasons.append(f'强势收盘 日内高位')
        elif intraday_pos > 0.7:
            score += 6
            reasons.append(f'偏强收盘')
    
    # 7. 成交量能 (额外加分)
    if amount > 5e8:  # 成交额 > 5亿
        score += 5
        reasons.append(f'大成交额 {amount/1e8:.1f}亿')
    
    return {
        'code': code,
        'name': name,
        'price': round(price, 2),
        'chg': round(chg, 2),
        'mv': round(mv, 2),
        'pe': round(pe, 2),
        'turnover': round(turnover, 2),
        'chg_5d': round(chg_5d, 2),
        'score': score,
        'reasons': reasons,
    }

def main():
    print('='*60)
    print('【深度优化选股策略 v2】')
    print('目标: 周涨幅30%+')
    print('='*60)
    print('')
    print('正在扫描市场...')
    
    data = get_realtime_data()
    
    candidates = []
    for stock in data['data']['diff']:
        result = analyze_stock(stock)
        if result and result['score'] >= 50:
            candidates.append(result)
    
    # 排序
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    print(f'扫描: {len(data["data"]["diff"])}只')
    print(f'候选: {len(candidates)}只')
    print('')
    
    if candidates:
        best = candidates[0]
        print('='*60)
        print('【今日唯一精选】')
        print('='*60)
        print('')
        print(f'代码: {best["code"]}')
        print(f'名称: {best["name"]}')
        print(f'价格: {best["price"]}元')
        print(f'涨幅: +{best["chg"]}%')
        print(f'市值: {best["mv"]}亿')
        print(f'PE: {best["pe"]}')
        print(f'换手: {best["turnover"]}%')
        print(f'5日涨幅: {best["chg_5d"]}%')
        print(f'综合评分: {best["score"]}分')
        print('')
        print('选股理由:')
        for i, r in enumerate(best['reasons'], 1):
            print(f'  {i}. {r}')
        print('')
        print('操作建议:')
        print('  买入: 明日开盘')
        print('  止损: -5%')
        print('  止盈: +30%')
        print('  持有: 5-7天')
        print('')
        print('='*60)
        print('TOP 5 备选:')
        print('='*60)
        for i, c in enumerate(candidates[:5], 1):
            print(f'{i}. {c["code"]} {c["name"]} {c["price"]}元 +{c["chg"]}% 评分{c["score"]}')
            print(f'   理由: {", ".join(c["reasons"][:3])}')
            print('')
    else:
        print('今日无符合条件股票，请降低筛选标准或等待机会')

if __name__ == '__main__':
    main()
