import sqlite3
conn = sqlite3.connect('data/stocks.db')
c = conn.cursor()

# Check stocks in kline
c.execute("SELECT COUNT(DISTINCT code) FROM kline")
print('Stocks:', c.fetchone()[0])

# Sample stock data
c.execute("SELECT code, date, open, high, low, close, volume FROM kline WHERE date='2026-04-11' LIMIT 5")
print('Today sample:', c.fetchall())

c.execute("SELECT DISTINCT code FROM kline WHERE date='2026-04-11' LIMIT 10")
print('Today stocks:', [r[0] for r in c.fetchall()])

# Check date distribution
c.execute("SELECT date, COUNT(*) FROM kline GROUP BY date ORDER BY date DESC LIMIT 10")
print('Recent dates:', c.fetchall())

conn.close()
