# -*- coding: utf-8 -*-
"""
皇氏集团终极分析 - 月线+周线+主力动向
"""
import requests
import json
from datetime import datetime, timedelta

CODE = '002329'

print('='*70)
print('皇氏集团终极深度分析')
print('='*70)

# 1. 获取月K线数据
print('\n【获取月K线数据】')
market = '0'
end = datetime.now().strftime('%Y%m%d')
start = '20200101'  # 5年月线

url = f'https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={market}.{CODE}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57&klt=103&fqt=1&beg={start}&end={end}'

try:
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    data = r.json()
    
    if data.get('data') and data['data'].get('klines'):
        monthly = data['data']['klines']
        print(f'获取到 {len(monthly)} 条月K线')
        
        # 解析月线
        monthly_records = []
        for k in monthly:
            parts = k.split(',')
            monthly_records.append({
                'date': parts[0],
                'open': float(parts[1]),
                'close': float(parts[2]),
                'high': float(parts[3]),
                'low': float(parts[4]),
                'volume': float(parts[5]),
                'amount': float(parts[6])
            })
        
        monthly_records.reverse()
        
        print('\n【月线筹码分布】')
        print('='*70)
        
        # 月线价格分布
        for r in monthly_records[-24:]:  # 近24个月
            chg = (r['close'] - r['open']) / r['open'] * 100
            vol_wan = r['volume'] / 10000
            icon = '🟢' if chg > 0 else '🔴' if chg < 0 else '⚪'
            print(f"{r['date'][:7]} 开:{r['open']:.2f} 收:{r['close']:.2f} 高:{r['high']:.2f} 低:{r['low']:.2f} 量:{vol_wan:.0f}万 {icon}{chg:+.1f}%")
        
        # 月线关键分析
        print('\n【月线关键信号】')
        print('='*70)
        
        # 找出月线收盘价密集区
        monthly_closes = [r['close'] for r in monthly_records]
        
        print('\n月线收盘价分布（近24月）:')
        ranges = {'2-3': 0, '3-4': 0, '4-5': 0, '5-6': 0, '6-8': 0, '8+': 0}
        for c in monthly_closes:
            if c < 3: ranges['2-3'] += 1
            elif c < 4: ranges['3-4'] += 1
            elif c < 5: ranges['4-5'] += 1
            elif c < 6: ranges['5-6'] += 1
            elif c < 8: ranges['6-8'] += 1
            else: ranges['8+'] += 1
        
        for r, cnt in ranges.items():
            bar = '█' * cnt
            pct = cnt / len(monthly_closes) * 100
            print(f'  {r}元: {cnt}月 ({pct:.0f}%) {bar}')
        
        # 月线形态分析
        print('\n【月线形态分析】')
        print('='*70)
        
        last_3_close = [r['close'] for r in monthly_records[-3:]]
        if all(last_3_close[i] >= last_3_close[i-1] - 0.1 for i in range(1, len(last_3_close))):
            print('✅ 连续3月收盘价基本持平 = 主力控盘吸筹')
        
        # 找出历史大底
        all_lows = [r['low'] for r in monthly_records]
        min_low = min(all_lows)
        min_low_date = [r for r in monthly_records if r['low'] == min_low][0]['date']
        print(f'历史最低月收盘: {min_low}元 ({min_low_date})')
        
        # 当前处于历史低位
        current_month_close = monthly_records[-1]['close']
        pct_from_low = (current_month_close - min_low) / min_low * 100
        print(f'当前价格({current_month_close}元)距离历史低点: +{pct_from_low:.1f}%')
        
        if pct_from_low < 30:
            print('🔔 当前处于历史低位区域！')
        
except Exception as e:
    print(f'月线数据获取失败: {e}')

# 2. 获取周K线数据
print('\n\n【获取周K线数据】')
start = '20250101'
url = f'https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={market}.{CODE}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57&klt=102&fqt=1&beg={start}&end={end}'

try:
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    data = r.json()
    
    if data.get('data') and data['data'].get('klines'):
        weekly = data['data']['klines']
        print(f'获取到 {len(weekly)} 条周K线')
        
        weekly_records = []
        for k in weekly:
            parts = k.split(',')
            weekly_records.append({
                'date': parts[0],
                'open': float(parts[1]),
                'close': float(parts[2]),
                'high': float(parts[3]),
                'low': float(parts[4]),
                'volume': float(parts[5]),
                'amount': float(parts[6])
            })
        
        weekly_records.reverse()
        
        print('\n【近10周K线】')
        print('='*70)
        for r in weekly_records[-10:]:
            chg = (r['close'] - r['open']) / r['open'] * 100
            vol_wan = r['volume'] / 10000
            icon = '🟢' if chg > 0 else '🔴' if chg < 0 else '⚪'
            print(f"{r['date']} 收:{r['close']:.2f} 高:{r['high']:.2f} 低:{r['low']:.2f} 量:{vol_wan:.0f}万 {icon}{chg:+.1f}%")
        
        # 周线均线
        closes = [r['close'] for r in weekly_records]
        ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else sum(closes) / len(closes)
        ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else sum(closes) / len(closes)
        
        print(f'\n周线均线: MA5={ma5:.2f} MA10={ma10:.2f}')
        print(f'当前收盘: {closes[-1]:.2f}')
        
        if abs(ma5 - ma10) < 0.1:
            print('✅ 周线均线粘合！重要信号！')
        
except Exception as e:
    print(f'周线数据获取失败: {e}')

# 3. 历史底部形态分析
print('\n\n【历史底部形态分析】')
print('='*70)

# 获取日线找历史底部
start = '20180101'
url = f'https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={market}.{CODE}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&beg={start}&end={end}'

try:
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    data = r.json()
    
    if data.get('data') and data['data'].get('klines'):
        daily = data['data']['klines']
        daily_records = []
        for k in daily:
            parts = k.split(',')
            daily_records.append({
                'date': parts[0],
                'close': float(parts[2]),
                'high': float(parts[3]),
                'low': float(parts[4]),
                'volume': float(parts[5])
            })
        
        daily_records.reverse()
        
        # 找出所有历史低点
        lows = []
        for i in range(5, len(daily_records) - 5):
            if daily_records[i]['low'] < daily_records[i-1]['low'] and \
               daily_records[i]['low'] < daily_records[i+1]['low'] and \
               daily_records[i]['low'] < daily_records[i-2]['low'] and \
               daily_records[i]['low'] < daily_records[i+2]['low']:
                lows.append(daily_records[i])
        
        print(f'\n历史低点:')
        for low in lows[-10:]:
            print(f"  {low['date']}: {low['low']:.2f}元")
        
        # 底部形态识别
        print('\n【底部形态识别】')
        
        # 当前是否形成底部
        current_lows = [r for r in daily_records[-60:] if r['low'] < 3.5]
        print(f'近60日低点数量: {len(current_lows)}')
        
        if len(set([round(r['low'], 1) for r in current_lows])) <= 3:
            print('✅ 多个低点接近 = 底部区间确认')
        
        # 双底/头肩底检测
        low_prices = [r['low'] for r in daily_records[-30:]]
        min_price = min(low_prices)
        low_indices = [i for i, p in enumerate(low_prices) if abs(p - min_price) < 0.1]
        
        if len(low_indices) >= 2:
            print(f'✅ 可能形成双底！最低价{min_price:.2f}出现{len(low_indices)}次')
        
except Exception as e:
    print(f'底部分析失败: {e}')

# 4. 主力行为分析
print('\n\n【主力行为分析】')
print('='*70)

try:
    # 分析近期涨跌与成交量关系
    start = '20250301'
    url = f'https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={market}.{CODE}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&beg={start}&end={end}'
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    data = r.json()
    
    if data.get('data') and data['data'].get('klines'):
        records = []
        for k in data['data']['klines']:
            parts = k.split(',')
            records.append({
                'date': parts[0],
                'open': float(parts[1]),
                'close': float(parts[2]),
                'volume': float(parts[5]),
                'amount': float(parts[6])
            })
        
        records.reverse()
        
        print('\n【量价行为分析（近30日）】')
        
        # 统计
        up_days = sum(1 for r in records if r['close'] > r['open'])
        down_days = sum(1 for r in records if r['close'] < r['open'])
        
        avg_vol = sum(r['volume'] for r in records) / len(records)
        
        print(f'上涨日: {up_days}天')
        print(f'下跌日: {down_days}天')
        print(f'平均成交量: {avg_vol/10000:.0f}万')
        
        # 找出异常日
        print('\n【异常交易日】')
        for r in records[-10:]:
            vol_ratio = r['volume'] / avg_vol if avg_vol > 0 else 0
            chg = (r['close'] - r['open']) / r['open'] * 100
            
            if vol_ratio > 1.8 or vol_ratio < 0.5:
                print(f"  {r['date']}: 收{r['close']:.2f} 涨跌{chg:+.1f}% 量比{vol_ratio:.1f}x {'🔴放量' if vol_ratio > 1.5 and chg < 0 else '🟢放量' if vol_ratio > 1.5 and chg > 0 else '⚪缩量'}")
        
        # 判断主力意图
        print('\n【主力意图判断】')
        
        total_vol = sum(r['volume'] for r in records)
        total_amount = sum(r['amount'] for r in records)
        
        # 计算加权平均价格
        avg_price = total_amount / total_vol if total_vol > 0 else 0
        
        closes = [r['close'] for r in records]
        current = closes[-1]
        period_high = max(closes)
        period_low = min(closes)
        
        print(f'期间均价: {avg_price:.2f}元')
        print(f'期间最高: {period_high:.2f}元')
        print(f'期间最低: {period_low:.2f}元')
        print(f'当前价格: {current:.2f}元')
        
        # 判断
        if current < avg_price * 0.95:
            print('\n🔔 主力可能在洗盘！价格低于成本区域')
        elif current > avg_price * 1.05:
            print('\n⚠️ 主力可能有派发嫌疑')
        else:
            print('\n⚪ 主力可能仍在吸筹')
        
        if current < period_low * 1.05:
            print('🔔 价格接近区间低点，主力可能护盘')
        
except Exception as e:
    print(f'主力分析失败: {e}')

print('\n' + '='*70)
print('分析完成')
print('='*70)
