import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/stocks.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print('Tables:', [t[0] for t in tables])
for t in tables:
    tname = t[0]
    cur.execute(f'SELECT COUNT(*) FROM {tname}')
    cnt = cur.fetchone()[0]
    print(f'{tname} rows: {cnt}')
    if cnt > 0:
        cur.execute(f'SELECT * FROM {tname} LIMIT 1')
        cols = [d[0] for d in cur.description]
        print(f'  columns: {cols}')
conn.close()
