# -*- coding: utf-8 -*-
"""
深度优化选股策略 v3
放宽条件，提高命中率
"""
import requests
import json

def main():
    url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f12,f14,f2,f3,f5,f6,f8,f15,f16,f20,f23,f24'
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=15)
    data = resp.json()
    
    candidates = []
    
    for stock in data['data']['diff']:
        code = stock['f12']
        name = stock['f14']
        
        # 排除
        if code.startswith('688') or code.startswith('300') or code.startswith('8') or code.startswith('4'):
            continue
        if 'ST' in name or '退' in name or name.startswith('N'):
            continue
        
        try:
            price = float(stock['f2']) if stock['f2'] != '-' else 0
            chg = float(stock['f3']) if stock['f3'] != '-' else 0
            volume = float(stock['f5']) if stock['f5'] != '-' else 0
            turnover = float(stock['f8']) if stock['f8'] != '-' else 0
            high = float(stock['f15']) if stock['f15'] != '-' else price
            low = float(stock['f16']) if stock['f16'] != '-' else price
            mv = float(stock['f20']) / 1e8 if stock['f20'] != '-' else 0
            pe = float(stock['f23']) if stock['f23'] != '-' else 0
            chg_5d = float(stock['f24']) if stock['f24'] != '-' else 0
        except:
            continue
        
        # 放宽筛选
        if price <= 2 or price > 25:
            continue
        if chg < 3 or chg > 9.5:  # 放宽到3-9.5%
            continue
        if mv < 30 or mv > 150:  # 放宽到150亿
            continue
        
        # 评分
        score = 0
        reasons = []
        
        # 涨幅 (25分)
        if 5 <= chg <= 8:
            score += 25
            reasons.append(f'涨幅完美{chg}%')
        elif 3 <= chg <= 9:
            score += 18
            reasons.append(f'涨幅良好{chg}%')
        
        # 市值 (20分)
        if 30 <= mv <= 80:
            score += 20
            reasons.append(f'小市值{mv}亿')
        elif mv <= 120:
            score += 15
            reasons.append(f'中市值{mv}亿')
        
        # 换手 (15分)
        if turnover >= 8:
            score += 15
            reasons.append(f'高换手{turnover}%')
        elif turnover >= 4:
            score += 10
            reasons.append(f'活跃{turnover}%')
        elif turnover >= 2:
            score += 5
        
        # 估值 (15分)
        if 0 < pe < 8:
            score += 15
            reasons.append(f'低估值PE{pe}')
        elif 0 < pe < 20:
            score += 10
            reasons.append(f'估值合理PE{pe}')
        elif pe <= 0:
            score += 8
            reasons.append('亏损股')
        
        # 5日趋势 (10分)
        if 0 < chg_5d < 12:
            score += 10
            reasons.append(f'5日+{chg_5d}%')
        elif chg_5d < 0:
            score += 8  # 超跌反弹
            reasons.append(f'超跌反弹')
        
        # 日内强度 (10分)
        if high > low:
            pos = (price - low) / (high - low)
            if pos >= 0.85:
                score += 10
                reasons.append('强势收盘')
            elif pos >= 0.6:
                score += 5
        
        # 量能 (5分)
        if volume > 200000:
            score += 5
            reasons.append('放量')
        
        if score >= 40:
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
                'reasons': reasons,
            })
    
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    print('='*60)
    print('【深度优化选股 v3】目标: 周涨幅30%+')
    print('='*60)
    print(f'扫描: {len(data["data"]["diff"])}只 | 候选: {len(candidates)}只')
    print('')
    
    if candidates:
        best = candidates[0]
        print('【唯一推荐】')
        print(f'代码: {best["code"]} | 名称: {best["name"]}')
        print(f'价格: {best["price"]}元 | 涨幅: +{best["chg"]}%')
        print(f'市值: {best["mv"]}亿 | PE: {best["pe"]} | 换手: {best["turnover"]}%')
        print(f'5日涨幅: {best["chg_5d"]}% | 评分: {best["score"]}分')
        print('')
        print('理由:')
        for r in best['reasons']:
            print(f'  - {r}')
        print('')
        print('操作: 买入后持有5-7天 | 止损-5% | 止盈+30%')
        print('')
        print('='*60)
        print('TOP 5:')
        for i, c in enumerate(candidates[:5], 1):
            print(f'{i}. {c["code"]} {c["name"]} {c["price"]}元 +{c["chg"]}% 分{c["score"]}')
    else:
        print('无符合条件股票')

if __name__ == '__main__':
    main()
