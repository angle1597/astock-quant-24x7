# -*- coding: utf-8 -*-
"""
资金流选股策略 v7 - 基于主力资金动向
"""
import requests
import json
import sys
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def get_money_flow_data():
    """获取资金流数据"""
    # 东方财富资金流向接口
    url = 'https://push2.eastmoney.com/api/qt/stock/get'
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # 获取主力净流入排名
    list_url = 'https://push2.eastmoney.com/api/qt/clist/get'
    params = {
        'pn': 1,
        'pz': 500,
        'po': 1,
        'np': 1,
        'fltt': 2,
        'invt': 2,
        'fid': 'f62',  # 按主力净流入排序
        'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
        'fields': 'f12,f14,f2,f3,f5,f6,f8,f20,f23,f62,f184'
    }
    
    try:
        resp = requests.get(list_url, params=params, headers=headers, timeout=15)
        data = resp.json()
        return data.get('data', {}).get('diff', [])
    except Exception as e:
        print(f"获取数据失败: {e}")
        return []


def get_stock_detail(code):
    """获取单只股票详情"""
    try:
        # 基本信息
        quote_url = f'https://hq.sinajs.cn/list={code}'
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn'}
        resp = requests.get(quote_url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            text = resp.text.strip()
            # 解析: var hq_str_xxxxx="name,price,change,volume,..."
            parts = text.split('"')[1].split(',')
            if len(parts) > 10:
                return {
                    'name': parts[0],
                    'price': float(parts[3]) if parts[3] else 0,
                    'change': float(parts[3]) if parts[3] else 0,
                    'open': float(parts[1]) if parts[1] else 0,
                    'high': float(parts[4]) if parts[4] else 0,
                    'low': float(parts[5]) if parts[5] else 0,
                    'volume': float(parts[8]) if parts[8] else 0,
                }
    except:
        pass
    return None


def analyze_money_flow(stock):
    """分析资金流"""
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
        main_inflow = float(stock['f62']) if stock.get('f62') and stock['f62'] != '-' else 0  # 主力净流入
        turnover = float(stock['f8']) if stock['f8'] != '-' else 0
        mv = float(stock['f20']) / 1e8 if stock['f20'] != '-' else 0  # 市值(万)
        pe = float(stock['f23']) if stock['f23'] != '-' else 0
    except:
        return None
    
    if price <= 0 or mv <= 0:
        return None
    
    # 筛选条件
    if price < 3 or price > 50:
        return None
    if mv < 20 or mv > 200:
        return None
    if turnover < 2:  # 换手率太低
        return None
    
    # 评分
    score = 0
    signals = []
    
    # 1. 主力资金 (40分) - 核心指标
    if main_inflow > 1e8:  # >1亿
        score += 40
        signals.append('主力大幅流入')
    elif main_inflow > 5000:  # >5000万
        score += 30
        signals.append('主力流入')
    elif main_inflow > 0:
        score += 20
        signals.append('资金正流入')
    elif main_inflow > -1000:
        score += 10
        signals.append('资金平稳')
    else:
        score += 5
        signals.append('主力流出')
    
    # 2. 涨幅 (25分)
    if 3 <= change <= 8:
        score += 25
        signals.append('强势上涨')
    elif 1 <= change < 3:
        score += 20
        signals.append('温和上涨')
    elif change > 8:
        score += 15
        signals.append('接近涨停')
    elif -3 <= change < 1:
        score += 10
        signals.append('横盘整理')
    else:
        score += 5
        signals.append('调整中')
    
    # 3. 换手率 (20分)
    if turnover >= 15:
        score += 20
        signals.append('高度活跃')
    elif turnover >= 8:
        score += 15
        signals.append('活跃')
    elif turnover >= 4:
        score += 10
        signals.append('量能适中')
    else:
        score += 5
    
    # 4. 市盈率加分 (15分)
    if 0 < pe <= 20:
        score += 15
        signals.append('低估值')
    elif 0 < pe <= 40:
        score += 10
        signals.append('估值合理')
    elif pe <= 0:
        score += 5
        signals.append('亏损股')
    
    return {
        'code': code,
        'name': name,
        'price': price,
        'change_pct': change,
        'main_inflow': main_inflow,
        'main_inflow_wan': main_inflow / 10000,  # 转换为万元
        'turnover': turnover,
        'market_cap': mv,
        'pe': pe,
        'score': score,
        'signals': signals
    }


def main():
    print("\n" + "="*60)
    print("【资金流选股策略 v7】主力资金动向分析")
    print("="*60)
    
    # 获取资金流数据
    print("\n获取主力资金流向数据...")
    stocks = get_money_flow_data()
    print(f"获取到: {len(stocks)}只股票")
    
    # 分析每只股票
    candidates = []
    for stock in stocks[:200]:  # 取前200只
        result = analyze_money_flow(stock)
        if result and result['score'] >= 50:
            candidates.append(result)
    
    # 按主力净流入排序
    candidates.sort(key=lambda x: x['main_inflow'], reverse=True)
    
    # 输出TOP 10
    print("\n" + "="*60)
    print("【TOP 10 资金流入股票】")
    print("="*60)
    print("\n| 排名 | 代码 | 名称 | 现价 | 涨幅 | 主力流入 | 换手 | 评分 |")
    print("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    
    for i, c in enumerate(candidates[:10], 1):
        inflow_str = f"{c['main_inflow_wan']:.0f}万"
        if c['main_inflow_wan'] >= 10000:
            inflow_str = f"{c['main_inflow_wan']/10000:.1f}亿"
        
        print(f"| {i} | {c['code']} | {c['name']} | {c['price']:.2f} | {c['change_pct']:+.2f}% | {inflow_str} | {c['turnover']:.1f}% | {c['score']} |")
    
    # 分类推荐
    print("\n" + "="*60)
    print("【分类推荐】")
    print("="*60)
    
    # 主力大幅流入
    big_inflow = [c for c in candidates if c['main_inflow'] > 50000000][:3]
    print("\n💰 主力大幅流入 (>5000万):")
    for c in big_inflow:
        print(f"  {c['code']} {c['name']} 流入{c['main_inflow_wan']/10000:.1f}亿 涨幅{c['change_pct']:+.1f}%")
    
    # 强势+资金
    strong_money = [c for c in candidates if c['change_pct'] >= 3 and c['main_inflow'] > 0][:3]
    print("\n🔥 强势+资金流入:")
    for c in strong_money:
        print(f"  {c['code']} {c['name']} 涨幅{c['change_pct']:+.1f}% 流入{c['main_inflow_wan']/10000:.1f}亿")
    
    # 超跌反弹
    oversold = [c for c in candidates if -5 <= c['change_pct'] < 0 and c['main_inflow'] > 0][:3]
    print("\n📉 超跌+资金流入:")
    for c in oversold:
        print(f"  {c['code']} {c['name']} 跌幅{c['change_pct']:+.1f}% 流入{c['main_inflow_wan']/10000:.1f}亿")
    
    # 保存结果
    date_str = datetime.now().strftime('%Y-%m-%d')
    output = {
        'date': date_str,
        'type': 'money_flow',
        'candidates': candidates[:20],
        'summary': {
            'total': len(candidates),
            'big_inflow': len(big_inflow),
            'strong_money': len(strong_money),
            'oversold': len(oversold)
        }
    }
    
    with open(f'data/money_flow_picks_{date_str}.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存: data/money_flow_picks_{date_str}.json")


if __name__ == '__main__':
    main()
