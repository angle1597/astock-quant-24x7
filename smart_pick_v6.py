# -*- coding: utf-8 -*-
"""
智能选股策略 v6 - 基于动量和趋势的优化策略
"""
import requests
import json
import sys
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def get_realtime_data():
    """获取实时数据"""
    url1 = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:1+t:2,m:1+t:23&fields=f12,f14,f2,f3,f5,f6,f8,f20,f23,f24,f62,f115,f128,f140,f141'
    url2 = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80&fields=f12,f14,f2,f3,f5,f6,f8,f20,f23,f24,f62,f115,f128,f140,f141'
    
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


def analyze_stock(stock):
    """智能分析股票"""
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
        volume = float(stock['f5']) if stock['f5'] != '-' else 0
        amount = float(stock['f6']) / 1e8 if stock['f6'] != '-' else 0
        mv = float(stock['f20']) / 1e8 if stock['f20'] != '-' else 0
        pe = float(stock['f23']) if stock['f23'] != '-' else 0
        turnover = float(stock['f8']) if stock['f8'] != '-' else 0
        change_5d = float(stock['f24']) if stock['f24'] != '-' else 0
        # 主力净流入
        main_force = float(stock['f62']) if stock.get('f62') and stock['f62'] != '-' else 0
    except:
        return None
    
    if price <= 0:
        return None
    
    # 多维度评分
    score = 0
    signals = []
    
    # 1. 趋势动量 (40分)
    if 3 <= change <= 9:
        score += 40
        signals.append('强势上涨')
    elif 1 <= change < 3:
        score += 25
        signals.append('温和上涨')
    elif change > 9:
        score += 20
        signals.append('涨停边缘')
    elif -3 <= change < 1:
        score += 10
        signals.append('横盘整理')
    else:
        score += 5
        signals.append('超跌')
    
    # 2. 成交量 (25分)
    if turnover >= 15:
        score += 25
        signals.append('放量')
    elif turnover >= 8:
        score += 20
        signals.append('量能活跃')
    elif turnover >= 4:
        score += 15
        signals.append('量能适中')
    else:
        score += 5
    
    # 3. 主力资金 (20分)
    if main_force > 0:
        score += 20
        signals.append('主力净流入')
    elif main_force > -1000:
        score += 10
        signals.append('资金平稳')
    else:
        score += 5
    
    # 4. 超跌反弹 (15分)
    if change_5d < -10:
        score += 15
        signals.append('超跌反弹')
    elif change_5d < -5:
        score += 10
        signals.append('短期回调')
    
    # 5. 基本面加分
    if 0 < pe <= 25:
        score += 10
    elif pe <= 0:
        score += 5  # 亏损但有题材
    
    # 市值适中
    if 30 <= mv <= 150:
        score += 10
    
    return {
        'code': code,
        'name': name,
        'price': price,
        'change_pct': change,
        'turnover': turnover,
        'market_cap': mv,
        'pe': pe,
        'main_force': main_force,
        'change_5d': change_5d,
        'score': score,
        'signals': signals
    }


def main():
    print("\n" + "="*60)
    print("【智能选股策略 v6】动量+趋势+资金流")
    print("="*60)
    
    # 获取数据
    print("\n获取实时数据...")
    stocks = get_realtime_data()
    print(f"扫描: {len(stocks)}只")
    
    # 分析每只股票
    candidates = []
    for stock in stocks:
        result = analyze_stock(stock)
        if result and result['score'] >= 50:
            # 价格和市值筛选
            if 3 <= result['price'] <= 50:
                if 20 <= result['market_cap'] <= 200:
                    candidates.append(result)
    
    # 排序
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # 输出TOP 10
    print("\n" + "="*60)
    print("【TOP 10 选股结果】")
    print("="*60)
    print("\n| 排名 | 代码 | 名称 | 现价 | 涨幅 | 换手 | 评分 | 信号 |")
    print("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|")
    
    for i, c in enumerate(candidates[:10], 1):
        signals = ','.join(c['signals'][:2])
        print(f"| {i} | {c['code']} | {c['name']} | {c['price']:.2f} | {c['change_pct']:+.2f}% | {c['turnover']:.1f}% | {c['score']} | {signals} |")
    
    # 分类推荐
    print("\n" + "="*60)
    print("【分类推荐】")
    print("="*60)
    
    # 强势股
    strong = [c for c in candidates if c['change_pct'] >= 5][:3]
    print("\n🔥 强势股:")
    for c in strong:
        print(f"  {c['code']} {c['name']} 涨幅{c['change_pct']:+.1f}% 评分{c['score']}")
    
    # 超跌股
    oversold = [c for c in candidates if c['change_pct'] < 0][:3]
    print("\n📉 超跌反弹:")
    for c in oversold:
        print(f"  {c['code']} {c['name']} 涨幅{c['change_pct']:+.1f}% 评分{c['score']}")
    
    # 资金流入
    inflow = [c for c in candidates if c['main_force'] > 0][:3]
    print("\n💰 主力资金:")
    for c in inflow:
        print(f"  {c['code']} {c['name']} 流入{c['main_force']/10000:.0f}万 评分{c['score']}")
    
    # 保存结果
    date_str = datetime.now().strftime('%Y-%m-%d')
    with open(f'data/smart_picks_{date_str}.json', 'w', encoding='utf-8') as f:
        json.dump({
            'date': date_str,
            'candidates': candidates[:20],
            'summary': {
                'total': len(candidates),
                'strong': len(strong),
                'oversold': len(oversold),
                'inflow': len(inflow)
            }
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存: data/smart_picks_{date_str}.json")


if __name__ == '__main__':
    main()
