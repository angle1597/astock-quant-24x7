# -*- coding: utf-8 -*-
"""皇氏集团深度分析"""
import requests
import json
from datetime import datetime, timedelta

# 皇氏集团代码
CODE = '002329'

print('='*70)
print('皇氏集团(002329) 深度调研报告')
print('生成时间: ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
print('='*70)

# 1. 获取K线数据
print('\n【一、K线数据收集】')
market = '0'  # 深圳
end = datetime.now().strftime('%Y%m%d')
start = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')

url = f'https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={market}.{CODE}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&beg={start}&end={end}'

try:
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    data = r.json()
    
    if data.get('data') and data['data'].get('klines'):
        klines = data['data']['klines']
        print(f'获取到 {len(klines)} 条K线数据')
        
        # 解析K线
        records = []
        for k in klines:
            parts = k.split(',')
            records.append({
                'date': parts[0],
                'open': float(parts[1]),
                'close': float(parts[2]),
                'high': float(parts[3]),
                'low': float(parts[4]),
                'volume': float(parts[5]),
                'amount': float(parts[6])
            })
        
        records.reverse()  # 按日期正序
        
        # 基本统计
        closes = [r['close'] for r in records]
        volumes = [r['volume'] for r in records]
        
        print(f'\n股价范围: {min(closes):.2f} - {max(closes):.2f} 元')
        print(f'最新收盘: {closes[-1]:.2f} 元')
        print(f'近一年涨跌: {(closes[-1]/closes[0]-1)*100:+.2f}%')
        
        # 近期数据
        print('\n【近期K线】')
        for r in records[-10:]:
            chg = (r['close'] - records[records.index(r)-1]['close'])/records[records.index(r)-1]['close']*100 if records.index(r) > 0 else 0
            print(f"{r['date']} 开:{r['open']:.2f} 高:{r['high']:.2f} 低:{r['low']:.2f} 收:{r['close']:.2f} 量:{r['volume']/10000:.0f}万 涨:{chg:+.2f}%")
        
        # 计算技术指标
        print('\n【二、技术分析】')
        
        # 均线
        ma5 = sum(closes[-5:])/5
        ma10 = sum(closes[-10:])/10
        ma20 = sum(closes[-20:])/20
        ma60 = sum(closes[-60:])/60
        
        print(f'MA5:  {ma5:.2f} 元')
        print(f'MA10: {ma10:.2f} 元')
        print(f'MA20: {ma20:.2f} 元')
        print(f'MA60: {ma60:.2f} 元')
        
        # 近期涨幅
        print('\n【近期涨幅统计】')
        for d in [5, 10, 20, 60]:
            if len(closes) >= d:
                chg = (closes[-1] - closes[-d]) / closes[-d] * 100
                print(f'近{d}日: {chg:+.2f}%')
        
        # 成交量分析
        avg_vol = sum(volumes[-20:])/20
        last_vol = volumes[-1]
        vol_ratio = last_vol / avg_vol if avg_vol > 0 else 0
        print(f'\n成交量: 近期均量 {avg_vol/10000:.0f}万 股')
        print(f'昨日成交量: {last_vol/10000:.0f}万 股')
        print(f'量比: {vol_ratio:.2f}x')
        
        # 预测分析
        print('\n' + '='*70)
        print('【三、两个月走势预测分析】')
        print('='*70)
        
        current = closes[-1]
        
        # 支撑位
        low_price = min(closes[-60:])
        high_price = max(closes[-60:])
        
        print(f'\n支撑位分析:')
        print(f'  历史低点: {low_price:.2f} 元')
        print(f'  历史高点: {high_price:.2f} 元')
        print(f'  当前价格: {current:.2f} 元')
        print(f'  50%回调位: {(current + low_price)/2:.2f} 元')
        
        # 预测方案
        print('\n' + '-'*70)
        print('【乐观情景】持续放量上涨')
        print('-'*70)
        target1 = current * 1.15  # 涨15%
        target2 = current * 1.30  # 涨30%
        print(f'  一个月目标: {target1:.2f} 元 ({+15:.0f}%)')
        print(f'  两个月目标: {target2:.2f} 元 ({+30:.0f}%)')
        
        print('\n' + '-'*70)
        print('【中性情景】震荡整理')
        print('-'*70)
        target1 = current * 1.05
        target2 = current * 1.10
        print(f'  一个月目标: {target1:.2f} 元 ({+5:.0f}%)')
        print(f'  两个月目标: {target2:.2f} 元 ({+10:.0f}%)')
        
        print('\n' + '-'*70)
        print('【保守情景】回调整固')
        print('-'*70)
        target1 = current * 0.92
        target2 = current * 0.85
        print(f'  一个月目标: {target1:.2f} 元 ({-8:.0f}%)')
        print(f'  两个月目标: {target2:.2f} 元 ({-15:.0f}%)')
        
        # 保存数据
        with open('data/huangshi_analysis.json', 'w', encoding='utf-8') as f:
            json.dump({
                'code': CODE,
                'name': '皇氏集团',
                'current': current,
                'ma5': ma5, 'ma10': ma10, 'ma20': ma20, 'ma60': ma60,
                'klines': records[-60:],
                'analysis_time': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        
except Exception as e:
    print(f'获取数据失败: {e}')

print('\n' + '='*70)
print('报告生成完成')
print('='*70)
