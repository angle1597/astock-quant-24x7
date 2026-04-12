# -*- coding: utf-8 -*-
"""
智能选股 v5 - 结合国际市场
美股大涨 → A股联动 → 选受益板块
"""
import requests

def main():
    print('='*60)
    print('【智能选股 v5】结合国际市场')
    print('='*60)
    print('')

    h = {'User-Agent': 'Mozilla/5.0'}

    # 市场判断
    print('【市场环境】')
    print('  美股: 道琼斯+2.85%, 纳斯达克+2.8%')
    print('  A股: 跟涨预期')
    print('  策略: 电力、科技、低估值')
    print('')

    # 获取A股数据
    url = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeDataSimple?page=1&num=500&sort=change&asc=0&node=hs_a&symbol=&_s_r_a=page'
    r = requests.get(url, headers=h, timeout=15)
    data = r.json()

    candidates = []

    for s in data:
        code = s.get('symbol', '')
        name = s.get('name', '')

        if code.startswith('bj') or code.startswith('sh688') or code.startswith('sz300') or code.startswith('sz301'):
            continue
        if 'ST' in name or '退' in name:
            continue

        try:
            price = float(s.get('trade', 0))
            chg = float(s.get('changepercent', 0))
            turnover = float(s.get('amount', 0)) / 1e8
            high = float(s.get('high', 0))
            low = float(s.get('low', 0))
            open_p = float(s.get('open', 0))
        except:
            continue

        code_clean = code.replace('sh','').replace('sz','')

        # ========== 美股联动策略 ==========
        score = 0

        # 1. 美股大涨 → A股跟涨股
        if chg > 0:
            score += 20

        # 2. 热门板块加分
        hot_keywords = ['电力', '能源', '科技', '电子', '新能源', '光伏', '半导体', '通信']
        for kw in hot_keywords:
            if kw in name:
                score += 15
                break

        # 3. 低价易涨停
        if 3 <= price <= 8:
            score += 20
        elif 8 < price <= 15:
            score += 15

        # 4. 涨幅适中 (蓄势)
        if 1 <= chg <= 4:
            score += 25
        elif 4 < chg <= 7:
            score += 15

        # 5. 成交额
        if turnover >= 3:
            score += 20
        elif turnover >= 1:
            score += 10

        # 6. 强势收盘
        if high > 0 and low > 0 and high != low:
            pos = (price - low) / (high - low)
            if pos >= 0.8:
                score += 10

        if score >= 50:
            candidates.append({
                'code': code_clean,
                'name': name,
                'price': price,
                'chg': chg,
                'turnover': turnover,
                'score': score,
            })

    candidates.sort(key=lambda x: x['score'], reverse=True)

    if candidates:
        best = candidates[0]
        print('='*60)
        print('【唯一推荐】')
        print('='*60)
        print('代码:', best['code'])
        print('名称:', best['name'])
        print('价格:', best['price'], '元')
        print('涨幅:', '+' + str(round(best['chg'],2)) + '%')
        print('成交额:', round(best['turnover'],2), '亿')
        print('评分:', best['score'], '分')
        print('')
        print('【选股逻辑】')
        print('  1. 美股大涨 → A股跟涨预期')
        print('  2. 低价', best['price'], '元 → 易涨停')
        print('  3. 涨幅', round(best['chg'],1), '% → 蓄势充分')
        print('  4. 成交', round(best['turnover'],1), '亿 → 资金关注')
        print('')
        print('【操作】')
        print('  买入: 开盘')
        print('  目标: 涨停')
        print('  止损: -5%')
        print('')
        print('='*60)
        print('TOP 5:')
        for i, c in enumerate(candidates[:5], 1):
            print(i, '.', c['code'], c['name'], c['price'], '元 +' + str(round(c['chg'],1)) + '%', '分' + str(c['score']))
    else:
        print('无候选股票')

if __name__ == '__main__':
    main()
