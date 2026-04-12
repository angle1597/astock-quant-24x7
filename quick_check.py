import sqlite3
conn = sqlite3.connect('data/stocks.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)
cur.execute('SELECT COUNT(*) FROM stock_daily')
print('stock_daily rows:', cur.fetchone()[0])
cur.execute('SELECT COUNT(DISTINCT ts_code) FROM stock_daily')
print('distinct stocks:', cur.fetchone()[0])

# Check schema of stock_daily
cur.execute("PRAGMA table_info(stock_daily)")
print("\nstock_daily schema:")
for col in cur.fetchall():
    print(f"  {col[1]}: {col[2]}")

# Check date range
cur.execute("SELECT MIN(trade_date), MAX(trade_date) FROM stock_daily")
print("\nDate range:", cur.fetchone())

# Sample data
cur.execute("SELECT * FROM stock_daily LIMIT 3")
print("\nSample rows:")
for row in cur.fetchall():
    print(row)

conn.close()
