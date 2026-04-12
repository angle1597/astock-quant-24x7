import sqlite3
conn = sqlite3.connect('data/stocks.db')
cur = conn.cursor()

cur.execute('SELECT MIN(date), MAX(date) FROM kline')
print('kline date range:', cur.fetchone())
cur.execute('SELECT COUNT(DISTINCT code) FROM kline')
print('distinct stocks:', cur.fetchone()[0])
cur.execute('SELECT * FROM kline ORDER BY date DESC LIMIT 3')
print('kline latest rows:')
for row in cur.fetchall():
    print(row)
cur.execute('SELECT * FROM kline LIMIT 3')
print('kline oldest rows:')
for row in cur.fetchall():
    print(row)

# Check backtest results
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('all tables:', [r[0] for r in cur.fetchall()])

# Check pick history
for tbl in ['picks', 'pick_history', 'backtest_results', 'strategy_log']:
    try:
        cur.execute(f'SELECT COUNT(*) FROM {tbl}')
        print(f'{tbl}: {cur.fetchone()[0]} rows')
    except Exception as e:
        print(f'{tbl}: {e}')

# Check recent picks
try:
    cur.execute("SELECT * FROM picks ORDER BY date DESC LIMIT 5")
    print('recent picks:')
    for row in cur.fetchall():
        print(row)
except:
    pass

# Check backtest_results
try:
    cur.execute("SELECT * FROM backtest_results ORDER BY date DESC LIMIT 5")
    print('backtest results:')
    for row in cur.fetchall():
        print(row)
except:
    pass

conn.close()
