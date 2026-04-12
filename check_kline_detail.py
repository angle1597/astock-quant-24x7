import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/stocks.db')
cur = conn.cursor()
cur.execute("SELECT DISTINCT code FROM kline ORDER BY code")
codes = [r[0] for r in cur.fetchall()]
print(f'Total stocks in kline: {len(codes)}')
print('Sample codes:', codes[:20])
# Check date range
cur.execute("SELECT MIN(date), MAX(date) FROM kline")
r = cur.fetchone()
print(f'Date range: {r[0]} to {r[1]}')
# Rows per stock
cur.execute("SELECT code, COUNT(*) as cnt FROM kline GROUP BY code ORDER BY cnt DESC LIMIT 10")
print('Top stocks by row count:')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]} rows')
conn.close()
