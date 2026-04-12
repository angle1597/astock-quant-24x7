# -*- coding: utf-8 -*-
"""
收集更多K线数据 - 目标200只股票
"""
import sys, sqlite3, time, requests
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'

# Get candidates from realtime_quote
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('''SELECT code, name FROM realtime_quote 
             WHERE code NOT LIKE '688%' 
             AND code NOT LIKE '300%'
             AND code NOT LIKE '8%' 
             AND name NOT LIKE '%ST%'
             AND name NOT LIKE '%退%' ''')
candidates = c.fetchall()
conn.close()

# Check existing
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('SELECT code, COUNT(*) FROM kline GROUP BY code')
existing = dict(c.fetchall())
conn.close()

need = [(code, name, existing.get(code, 0)) for code, name in candidates if existing.get(code, 0) < 150]
need.sort(key=lambda x: x[2])

print(f"Need to collect: {len(need)} stocks")

def collect_sina(code, days=200):
    market = 'sh' if code.startswith('6') else 'sz'
    url = 'https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
    params = {'symbol': f'{market}{code}', 'scale': 240, 'ma': 'no', 'datalen': days}
    try:
        r = requests.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'}, timeout=12)
        data = r.json()
        if data and isinstance(data, list) and len(data) > 10:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            count = 0
            for d in data:
                try:
                    c.execute('''INSERT OR IGNORE INTO kline 
                        (code,date,open,close,high,low,volume,turnover)
                        VALUES (?,?,?,?,?,?,?,?)''',
                        (code, d['day'], float(d['open']), float(d['close']),
                         float(d['high']), float(d['low']), float(d['volume']), 0))
                    count += 1
                except:
                    pass
            conn.commit()
            conn.close()
            return count
    except:
        pass
    return 0

# Collect
collected = []
for code, name, old in need[:80]:
    n = collect_sina(code, 200)
    if n > old:
        collected.append((code, name, old, n))
        print(f"  {code} {name}: {old} -> {n}")
    time.sleep(0.15)

# Final count
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('SELECT COUNT(DISTINCT code) FROM kline')
total = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM kline')
klines = c.fetchone()[0]
conn.close()

print(f"\nDone. Collected: {len(collected)}")
print(f"Total: {total} stocks, {klines} k-lines")
