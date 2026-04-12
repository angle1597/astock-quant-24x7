# -*- coding: utf-8 -*-
"""
综合选股系统 v8 - 多策略融合
集成: 基础筛选 + 资金流 + 趋势动量
"""
import os
import sys
import json
import requests
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def get_all_stocks():
    """获取全市场股票"""
    url1 = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:1+t:2,m:1+t:23&fields=f12,f14,f2,f3,f5,f6,f8,f20,f23,f24,f62'
    url2 = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80&fields=f12,f14,f2,f3,f5,f6,f8,f20,f23,f24,f62'
    
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


def get_money_flow_rank():
    """获取资金流排名"""
    url = 'https://push2.eastmoney.com/api/qt/clist/get'
    params = {
        'pn': 1, 'pz': 500, 'po': 1, 'np': 1, 'fltt': 2, 'invt': 2,
        'fid': 'f62',  # 按主力净流入排序
        'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
        'fields': 'f12,f14,f2,f3,f5,f6,f8,f20,f62'
    }
    
    try:
        resp = requests.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        data = resp.json()
        return data.get('data', {}).get('diff', [])
    except:
        return []


def analyze_stock(stock, money_flow_rank=None):
    """综合分析股票"""
    code = stock['f12']
    name = stock['f14']
    
    # 排除
    if code.startswith('688') or code.startswith('300') or code.startswith('8') or code.startswith('4'):
        return None
    if 'ST' in name or '退' in name:
        return None
    
    try:
        price = float(stock['f2']) if stock['f2'] != '-' else 0
        change = float(stock['f3']) if stock['f3'] != '-' else 0
        turnover = float(stock['f8']) if stock['f8'] != '-' else 0
        mv = float(stock['f20']) / 1e8 if stock['f20'] != '-' else 0
        pe = float(stock['f23']) if stock['f23'] != '-' else 0
        change_5d = float(stock['f24']) if stock['f24'] != '-' else 0
        main_inflow = float(stock['f62']) if stock.get('f62') and stock['f62'] != '-' else 0
    except:
        return None
    
    if price <= 0:
        return None
    
    # 基础筛选
    if price < 3 or price > 50:
        return None
    if mv < 20 or mv > 200:
        return None
    
    # === 评分系统 ===
    score = {
        'total': 0,
        'trend': 0,      # 趋势
        'money': 0,      # 资金
        'momentum': 0,   # 动量
        'basic': 0       # 基本面
    }
    signals = []
    
    # 1. 趋势评分 (30分)
    if 3 <= change <= 8:
        score['trend'] = 30
        signals.append('强势上涨')
    elif 1 <= change < 3:
        score['trend'] = 20
        signals.append('温和上涨')
    elif change >= 8:
        score['trend'] = 15
        signals.append('涨停边缘')
    elif -3 <= change < 1:
        score['trend'] = 10
        signals.append('横盘整理')
    elif change > -3:
        score['trend'] = 5
        signals.append('小幅调整')
    
    # 2. 资金评分 (30分) - 最重要
    if main_inflow > 1e8:  # >1亿
        score['money'] = 30
        signals.append('主力大幅流入')
    elif main_inflow > 5000:  # >5000万
        score['money'] = 25
        signals.append('主力流入')
    elif main_inflow > 0:
        score['money'] = 15
        signals.append('资金正流入')
    elif main_inflow > -1000:
        score['money'] = 10
        signals.append('资金平稳')
    else:
        score['money'] = 5
        signals.append('主力流出')
    
    # 3. 动量评分 (25分)
    if turnover >= 15:
        score['momentum'] = 25
        signals.append('高度活跃')
    elif turnover >= 8:
        score['momentum'] = 20
        signals.append('活跃')
    elif turnover >= 4:
        score['momentum'] = 15
        signals.append('量能适中')
    elif turnover >= 2:
        score['momentum'] = 10
        signals.append('量能一般')
    else:
        score['momentum'] = 5
    
    # 4. 基本面评分 (15分)
    if 0 < pe <= 20:
        score['basic'] = 15
        signals.append('低估')
    elif 0 < pe <= 40:
        score['basic'] = 10
        signals.append('估值合理')
    elif pe <= 0:
        score['basic'] = 5
        signals.append('亏损')
    else:
        score['basic'] = 5
    
    score['total'] = sum(score.values())
    
    return {
        'code': code,
        'name': name,
        'price': price,
        'change_pct': change,
        'turnover': turnover,
        'market_cap': mv,
        'pe': pe,
        'main_inflow': main_inflow,
        'main_inflow_wan': main_inflow / 10000,
        'change_5d': change_5d,
        'score': score,
        'total_score': score['total'],
        'signals': signals[:3]
    }


def main():
    print("\n" + "="*60)
    print("【综合选股系统 v8】多策略融合")
    print("="*60)
    
    # 获取数据
    print("\n获取市场数据...")
    stocks = get_all_stocks()
    print(f"扫描: {len(stocks)}只")
    
    # 分析
    candidates = []
    for stock in stocks:
        result = analyze_stock(stock)
        if result and result['total_score'] >= 60:
            candidates.append(result)
    
    # 按总分排序
    candidates.sort(key=lambda x: x['total_score'], reverse=True)
    
    # TOP 10
    print("\n" + "="*60)
    print("【综合评分 TOP 10】")
    print("="*60)
    print("\n| 排名 | 代码 | 名称 | 现价 | 涨幅 | 主力流入 | 换手 | 总分 |")
    print("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    
    for i, c in enumerate(candidates[:10], 1):
        inflow_str = f"{c['main_inflow_wan']:.0f}万"
        if c['main_inflow_wan'] >= 10000:
            inflow_str = f"{c['main_inflow_wan']/10000:.1f}亿"
        
        print(f"| {i} | {c['code']} | {c['name']} | {c['price']:.2f} | {c['change_pct']:+.2f}% | {inflow_str} | {c['turnover']:.1f}% | {c['total_score']} |")
    
    # 分类推荐
    print("\n" + "="*60)
    print("【分类推荐】")
    print("="*60)
    
    # A类: 趋势+资金 (追涨)
    class_a = [c for c in candidates if c['change_pct'] >= 3 and c['main_inflow'] > 0][:5]
    print("\n📈 A类-趋势资金共振 (追涨):")
    print("| 代码 | 名称 | 涨幅 | 主力 | 评分 |")
    print("|:---:|:---:|:---:|:---:|:---:|")
    for c in class_a:
        inflow = f"{c['main_inflow_wan']/10000:.1f}亿" if c['main_inflow_wan'] >= 10000 else f"{c['main_inflow_wan']:.0f}万"
        print(f"| {c['code']} | {c['name']} | {c['change_pct']:+.1f}% | {inflow} | {c['total_score']} |")
    
    # B类: 超跌反弹
    class_b = [c for c in candidates if -5 <= c['change_pct'] < 0 and c['main_inflow'] > 0][:5]
    print("\n📉 B类-超跌反弹:")
    if class_b:
        print("| 代码 | 名称 | 跌幅 | 主力 | 评分 |")
        print("|:---:|:---:|:---:|:---:|:---:|")
        for c in class_b:
            inflow = f"{c['main_inflow_wan']/10000:.1f}亿" if c['main_inflow_wan'] >= 10000 else f"{c['main_inflow_wan']:.0f}万"
            print(f"| {c['code']} | {c['name']} | {c['change_pct']:+.1f}% | {inflow} | {c['total_score']} |")
    else:
        print("  无符合条件的股票")
    
    # C类: 低估值+资金
    class_c = [c for c in candidates if 0 < c['pe'] <= 30 and c['main_inflow'] > 0][:5]
    print("\n💰 C类-低估值+资金:")
    if class_c:
        print("| 代码 | 名称 | 市盈率 | 主力 | 评分 |")
        print("|:---:|:---:|:---:|:---:|:---:|")
        for c in class_c:
            inflow = f"{c['main_inflow_wan']/10000:.1f}亿" if c['main_inflow_wan'] >= 10000 else f"{c['main_inflow_wan']:.0f}万"
            print(f"| {c['code']} | {c['name']} | {c['pe']:.0f} | {inflow} | {c['total_score']} |")
    
    # 止损建议
    print("\n" + "="*60)
    print("【止损建议】")
    print("="*60)
    print("\n| 代码 | 名称 | 买入价 | 止损价(-5%) | 止盈建议 |")
    print("|:---:|:---:|:---:|:---:|:---:|")
    for c in candidates[:5]:
        stop = c['price'] * 0.95
        print(f"| {c['code']} | {c['name']} | {c['price']:.2f} | {stop:.2f} | +10% |")
    
    # 保存
    date_str = datetime.now().strftime('%Y-%m-%d')
    output = {
        'date': date_str,
        'version': 'v8',
        'candidates': candidates[:30],
        'class_a': class_a,
        'class_b': class_b,
        'class_c': class_c,
        'summary': {
            'total': len(candidates),
            'class_a': len(class_a),
            'class_b': len(class_b),
            'class_c': len(class_c)
        }
    }
    
    with open(f'data/comprehensive_picks_{date_str}.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存: data/comprehensive_picks_{date_str}.json")


if __name__ == '__main__':
    main()
