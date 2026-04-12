# -*- coding: utf-8 -*-
"""
每日精选一股 - 从东方财富实时数据筛选
"""
import requests
import json

def main():
    # 东方财富A股列表
    url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f12,f14,f2,f3,f5,f6,f8,f20,f23,f24'
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=15)
    data = resp.json()
    
    candidates = []
    
    for stock in data['data']['diff']:
        code = stock['f12']
        name = stock['f14']
        
        # 排除科创板、创业板、北交所、ST
        if code.startswith('688') or code.startswith('300') or code.startswith('8') or code.startswith('4'):
            continue
        if 'ST' in name or '退' in name or 'N' in name[:1]:  # 排除新股
            continue
        
        try:
            price = float(stock['f2']) if stock['f2'] != '-' else 0
            chg = float(stock['f3']) if stock['f3'] != '-' else 0
            mv = float(stock['f20']) / 1e8 if stock['f20'] != '-' else 0
            pe = float(stock['f23']) if stock['f23'] != '-' else 0
            chg_5d = float(stock['f24']) if stock['f24'] != '-' else 0
        except:
            continue
        
        # 基本筛选
        if price <= 2 or price > 25:  # 价格2-25元
            continue
        if chg < 3 or chg > 9.5:  # 今日涨幅3-9.5%
            continue
        if mv < 30 or mv > 150:  # 市值30-150亿
            continue
        
        # 评分
        score = 0
        
        # 涨幅适中 (30分)
        if 4 < chg < 8:
            score += 30
        elif 3 < chg < 9:
            score += 20
        
        # 市值适中 (25分)
        if 40 < mv < 100:
            score += 25
        elif 30 < mv < 120:
            score += 15
        
        # PE估值 (20分)
        if 0 < pe < 10:
            score += 20
        elif 0 < pe < 20:
            score += 15
        elif pe < 0:
            score += 10
        
        # 过去5天涨幅 (15分) - 不追高
        if 0 < chg_5d < 15:
            score += 15
        elif -10 < chg_5d < 20:
            score += 8
        
        # 价格位置 (10分)
        if 5 < price < 15:
            score += 10
        elif 3 < price < 20:
            score += 5
        
        candidates.append({
            'code': code,
            'name': name,
            'price': price,
            'chg': chg,
            'mv': round(mv, 2),
            'pe': pe,
            'chg_5d': chg_5d,
            'score': score,
        })
    
    # 排序
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
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
        print(f'  市值: {best["mv"]}亿')
        print(f'  PE: {best["pe"]}')
        print(f'  综合评分: {best["score"]}分')
        print('')
        print('选股逻辑:')
        print('  1. 主板中小市值股票')
        print('  2. 今日涨幅3-9.5%启动')
        print('  3. 估值合理不追高')
        print('  4. 价格适中流动性好')
        print('')
        print('操作建议:')
        print('  持有周期: 5-7天')
        print('  止损位: -5%')
        print('  止盈位: +30%')
        print('')
        print('='*60)
        print('TOP 5 备选:')
        for i, c in enumerate(candidates[:5], 1):
            print(f'{i}. {c["code"]} {c["name"]} {c["price"]}元 +{c["chg"]}% 评分{c["score"]}')
    else:
        print('今日无符合条件股票')

if __name__ == '__main__':
    main()
