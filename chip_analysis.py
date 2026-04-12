# -*- coding: utf-8 -*-
"""
皇氏集团(002329) 筹码分布深度分析
"""
import requests
import json
from datetime import datetime, timedelta
import sqlite3

CODE = '002329'

print('='*70)
print('皇氏集团筹码分布深度分析')
print('='*70)

# 1. 获取一年K线数据
print('\n【获取K线数据】')
market = '0'  # 深圳
end = datetime.now().strftime('%Y%m%d')
start = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')

url = f'https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={market}.{CODE}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&beg={start}&end={end}'

try:
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    data = r.json()
    
    if data.get('data') and data['data'].get('klines'):
        klines = data['data']['klines']
        print(f'获取到 {len(klines)} 条日K线')
        
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
        
        records.reverse()
        
        # ========== 筹码分布分析 ==========
        print('\n' + '='*70)
        print('【筹码分布分析】')
        print('='*70)
        
        # 近期价格分布
        print('\n【近期收盘价分布】')
        price_ranges = {
            '2.8-3.0': 0,
            '3.0-3.2': 0,
            '3.2-3.4': 0,
            '3.4-3.6': 0,
            '3.6-3.8': 0,
            '3.8-4.0': 0,
            '4.0+': 0
        }
        
        for r in records:
            c = r['close']
            if c < 3.0: price_ranges['2.8-3.0'] += 1
            elif c < 3.2: price_ranges['3.0-3.2'] += 1
            elif c < 3.4: price_ranges['3.2-3.4'] += 1
            elif c < 3.6: price_ranges['3.4-3.6'] += 1
            elif c < 3.8: price_ranges['3.6-3.8'] += 1
            elif c < 4.0: price_ranges['3.8-4.0'] += 1
            else: price_ranges['4.0+'] += 1
        
        total = len(records)
        print(f'总交易日: {total}天')
        print('\n价格区间分布（天数/占比）:')
        for range_name, count in price_ranges.items():
            pct = count / total * 100
            bar = '█' * int(pct / 2)
            print(f'  {range_name}: {count:3d}天 ({pct:5.1f}%) {bar}')
        
        # 计算筹码密集区
        closes = [r['close'] for r in records]
        current = closes[-1]
        
        print(f'\n【筹码密集区计算】')
        
        # 找出近期（60天）筹码分布
        recent = closes[-60:] if len(closes) >= 60 else closes
        
        min_p = min(recent)
        max_p = max(recent)
        avg_p = sum(recent) / len(recent)
        
        # 计算在当前价格附近的占比
        near_current = sum(1 for c in recent if abs(c - current) <= 0.1)
        pct_near = near_current / len(recent) * 100
        
        print(f'  近期均价: {avg_p:.2f}元')
        print(f'  近期最低: {min_p:.2f}元')
        print(f'  近期最高: {max_p:.2f}元')
        print(f'  当前价格附近({current}±0.1): {near_current}天 ({pct_near:.1f}%)')
        
        # ========== 成交量异常检测 ==========
        print('\n' + '='*70)
        print('【成交量异动分析】')
        print('='*70)
        
        volumes = [r['volume'] for r in records]
        avg_vol = sum(volumes[-60:]) / 60 if len(volumes) >= 60 else sum(volumes) / len(volumes)
        
        print(f'\n平均日成交量: {avg_vol/10000:.0f}万手')
        
        # 找出放量日
        print('\n【近期放量日（量比>1.5）】')
        abnormal_days = []
        for r in records[-30:]:
            vol_ratio = r['volume'] / avg_vol if avg_vol > 0 else 0
            if vol_ratio > 1.5:
                chg = (r['close'] - records[records.index(r)-1]['close']) / records[records.index(r)-1]['close'] * 100 if records.index(r) > 0 else 0
                abnormal_days.append({
                    'date': r['date'],
                    'close': r['close'],
                    'volume': r['volume'],
                    'vol_ratio': vol_ratio,
                    'chg': chg
                })
                print(f"  {r['date']}: 收{r['close']:.2f} 成交量{r['volume']/10000:.0f}万 量比{vol_ratio:.2f}x 涨跌{chg:+.2f}%")
        
        if not abnormal_days:
            print('  无明显放量日')
        
        # ========== 成本分布 ==========
        print('\n' + '='*70)
        print('【持仓成本分布估算】')
        print('='*70)
        
        # 按时间加权
        recent_amount = 0
        recent_vol = 0
        for i, r in enumerate(records[-60:]):
            weight = i + 1  # 越近权重越大
            recent_amount += r['close'] * r['volume'] * weight
            recent_vol += r['volume'] * weight
        
        if recent_vol > 0:
            weighted_cost = recent_amount / recent_vol
            print(f'\n按成交量加权成本: {weighted_cost:.2f}元')
            print(f'当前价格({current:.2f}) vs 成本: {(current/weighted_cost - 1)*100:+.2f}%')
        
        # ========== 主力动向 ==========
        print('\n' + '='*70)
        print('【主力动向分析】')
        print('='*70)
        
        # 计算资金流入
        # 简单方法：涨时量视为流入，跌时量视为流出
        inflow = 0
        outflow = 0
        for i, r in enumerate(records[-20:]):
            prev = records[-20+i-1]['close'] if i > 0 else r['close']
            if r['close'] > prev:
                inflow += r['amount']
            else:
                outflow += r['amount']
        
        net_flow = inflow - outflow
        print(f'\n近20日资金估算:')
        print(f'  流入: {inflow/1e8:.2f}亿')
        print(f'  流出: {outflow/1e8:.2f}亿')
        print(f'  净流入: {net_flow/1e8:.2f}亿')
        
        if net_flow > 0:
            print('  → 资金净流入，主力可能在吸筹')
        else:
            print('  → 资金净流出，主力可能在派发')
        
        # ========== 关键信号 ==========
        print('\n' + '='*70)
        print('【关键信号识别】')
        print('='*70)
        
        signals = []
        
        # 1. 筹码密集
        if pct_near > 30:
            signals.append(('筹码高度集中', '看涨', '集中后必有爆发'))
        
        # 2. 缩量整理
        recent_vol_avg = sum(volumes[-10:]) / 10
        if recent_vol_avg < avg_vol * 0.8:
            signals.append(('量能萎缩', '中性', '主力控盘观望'))
        
        # 3. 价格横盘
        price_std = (sum((c - avg_p)**2 for c in recent) / len(recent)) ** 0.5
        if price_std < 0.15:
            signals.append(('价格极度收敛', '看涨', '变盘在即'))
        
        # 4. 均线粘合
        ma5 = sum(closes[-5:]) / 5
        ma10 = sum(closes[-10:]) / 10
        ma20 = sum(closes[-20:]) / 20
        if abs(ma5 - ma10) < 0.05 and abs(ma10 - ma20) < 0.05:
            signals.append(('均线粘合', '强烈看涨', '即将选择方向'))
        
        # 5. 地量见地价
        if volumes[-1] < min(volumes[-60:]):
            signals.append(('出现地量', '看涨', '底部信号'))
        
        # 6. 连续小阳线
        small_up = 0
        for r in records[-5:]:
            chg = (r['close'] - r['open']) / r['open'] * 100
            if 0 < chg < 2:
                small_up += 1
        if small_up >= 4:
            signals.append(('连续小阳线', '看涨', '吸筹迹象'))
        
        print('\n发现以下信号:')
        for signal, status, reason in signals:
            status_icon = '✅' if '看涨' in status else '⚠️'
            print(f'  {status_icon} [{signal}] {status}')
            print(f'     原因: {reason}')
        
        # ========== 综合研判 ==========
        print('\n' + '='*70)
        print('【综合研判】')
        print('='*70)
        
        bullish = sum(1 for s in signals if '看涨' in s[1])
        neutral = sum(1 for s in signals if '中性' in s[1])
        
        print(f'\n看涨信号: {bullish}个')
        print(f'中性信号: {neutral}个')
        
        if bullish >= 3:
            print('\n🔔 强烈建议关注！筹码集中+技术面多个看涨信号')
        elif bullish >= 1:
            print('\n⚠️ 可以关注，但需等待放量确认')
        else:
            print('\n❌ 当前无明显信号，等待机会')
        
        # 保存分析结果
        analysis = {
            'code': CODE,
            'name': '皇氏集团',
            'analysis_time': datetime.now().isoformat(),
            'current_price': current,
            'signals': signals,
            'bullish_count': bullish,
            'neutral_count': neutral,
            'recent_60days': {
                'avg': avg_p,
                'min': min_p,
                'max': max_p
            }
        }
        
        with open('data/huangshi_chip_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        
except Exception as e:
    print(f'分析失败: {e}')

print('\n分析完成')
