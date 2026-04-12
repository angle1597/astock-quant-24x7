# -*- coding: utf-8 -*-
"""
明日涨停预测选股 v1
目标: 今天选 → 明天涨停
策略: 找今日涨幅3-6%、量能充足、蓄势待发的股票
"""
import requests

def main():
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

    print('='*60)
    print('【明日涨停预测】')
    print('目标: 今日选 → 明日涨停')
    print('='*60)
    print('扫描:', len(all_stocks), '只')
    print('')

    candidates = []

    for s in all_stocks:
        code = s['f12']
        name = s['f14']

        # 排除科创板、创业板、北交所、ST
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

        # ========== 关键筛选 ==========
        # 价格 3-15元 (低价股容易涨停)
        if price <= 3 or price > 15:
            continue

        # 涨幅 2-6% (蓄势区间，不是涨停但有动力)
        if chg < 2 or chg > 6:
            continue

        # 市值 30-100亿 (弹性最大)
        if mv < 30 or mv > 100:
            continue

        # 换手率 > 5% (有资金关注)
        if turnover < 5:
            continue

        # ========== 明日涨停预测评分 ==========
        score = 0

        # 1. 涨幅区间 (25分) - 2-4%最佳
        if 2 <= chg <= 4:
            score += 25  # 蓄势充分
        elif 4 < chg <= 6:
            score += 15  # 启动迹象

        # 2. 换手率 (25分)
        if turnover >= 15:
            score += 25
        elif turnover >= 10:
            score += 20
        elif turnover >= 7:
            score += 15
        elif turnover >= 5:
            score += 10

        # 3. 市值 (20分)
        if 30 <= mv <= 60:
            score += 20
        elif 60 < mv <= 80:
            score += 15
        else:
            score += 10

        # 4. 估值 (15分)
        if 0 < pe < 10:
            score += 15
        elif 0 < pe < 20:
            score += 10
        elif pe <= 0:
            score += 8

        # 5. 5日趋势 (15分)
        if 0 <= chg_5d <= 10:
            score += 15  # 稳步上涨
        elif -5 < chg_5d < 0:
            score += 12  # 调整充分
        elif chg_5d < -10:
            score += 10  # 超跌反弹

        # 6. 涨停预测加分
        # 价格低的更容易涨停
        if price < 8:
            score += 10
        elif price < 12:
            score += 5

        if score >= 55:
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

    print('候选:', len(candidates), '只')
    print('')

    if candidates:
        best = candidates[0]
        print('='*60)
        print('【明日涨停预测 - 唯一推荐】')
        print('='*60)
        print('代码:', best['code'])
        print('名称:', best['name'])
        print('价格:', best['price'], '元')
        print('今日涨幅:', '+' + str(best['chg']) + '%')
        print('市值:', best['mv'], '亿')
        print('PE:', best['pe'])
        print('换手:', best['turnover'], '%')
        print('5日涨幅:', best['chg_5d'], '%')
        print('预测评分:', best['score'], '分')
        print('')
        print('【选股逻辑】')
        print('  1. 今日涨幅', best['chg'], '% 蓄势充分')
        print('  2. 换手率', best['turnover'], '% 资金活跃')
        print('  3. 市值', best['mv'], '亿 弹性充足')
        print('  4. 低价', best['price'], '元 易涨停')
        print('')
        print('【操作建议】')
        print('  买入: 今日收盘前/明日开盘')
        print('  目标: 明日涨停 (+10%)')
        print('  止损: -3%')
        print('  持有: 1-3天')
        print('')
        print('='*60)
        print('TOP 5 备选:')
        for i, c in enumerate(candidates[:5], 1):
            print(i, '.', c['code'], c['name'], c['price'], '元 +' + str(c['chg']) + '%', '换手' + str(c['turnover']) + '%', '分' + str(c['score']))
    else:
        print('今日无符合条件的蓄势股票')
        print('建议: 等待市场机会')

if __name__ == '__main__':
    main()
