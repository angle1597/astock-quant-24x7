import sqlite3
conn = sqlite3.connect('data/stocks.db')
c = conn.cursor()
c.execute('SELECT DISTINCT code FROM kline')
codes = [r[0] for r in c.fetchall()]
print(f'Total stocks in kline: {len(codes)}')
print('Sample:', codes[:20])
c.execute('SELECT COUNT(*) FROM kline')
print(f'Total kline rows: {c.fetchone()[0]}')
c.execute('SELECT code, MIN(date), MAX(date), COUNT(*) FROM kline GROUP BY code LIMIT 5')
for r in c.fetchall():
    print(f'  {r[0]}: {r[1]} ~ {r[2]}, {r[3]} bars')
conn.close()
