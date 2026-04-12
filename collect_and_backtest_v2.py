# -*- coding: utf-8 -*-
"""
大规模K线数据收集 + 涨停回调策略测试
Target: 300+ stocks, 120 days kline, test limit-up pullback strategy
"""
import sys, sqlite3, time, requests, json
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'

# ============ STEP 1: Get stock list from realtime_quote ============
print("="*60)
print("STEP 1: 获取股票列表")
print("="*60)

conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('''SELECT code, name FROM realtime_quote 
             WHERE code NOT LIKE '688%' 
             AND code NOT LIKE '300%'
             AND code NOT LIKE '8%'
             AND code NOT LIKE '4%'
             AND name NOT LIKE '%ST%'
             AND name NOT LIKE '%退%'
             AND price > 2
             AND price < 200''')
rt_stocks = c.fetchall()
conn.close()

print(f"realtime_quote中有效股票: {len(rt_stocks)}只")

# ============ STEP 2: Also fetch fresh stocks from eastmoney ============
def fetch_eastmoney_stocks():
    """从东方财富获取A股列表"""
    stocks = []
    # 上交所主板 60xxxx
    # 深交所主板 00xxxx 002xxx
    for market_id, market_name in [('1', 'SH'), ('0', 'SZ')]:
        try:
            url = 'https://80.push2.eastmoney.com/api/qt/clist/get'
            params = {
                'cb': '',
                'pn': 1, 'pz': 2000,
                'po': 1, 'np': 1,
                'ut': 'bd1d9428105693ce1542496826873500',
                'fltt': 2,
                'invt': 2,
                'fid': 'f12',
                'fs': f'm:{market_id} t:2,m:{market_id} t:23' if market_id == '1' else f'm:{market_id} t:6,m:{market_id} t:80',
                'fields': 'f12,f14,f13',
                '_': int(time.time()*1000)
            }
            r = requests.get(url, params=params, 
                           headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                   'Referer': 'https://quote.eastmoney.com/'},
                           timeout=15)
            data = r.json()
            if data and 'data' in data and data['data'] and 'diff' in data['data']:
                for item in data['data']['diff']:
                    code = str(item.get('f12', '')).zfill(6)
                    name = item.get('f14', '')
                    # Filter: exclude 688x (STAR market), 300x (ChiNext), 8x, 4x
                    if (code and name and 
                        not code.startswith('688') and 
                        not code.startswith('300') and
                        not code.startswith('8') and
                        not code.startswith('4') and
                        'ST' not in name and
                        '退' not in name):
                        stocks.append((code, name))
            print(f"  {market_name}: fetched {len([s for s in stocks if (s[0].startswith('6') if market_id=='1' else not s[0].startswith('6'))])} stocks")
        except Exception as e:
            print(f"  {market_name} fetch error: {e}")
        time.sleep(0.5)
    return stocks

print("\n从东方财富获取新股票列表...")
em_stocks = fetch_eastmoney_stocks()
print(f"东方财富获取到: {len(em_stocks)}只")

# Merge all stocks
all_stocks_dict = {}
for code, name in rt_stocks:
    all_stocks_dict[code] = name
for code, name in em_stocks:
    if code not in all_stocks_dict:
        all_stocks_dict[code] = name

all_stocks = list(all_stocks_dict.items())
print(f"合并后总计: {len(all_stocks)}只股票")

# ============ STEP 3: Check existing data ============
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('SELECT code, COUNT(*) FROM kline GROUP BY code')
existing = dict(c.fetchall())
conn.close()

print(f"\n已有kline数据的股票: {len(existing)}只")

# Stocks needing data
NEED_DAYS = 120
need_collect = [(code, name) for code, name in all_stocks 
                if existing.get(code, 0) < NEED_DAYS]
print(f"需要补充数据的股票: {len(need_collect)}只")

# ============ STEP 4: Collect kline data ============
print("\n" + "="*60)
print(f"STEP 2: 采集K线数据 (目标:{len(need_collect)}只股票)")
print("="*60)

def collect_kline_sina(code, days=200):
    """从新浪获取K线数据"""
    market = 'sh' if code.startswith('6') else 'sz'
    url = 'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
    params = {
        'symbol': f'{market}{code}', 
        'scale': 240, 
        'ma': 'no', 
        'datalen': days
    }
    try:
        r = requests.get(url, params=params, 
                        headers={'User-Agent': 'Mozilla/5.0'},
                        timeout=12)
        data = r.json()
        if data and isinstance(data, list) and len(data) > 10:
            return [(code, d['day'], float(d['open']), float(d['close']),
                    float(d['high']), float(d['low']), float(d['volume']), 0)
                   for d in data if all(k in d for k in ['day','open','close','high','low','volume'])]
    except:
        pass
    return []

def collect_kline_eastmoney(code, days=120):
    """从东方财富获取K线数据"""
    secid = f"1.{code}" if code.startswith('6') else f"0.{code}"
    url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
    params = {
        'secid': secid,
        'ut': 'bd1d9428105693ce1542496826873500',
        'fields1': 'f1,f2,f3,f4,f5,f6',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
        'klt': 101,  # daily
        'fqt': 1,    # forward adjust
        'end': '20260430',
        'lmt': days,
        '_': int(time.time()*1000)
    }
    try:
        r = requests.get(url, params=params,
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                                'Referer': 'https://quote.eastmoney.com/'},
                        timeout=12)
        data = r.json()
        if data and 'data' in data and data['data'] and 'klines' in data['data']:
            rows = []
            for kline in data['data']['klines']:
                parts = kline.split(',')
                if len(parts) >= 6:
                    try:
                        rows.append((code, parts[0], float(parts[1]), float(parts[2]),
                                    float(parts[3]), float(parts[4]), float(parts[5]), 0))
                    except:
                        pass
            return rows
    except:
        pass
    return []

def save_klines(rows):
    """批量保存K线数据"""
    if not rows:
        return 0
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    count = 0
    for row in rows:
        try:
            c.execute('''INSERT OR IGNORE INTO kline 
                (code,date,open,close,high,low,volume,turnover)
                VALUES (?,?,?,?,?,?,?,?)''', row)
            count += 1
        except:
            pass
    conn.commit()
    conn.close()
    return count

# Collect with progress
success = 0
failed = 0
total_new_rows = 0

for i, (code, name) in enumerate(need_collect):
    # Try eastmoney first, fallback to sina
    rows = collect_kline_eastmoney(code, 150)
    if len(rows) < 50:
        rows = collect_kline_sina(code, 200)
    
    n = save_klines(rows)
    total_new_rows += n
    
    if len(rows) >= 50:
        success += 1
        if i % 20 == 0 or success <= 5:
            print(f"  [{i+1}/{len(need_collect)}] {code} {name}: {len(rows)} bars saved")
    else:
        failed += 1
    
    # Rate limit
    time.sleep(0.1 if i % 3 != 0 else 0.3)
    
    # Progress every 50
    if (i+1) % 50 == 0:
        print(f"  Progress: {i+1}/{len(need_collect)} | Success:{success} Failed:{failed} NewRows:{total_new_rows}")

print(f"\n采集完成: Success={success}, Failed={failed}, NewRows={total_new_rows}")

# ============ STEP 5: Summary of DB ============
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('SELECT COUNT(DISTINCT code) FROM kline')
total_stocks = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM kline')
total_rows = c.fetchone()[0]
c.execute('SELECT MIN(date), MAX(date) FROM kline')
date_range = c.fetchone()
conn.close()

print(f"\n数据库统计:")
print(f"  股票数: {total_stocks}")
print(f"  K线总行数: {total_rows}")
print(f"  日期范围: {date_range[0]} ~ {date_range[1]}")

# ============ STEP 6: Limit-up Pullback Strategy Backtest ============
print("\n" + "="*60)
print("STEP 3: 涨停回调策略回测")
print("="*60)
print("策略逻辑: 涨停后1-3天内回调买入，持有3-5天")

conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('SELECT DISTINCT code FROM kline')
all_codes = [r[0] for r in c.fetchall()]
conn.close()

def get_klines_for_code(code):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT date, open, high, low, close, volume FROM kline WHERE code=? ORDER BY date', (code,))
    rows = c.fetchall()
    conn.close()
    return rows

def backtest_limit_up_pullback(klines, 
                                pullback_days=3,    # 涨停后N天内回调买入
                                pullback_pct=-0.02, # 回调幅度 >= 2%
                                hold_days=5,        # 持有天数
                                stop_loss=-0.07):   # 止损
    """涨停回调策略回测"""
    trades = []
    n = len(klines)
    if n < 20:
        return trades
    
    LIMIT_UP = 0.095  # 涨停线9.5%
    
    i = 1
    while i < n - hold_days - 1:
        date, o, h, l, c_price, vol = klines[i]
        prev_close = klines[i-1][4]
        
        # Check limit-up
        if prev_close <= 0:
            i += 1
            continue
        chg = (c_price - prev_close) / prev_close
        
        if chg >= LIMIT_UP:
            # Found limit-up! Look for pullback in next pullback_days
            limit_price = c_price
            buy_date = None
            buy_price = None
            
            for j in range(1, pullback_days + 1):
                if i + j >= n - hold_days - 1:
                    break
                pb_date, pb_o, pb_h, pb_l, pb_c, pb_vol = klines[i + j]
                pb_chg = (pb_c - limit_price) / limit_price
                
                # Buy if pullback >= pullback_pct
                if pb_chg <= pullback_pct:
                    buy_date = pb_date
                    buy_price = pb_o  # Next day open
                    buy_idx = i + j + 1
                    break
            
            if buy_price and buy_idx < n:
                # Hold for hold_days or stop loss
                sell_date = None
                sell_price = None
                entry_price = klines[buy_idx][1]  # open of buy day
                
                for k in range(1, hold_days + 1):
                    if buy_idx + k >= n:
                        break
                    sell_d, sell_o, sell_h, sell_l, sell_c, sell_vol = klines[buy_idx + k]
                    ret = (sell_c - entry_price) / entry_price if entry_price > 0 else 0
                    
                    # Stop loss
                    if ret <= stop_loss:
                        sell_date = sell_d
                        sell_price = sell_c
                        break
                    
                    # Take profit at hold_days
                    if k == hold_days:
                        sell_date = sell_d
                        sell_price = sell_c
                
                if entry_price > 0 and sell_price and sell_price > 0:
                    ret = (sell_price - entry_price) / entry_price
                    trades.append({
                        'limit_date': date,
                        'buy_date': buy_date,
                        'sell_date': sell_date,
                        'entry': entry_price,
                        'exit': sell_price,
                        'return': ret
                    })
            
            i += pullback_days + 2  # Skip ahead
        else:
            i += 1
    
    return trades

# Run backtest on all stocks
all_trades = []
codes_tested = 0

for code in all_codes:
    klines = get_klines_for_code(code)
    if len(klines) < 30:
        continue
    trades = backtest_limit_up_pullback(klines)
    for t in trades:
        t['code'] = code
    all_trades.extend(trades)
    codes_tested += 1

print(f"\n回测结果:")
print(f"  测试股票数: {codes_tested}")
print(f"  总交易次数: {len(all_trades)}")

if all_trades:
    returns = [t['return'] for t in all_trades]
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    
    avg_ret = sum(returns) / len(returns)
    win_rate = len(wins) / len(returns)
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 999
    
    print(f"  平均收益率: {avg_ret*100:.2f}%")
    print(f"  胜率: {win_rate*100:.1f}%")
    print(f"  平均盈利: {avg_win*100:.2f}%")
    print(f"  平均亏损: {avg_loss*100:.2f}%")
    print(f"  盈亏比: {profit_factor:.2f}")
    
    # Best and worst trades
    all_trades.sort(key=lambda x: x['return'], reverse=True)
    print(f"\n  最佳交易 Top5:")
    for t in all_trades[:5]:
        print(f"    {t['code']} {t['limit_date']} -> {t['sell_date']}: {t['return']*100:.1f}%")
    
    print(f"\n  最差交易 Worst5:")
    for t in all_trades[-5:]:
        print(f"    {t['code']} {t['limit_date']} -> {t['sell_date']}: {t['return']*100:.1f}%")
    
    # Save results
    result = {
        'strategy': 'limit_up_pullback',
        'params': {
            'pullback_days': 3,
            'pullback_pct': -0.02,
            'hold_days': 5,
            'stop_loss': -0.07
        },
        'stats': {
            'codes_tested': codes_tested,
            'total_trades': len(all_trades),
            'avg_return': round(avg_ret*100, 2),
            'win_rate': round(win_rate*100, 1),
            'avg_win': round(avg_win*100, 2),
            'avg_loss': round(avg_loss*100, 2),
            'profit_factor': round(profit_factor, 2)
        },
        'top_trades': all_trades[:10],
        'run_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    with open('data/limit_up_pullback_backtest.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到 data/limit_up_pullback_backtest.json")
else:
    print("  没有发现交易机会（数据可能不足）")

print("\n全部完成!")
