# -*- coding: utf-8 -*-
"""
实时选股 - 更宽松条件
"""
import requests

def main():
    url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f12,f14,f2,f3,f5,f6,f8,f20,f23,f24'
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=15)
    data = resp.json()
    
    candidates = []
    
    for stock in data['data']['diff']:
        code = stock['f12']
        name = stock['f14']
        
        # 只排除科创板和北交所
        if code.startswith('688') or code.startswith('8') or code.startswith('4'):
            continue
        if 'ST' in name or '退' in name:
            continue
        
        try:
            price = float(stock['f2']) if stock['f2'] != '-' else 0
            chg = float(stock['f3']) if stock['f3'] != '-' else 0
            volume = float(stock['f5']) if stock['f5'] != '-' else 0
            turnover = float(stock['f8']) if stock['f8'] != '-' else 0
            mv = float(stock['f20']) / 1e8 if stock['f20'] != '-' else 0
            pe = float(stock['f23']) if stock['f23'] != '-' else 0
            chg_5d = float(stock['f24']) if stock['f24'] != '-' else 0
        except:
            continue
        
        # 超宽松筛选
        if price <= 0 or price > 30:
            continue
        if chg <= 0 or chg > 10:  # 上涨但未涨停
            continue
        if mv <= 0 or mv > 200:
            continue
        
        # 基础评分
        score = 0
        
        # 涨幅适中
        if 3 <= chg <= 8:
            score += 30
        elif chg > 0:
            score += 20
        
        # 市值
        if 30 <= mv <= 100:
            score += 25
        elif mv <= 150:
            score += 15
        
        # 换手
        if turnover >= 5:
            score += 20
        elif turnover >= 2:
            score += 10
        
        # 估值
        if 0 < pe < 10:
            score += 15
        elif 0 < pe < 30:
            score += 10
        
        # 5日趋势
        if -5 < chg_5d < 15:
            score += 10
        
        candidates.append({
            'code': code,
            'name': name,
            'price': price,
            'chg': chg,
            'mv': mv,
            'pe': pe,
            'turnover': turnover,
            'chg_5d': chg_5d,
            'score': score,
        })
    
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    print('='*60)
    print('【实时选股】')
    print('='*60)
    print(f'扫描: {len(data["data"]["diff"])}只')
    print(f'候选: {len(candidates)}只')
    print('')
    
    if candidates:
        best = candidates[0]
        print('【唯一推荐】')
        print(f'{best["code"]} {best["name"]}')
        print(f'价格: {best["price"]:.2f}元')
        print(f'涨幅: +{best["chg"]:.2f}%')
        print(f'市值: {best["mv"]:.2f}亿')
        print(f'PE: {best["pe"]:.2f}')
        print(f'换手: {best["turnover"]:.2f}%')
        print(f'5日: {best["chg_5d"]:.2f}%')
        print(f'评分: {best["score"]}')
        print('')
        print('TOP 10:')
        for i, c in enumerate(candidates[:10], 1):
            print(f'{i}. {c["code"]} {c["name"]} {c["price"]:.2f}元 +{c["chg"]:.2f}% 分{c["score"]}')

if __name__ == '__main__':
    main()
