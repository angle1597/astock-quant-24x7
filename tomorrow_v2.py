# -*- coding: utf-8 -*-
"""
明日涨停预测 v2 - 扩大筛选范围
"""
import requests

def main():
    url1 = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:1+t:2,m:1+t:23&fields=f12,f14,f2,f3,f5,f6,f8,f20,f23,f24'
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

    print('='*60)
    print('【明日涨停预测 v2】')
    print('='*60)
    print('扫描:', len(all_stocks), '只')

    candidates = []

    for s in all_stocks:
        code = s['f12']
        name = s['f14']

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

        # 放宽条件 - 找还没大涨的
        if price <= 2 or price > 20:
            continue
        if chg <= 0 or chg > 8:  # 不选已经涨停的
            continue
        if mv < 20 or mv > 150:
            continue

        score = 0

        # 涨幅适中 (还没涨停)
        if 1 <= chg <= 3:
            score += 30  # 最佳蓄势位置
        elif 3 < chg <= 5:
            score += 20
        elif 5 < chg <= 8:
            score += 10

        # 换手率
        if turnover >= 10:
            score += 25
        elif turnover >= 5:
            score += 15
        elif turnover >= 2:
            score += 5

        # 市值
        if 20 <= mv <= 50:
            score += 20
        elif 50 < mv <= 100:
            score += 15
        else:
            score += 10

        # 估值
        if 0 < pe < 15:
            score += 15
        elif pe <= 0:
            score += 10

        # 低价易涨停
        if price < 10:
            score += 10
        elif price < 15:
            score += 5

        # 5日趋势
        if chg_5d > 0:
            score += 5

        if score >= 50:
            candidates.append({
                'code': code, 'name': name, 'price': price,
                'chg': chg, 'mv': mv, 'pe': pe,
                'turnover': turnover, 'chg_5d': chg_5d, 'score': score
            })

    candidates.sort(key=lambda x: x['score'], reverse=True)

    print('候选:', len(candidates), '只')
    print('')

    if candidates:
        best = candidates[0]
        print('='*60)
        print('【唯一推荐 - 明日涨停预测】')
        print('='*60)
        print('代码:', best['code'])
        print('名称:', best['name'])
        print('价格:', best['price'], '元')
        print('今日涨幅:', '+' + str(round(best['chg'],2)) + '%')
        print('市值:', round(best['mv'],2), '亿')
        print('换手:', round(best['turnover'],2), '%')
        print('PE:', best['pe'])
        print('5日:', '+' + str(round(best['chg_5d'],2)) + '%')
        print('评分:', best['score'])
        print('')
        print('理由:')
        print('  1. 涨幅', round(best['chg'],1), '% 蓄势中')
        print('  2. 换手', round(best['turnover'],1), '% 资金活跃')
        print('  3. 价格', best['price'], '元 低价易涨')
        print('  4. 市值', round(best['mv'],1), '亿 弹性大')
        print('')
        print('操作: 今日买入 → 明日观察涨停')
        print('')
        print('='*60)
        print('TOP 5:')
        for i, c in enumerate(candidates[:5], 1):
            print(i, '.', c['code'], c['name'], c['price'], '元 +' + str(round(c['chg'],1)) + '%', '换手' + str(round(c['turnover'],1)) + '%')
    else:
        print('无候选股票')

if __name__ == '__main__':
    main()
