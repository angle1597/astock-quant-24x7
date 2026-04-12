# -*- coding: utf-8 -*-
"""
明日最佳股票选择 - 基于优化策略 (修正版)
"""
import sys, sqlite3, json
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'

# 最佳策略参数
HOLD_DAYS = 21
CHG_MIN, CHG_MAX = 8, 15
PRICE_MAX = 15

print("=" * 80)
print("明日最佳股票选择")
print("=" * 80)
print(f"策略: 持有{HOLD_DAYS}天, 买入涨幅{CHG_MIN}-{CHG_MAX}%, 价格≤{PRICE_MAX}元")
print()

# 读取实时行情
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('''SELECT code, name, price, change, change_pct, volume, amount, turnover 
             FROM realtime_quote 
             WHERE price > 0 
             AND price <= ?
             AND code NOT LIKE '688%' 
             AND name NOT LIKE '%ST%'
             AND name NOT LIKE '%退%'
             ORDER BY change_pct DESC''', (PRICE_MAX,))
quotes = c.fetchall()
conn.close()

print(f"价格≤{PRICE_MAX}元的股票数: {len(quotes)}")
print()

# 筛选符合策略的股票
picks = []
for row in quotes:
    code, name, price, change, change_pct, volume, amount, turnover = row
    try:
        price_f = float(price) if price and price != '-' else 0
        change_pct_f = float(change_pct) if change_pct and change_pct != '-' else 0
        change_f = float(change) if change and change != '-' else 0
        amount_f = float(amount)/1e8 if amount and amount != '-' else 0
        
        if price_f <= 0 or price_f > PRICE_MAX:
            continue
        
        score = 0
        factors = []
        
        # 核心因子：涨幅在8-15%区间
        if CHG_MIN <= change_pct_f <= CHG_MAX:
            score += 60
            factors.append(f'涨幅{change_pct_f:.1f}%')
        elif 6 <= change_pct_f < CHG_MIN:
            score += 40
            factors.append(f'涨幅{change_pct_f:.1f}%')
        elif change_pct_f >= 9.5:
            score += 50
            factors.append('接近涨停')
        
        # 价格因子 (低价股优势)
        if 3 <= price_f <= 10:
            score += 30
            factors.append(f'低价{price_f:.1f}')
        elif 3 <= price_f <= PRICE_MAX:
            score += 20
            factors.append(f'价格{price_f:.1f}')
        
        # 成交额因子
        if amount_f >= 5:
            score += 20
            factors.append(f'成交{amount_f:.1f}亿')
        elif amount_f >= 2:
            score += 10
            factors.append(f'成交{amount_f:.1f}亿')
        elif amount_f >= 1:
            score += 5
        
        # 换手率因子
        try:
            turnover_f = float(turnover) if turnover and turnover != '-' else 0
            if turnover_f >= 5:
                score += 10
                factors.append(f'换手{turnover_f:.1f}%')
            elif turnover_f >= 3:
                score += 5
        except:
            pass
        
        # 热门题材加分
        hot_keywords = ['能源', '电力', '光伏', '新能源', 'AI', '军工', '芯片', '半导体', 
                       '锂电', '储能', '风电', '汽车', '稀土', '医药', '科技', '智能']
        for kw in hot_keywords:
            if kw in str(name):
                score += 8
                factors.append(f'题材:{kw}')
                break
        
        if score >= 60:
            picks.append({
                'code': code,
                'name': name,
                'price': price_f,
                'change_pct': change_pct_f,
                'change': change_f,
                'amount': amount_f,
                'score': score,
                'factors': ', '.join(factors[:4])
            })
    except Exception as e:
        pass

# 排序
picks.sort(key=lambda x: x['score'], reverse=True)

print(f"符合策略股票: {len(picks)}只")
print()
print(f"{'#':^3} {'代码':^8} {'名称':^10} {'价格':^8} {'涨幅':^8} {'成交额':^8} {'评分':^6} {'核心因子':<30}")
print("-" * 90)
for i, p in enumerate(picks[:15], 1):
    print(f"{i:^3} {p['code']:^8} {p['name']:^10} {p['price']:^8.2f} {p['change_pct']:>+7.2f}% "
          f"{p['amount']:^8.1f} {p['score']:^6} {p['factors'][:30]}")

print()
print("=" * 80)
if picks:
    top = picks[0]
    print(f"🎯 明日首选: {top['code']} {top['name']}")
    print(f"   当前价格: {top['price']:.2f}元")
    print(f"   今日涨幅: {top['change_pct']:+.2f}%")
    print(f"   成交额: {top['amount']:.1f}亿")
    print(f"   综合评分: {top['score']}")
    print(f"   核心因子: {top['factors']}")
    print(f"   预期持有: {HOLD_DAYS}天")
    print(f"   目标收益: 30%+")
    
    if len(picks) >= 2:
        alt = picks[1]
        print()
        print(f"🥈 备选: {alt['code']} {alt['name']} @ {alt['price']:.2f}元 (评分{alt['score']})")
    if len(picks) >= 3:
        alt3 = picks[2]
        print(f"🥉 第三选: {alt3['code']} {alt3['name']} @ {alt3['price']:.2f}元 (评分{alt3['score']})")
else:
    print("⚠️ 当前没有符合策略的股票")

print("=" * 80)

# 保存结果
result = {
    'date': '2026-04-09',
    'strategy': {
        'hold_days': HOLD_DAYS,
        'chg_range': f'{CHG_MIN}-{CHG_MAX}%',
        'price_max': PRICE_MAX
    },
    'top_pick': picks[0] if picks else None,
    'alternative': picks[1] if len(picks) >= 2 else None,
    'third_pick': picks[2] if len(picks) >= 3 else None,
    'all_picks': picks[:20]
}

with open('data/tomorrow_pick.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("\n✓ 结果已保存到 data/tomorrow_pick.json")
