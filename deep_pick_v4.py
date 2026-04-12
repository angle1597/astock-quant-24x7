# -*- coding: utf-8 -*-
"""
深度优化选股 v4 - 使用正确的A股接口
"""
import requests
import json

# 主板A股 - 上证+深证
def get_main_board():
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

def main():
    print('='*60)
    print('【深度优化选股 v4】目标: 周涨幅30%+')
    print('='*60)
    print('')
    print('正在扫描主板A股...')

    stocks = get_main_board()
    print(f'扫描: {len(stocks)}只')

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
        except:
            continue

        # 筛选条件
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
        else:
            score += 10

        # 市值 (25分)
        if 30 <= mv <= 60:
            score += 25
        elif mv <= 100:
            score += 20
        else:
            score += 10

        # 换手率 (20分)
        if turnover >= 8:
            score += 20
        elif turnover >= 4:
            score += 15
        elif turnover >= 2:
            score += 10

        # 估值 (15分)
        if 0 < pe < 8:
            score += 15
        elif 0 < pe < 20:
            score += 10
        elif pe <= 0:
            score += 8

        # 5日趋势 (10分)
        if 0 < chg_5d < 10:
            score += 10
        elif chg_5d < 0:
            score += 8

        if score >= 50:
            candidates.append({
                'code': code,
                'name': name,
                'price': round(price, 2),
                'chg': round(chg, 2),
                'mv': round(mv, 2),
                'pe': round(pe, 2),
                'turnover': round(turnover, 2),
                'chg_5d': round(chg_5d, 2),
                'score': score,
            })

    candidates.sort(key=lambda x: x['score'], reverse=True)

    print(f'候选: {len(candidates)}只')
    print('')

    if candidates:
        best = candidates[0]
        print('='*60)
        print('【唯一推荐】')
        print('='*60)
        print(f'代码: {best["code"]}')
        print(f'名称: {best["name"]}')
        print(f'价格: {best["price"]}元')
        print(f'涨幅: +{best["chg"]}%')
        print(f'市值: {best["mv"]}亿')
        print(f'PE: {best["pe"]}')
        print(f'换手: {best["turnover"]}%')
        print(f'5日涨幅: {best["chg_5d"]}%')
        print(f'评分: {best["score"]}分')
        print('')
        print('操作建议:')
        print('  买入: 次日开盘')
        print('  止损: -5%')
        print('  止盈: +30%')
        print('  持有: 5-7天')
        print('')
        print('='*60)
        print('TOP 5:')
        for i, c in enumerate(candidates[:5], 1):
            print(f'{i}. {c["code"]} {c["name"]} {c["price"]}元 +{c["chg"]}% 分{c["score"]}')
    else:
        print('无符合条件股票，建议:')
        print('  1. 等待市场机会')
        print('  2. 降低筛选标准')

if __name__ == '__main__':
    main()
