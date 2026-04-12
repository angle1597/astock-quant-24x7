import sqlite3
conn = sqlite3.connect('data/stocks.db')
cur = conn.cursor()

tables = ['stocks', 'daily_kline', 'kline', 'realtime_quote', 'money_flow', 'pick_history']
for t in tables:
    cur.execute(f"PRAGMA table_info({t})")
    cols = cur.fetchall()
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    cnt = cur.fetchone()[0]
    print(f"\n=== {t} ({cnt} rows) ===")
    for c in cols:
        print(f"  {c[1]} {c[2]}")
