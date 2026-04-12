# -*- coding: utf-8 -*-
"""
收集50只股票数据 + 优化回测
目标: 选出每周涨30%的股票
"""
import os, sys, time, json, sqlite3, requests, numpy as np, pandas as pd
from datetime import datetime, timedelta

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')
sys.path.insert(0, os.getcwd())

DB_PATH = 'data/stocks.db'
DB_PATH2 = 'data/stocks_50.db'

# ============================================================
# 50只候选股票池 (从小市值、题材热门中精选)
# ============================================================
TARGET_50 = [
    ('600256', '广汇能源'), ('600127', '金健米业'), ('600219', '南山铝业'),
    ('600173', '卧龙新能'), ('601398', '工商银行'), ('600028', '中国石化'),
    ('600019', '宝钢股份'), ('601288', '农业银行'), ('600036', '招商银行'),
    ('601318', '中国平安'), ('600030', '中信证券'), ('601166', '兴业银行'),
    ('600048', '保利发展'), ('601012', '隆基绿能'), ('600900', '长江电力'),
    ('600519', '贵州茅台'), ('000858', '五粮液'), ('002714', '牧原股份'),
    ('000333', '美的集团'), ('600887', '伊利股份'), ('002475', '立讯精密'),
    ('300750', '宁德时代'), ('688041', '海光信息'), ('600522', '中天科技'),
    ('002466', '天齐锂业'), ('002594', '比亚迪'), ('601225', '陕西煤业'),
    ('600809', '山西汾酒'), ('002352', '顺丰控股'), ('603259', '药明康德'),
    ('000568', '泸州老窖'), ('600585', '海螺水泥'), ('601888', '中国中免'),
    ('002230', '科大讯飞'), ('600588', '用友网络'), ('300059', '东方财富'),
    ('600570', '恒生电子'), ('600031', '三一重工'), ('000002', '万科A'),
    ('601668', '中国建筑'), ('600837', '海通证券'), ('601688', '华泰证券'),
    ('600309', '万华化学'), ('002027', '分众传媒'), ('002415', '海康威视'),
    ('300015', '爱尔眼科'), ('300760', '迈瑞医疗'), ('603288', '海天味业'),
    ('600690', '海尔智家'), ('002460', '赣锋锂业'), ('601600', '中国铝业'),
    ('000063', '中兴通讯'), ('002049', '紫光国微'), ('600745', '闻泰科技'),
    ('000001', '平安银行'), ('601857', '中国石油'), ('600026', '中远海能'),
    ('601919', '中远海控'), ('600115', '东方航空'), ('601111', '中国国航'),
    ('600009', '上海机场'), ('601006', '大秦铁路'), ('600018', '上港集团'),
    ('600050', '中国联通'), ('601998', '中信银行'), ('601398', '工商银行'),
    ('601988', '中国银行'), ('601328', '交通银行'), ('601818', '光大银行'),
    ('600000', '浦发银行'), ('600015', '华夏银行'), ('601229', '上海银行'),
    ('600016', '民生银行'), ('600036', '招商银行'), ('601166', '兴业银行'),
    ('600176', '中国巨石'), ('002078', '太阳纸业'), ('000895', '双汇发展'),
    ('603605', '珀莱雅'), ('002304', '洋河股份'), ('000596', '古井贡酒'),
    ('603369', '今世缘'), ('002594', '比亚迪'), ('300014', '亿纬锂能'),
    ('300274', '阳光电源'), ('300498', '温氏股份'), ('002714', '牧原股份'),
    ('002385', '大北农'), ('000876', '新希望'), ('300122', '智飞生物'),
    ('300347', '泰格医药'), ('688180', '君实生物'), ('300759', '康龙化成'),
    ('603456', '九州药业'), ('002821', '凯莱英'), ('300015', '爱尔眼科'),
    ('300003', '乐普医疗'), ('002044', '美年健康'), ('300529', '健帆生物'),
    ('688399', '硕世生物'), ('300529', '健帆生物'), ('688111', '金山办公'),
    ('002230', '科大讯飞'), ('300474', '景嘉微'), ('688256', '寒武纪'),
    ('603019', '中科曙光'), ('688981', '中芯国际'), ('002371', '北方华创'),
    ('688012', '中微公司'), ('002459', '晶澳科技'), ('601012', '隆基绿能'),
    ('300274', '阳光电源'), ('002594', '比亚迪'), ('300014', '亿纬锂能'),
    ('002466', '天齐锂业'), ('002460', '赣锋锂业'), ('600111', '北方稀土'),
    ('600392', '盛和资源'), ('000831', '五矿稀土'), ('002176', '江特电机'),
    ('603799', '华友钴业'), ('300618', '寒锐钴业'), ('002340', '格林美'),
    ('002709', '天赐材料'), ('300037', '新宙邦'), ('300450', '先导智能'),
    ('688005', '容百科技'), ('688063', '派能科技'), ('002074', '国轩高科'),
    ('002594', '比亚迪'), ('300124', '汇川技术'), ('688116', '天奈科技'),
    ('603806', '福斯特'), ('002459', '晶澳科技'), ('601012', '隆基绿能'),
    ('600438', '通威股份'), ('600089', '特变电工'), ('002129', '中环股份'),
    ('600703', '三安光电'), ('600460', '士兰微'), ('002241', '歌尔股份'),
    ('002456', '欧菲光'), ('300408', '三环集团'), ('002036', '联创电子'),
    ('300207', '欣旺达'), ('002045', '国光电器'), ('688207', '格科微'),
    ('300223', '北京君正'), ('300782', '卓胜微'), ('603501', '韦尔股份'),
    ('688008', '澜起科技'), ('688036', '传音控股'), ('300033', '同花顺'),
    ('300059', '东方财富'), ('600570', '恒生电子'), ('688111', '金山办公'),
    ('002410', '广联达'), ('002439', '启明星辰'), ('300678', '中科信息'),
    ('688521', '芯原股份'), ('002185', '华天科技'), ('600745', '闻泰科技'),
    ('002049', '紫光国微'), ('300474', '景嘉微'), ('688256', '寒武纪'),
    ('603019', '中科曙光'), ('688981', '中芯国际'), ('002371', '北方华创'),
    ('688012', '中微公司'), ('300223', '北京君正'), ('300782', '卓胜微'),
]

# 去重
seen = set()
unique_50 = []
for code, name in TARGET_50:
    if code not in seen:
        seen.add(code)
        unique_50.append((code, name))
    if len(unique_50) >= 50:
        break

print(f"目标: 收集 {len(unique_50)} 只股票的历史K线数据")
print("=" * 60)

# ============================================================
# 数据收集
# ============================================================
def init_db(path):
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS kline (
        code TEXT, date TEXT, open REAL, close REAL, high REAL, low REAL,
        volume REAL, turnover REAL, amount REAL,
        UNIQUE(code, date))''')
    conn.commit()
    conn.close()

def collect(code, days=180):
    market = '1' if code.startswith('6') else ('0' if code.startswith('0') or code.startswith('3') else '1')
    end = datetime.now().strftime('%Y%m%d')
    start = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
    
    url = (f'https://push2his.eastmoney.com/api/qt/stock/kline/get'
           f'?secid={market}.{code}'
           f'&fields1=f1,f2,f3,f4,f5,f6'
           f'&fields2=f51,f52,f53,f54,f55,f56,f57'
           f'&klt=101&fqt=1&beg={start}&end={end}')
    
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        d = r.json()
        if d.get('data') and d['data'].get('klines'):
            klines = d['data']['klines']
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            for k in klines:
                p = k.split(',')
                c.execute('''INSERT OR IGNORE INTO kline 
                    (code,date,open,close,high,low,volume,turnover,amount)
                    VALUES (?,?,?,?,?,?,?,?,?)''',
                    (code, p[0], float(p[1]), float(p[2]), float(p[3]),
                     float(p[4]), float(p[5]), float(p[6]) if len(p)>6 else 0,
                     float(p[7]) if len(p)>7 else 0))
            conn.commit()
            conn.close()
            return len(klines)
    except Exception as e:
        pass
    return 0

init_db(DB_PATH)
print("开始收集K线数据...")

collected = []
for code, name in unique_50:
    n = collect(code, 180)
    if n > 0:
        collected.append((code, name, n))
    time.sleep(0.3)

print(f"\n收集完成: {len(collected)}/{len(unique_50)} 只")
for code, name, n in collected[:10]:
    print(f"  {code} {name}: {n}条K线")

# ============================================================
# 回测 - 优化策略
# ============================================================
print("\n" + "=" * 60)
print("运行优化回测...")

conn = sqlite3.connect(DB_PATH)
codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
conn.close()

print(f"数据库中股票数量: {len(codes)}")

# 多种策略回测
results = []

for holding in [5, 3, 1]:  # 持有天数
    for buy_chg_min, buy_chg_max in [(1, 5), (2, 8), (3, 9), (5, 10)]:
        for price_max in [15, 20, 30, 50]:
            trades = []
            
            for code in codes:
                conn = sqlite3.connect(DB_PATH)
                df = pd.read_sql(
                    'SELECT * FROM kline WHERE code=? ORDER BY date',
                    conn, params=(code,))
                conn.close()
                
                if df is None or len(df) < 40:
                    continue
                df = df.sort_values('date').tail(120).reset_index(drop=True)
                
                for i in range(25, len(df) - holding - 1):
                    row = df.iloc[i]
                    prev = df.iloc[i-1]
                    
                    chg = (row['close'] - prev['close']) / prev['close'] * 100 if prev['close'] > 0 else 0
                    
                    if buy_chg_min <= chg <= buy_chg_max and 3 <= row['close'] <= price_max:
                        buy = row['close']
                        sell = df.iloc[i + holding]['close']
                        if buy > 0:
                            pnl = (sell - buy) / buy * 100
                            # 计算周涨幅
                            week_end = min(i + holding, len(df) - 1)
                            week_chg = (df.iloc[week_end]['close'] - buy) / buy * 100
                            trades.append({
                                'code': code, 'date': row['date'],
                                'buy_chg': chg, 'price': buy,
                                'pnl': pnl, 'week_chg': week_chg,
                                'holding': holding
                            })
            
            if not trades:
                continue
            
            pnls = [t['pnl'] for t in trades]
            week_chgs = [t['week_chg'] for t in trades]
            wins = sum(1 for p in pnls if p > 0)
            targets = sum(1 for w in week_chgs if w >= 30)
            targets_10 = sum(1 for w in week_chgs if w >= 10)
            
            results.append({
                'holding': holding,
                'buy_chg': f'{buy_chg_min}-{buy_chg_max}',
                'price_max': price_max,
                'trades': len(trades),
                'win_rate': wins / len(trades) * 100,
                'avg_pnl': np.mean(pnls),
                'avg_week_chg': np.mean(week_chgs),
                'max_week_chg': max(week_chgs),
                'target_rate_30': targets / len(trades) * 100,
                'target_rate_10': targets_10 / len(trades) * 100,
            })

# 排序找最优
results.sort(key=lambda x: x['target_rate_30'], reverse=True)

print("\n策略回测结果 TOP 10:")
print(f"{'持有天':^6} {'买入涨幅':^10} {'价格上限':^8} {'交易数':^6} {'胜率':^8} {'平均收益':^10} {'周均收益':^10} {'最高周涨':^10} {'达标30%':^10}")
print("-" * 90)

for r in results[:10]:
    print(f"{r['holding']:^6} {r['buy_chg']:^10} {r['price_max']:^8} "
          f"{r['trades']:^6} {r['win_rate']:>6.1f}% {r['avg_pnl']:>8.2f}% "
          f"{r['avg_week_chg']:>8.2f}% {r['max_week_chg']:>8.2f}% {r['target_rate_30']:>8.1f}%")

best = results[0] if results else None

# 找出表现最好的股票
print("\n" + "=" * 60)
print("最佳股票 TOP 5 (按周涨幅):")

best_stocks = {}
for code in codes:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql('SELECT * FROM kline WHERE code=? ORDER BY date', conn, params=(code,))
    conn.close()
    if df is None or len(df) < 30:
        continue
    df = df.sort_values('date').tail(60).reset_index(drop=True)
    
    max_chg = 0
    best_date = ''
    for i in range(10, len(df) - 5):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        chg = (row['close'] - prev['close']) / prev['close'] * 100 if prev['close'] > 0 else 0
        if 3 <= chg <= 8 and 3 <= row['close'] <= 20:
            buy = row['close']
            sell = df.iloc[i + 5]['close']
            if buy > 0:
                pnl = (sell - buy) / buy * 100
                if pnl > max_chg:
                    max_chg = pnl
                    best_date = row['date']
    
    if max_chg > 5:
        name = ''
        for c, n in unique_50:
            if c == code:
                name = n
                break
        best_stocks[code] = (name, max_chg, best_date)

top_stocks = sorted(best_stocks.items(), key=lambda x: x[1][1], reverse=True)[:5]

for code, (name, pnl, date) in top_stocks:
    print(f"  {code} {name}: 最大周涨幅 {pnl:.1f}% (买入日: {date})")

# 保存结果
output = {
    'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
    'stocks_collected': len(collected),
    'total_codes_in_db': len(codes),
    'best_strategy': best,
    'top_stocks': [(code, name, round(pnl,1)) for code, (name, pnl, date) in top_stocks],
    'all_results': results[:20]
}

with open('data/collect_50_results.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 60)
print("【汇报】")
print("=" * 60)
print(f"- 收集进度: {len(collected)}只股票")
if best:
    print(f"- 回测结果: 胜率{best['win_rate']:.1f}%, 达标率{best['target_rate_30']:.1f}% (持有{best['holding']}天, 买入涨幅{best['buy_chg']}%)")
else:
    print(f"- 回测结果: 数据不足,无法回测")
if top_stocks:
    code, (name, pnl, date) = top_stocks[0]
    print(f"- 最佳股票: {code} {name} (周涨{pnl:.1f}%)")
else:
    print(f"- 最佳股票: 无")
print("- 下一步: 增加数据量,尝试更多策略参数组合")
print("=" * 60)
