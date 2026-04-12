# -*- coding: utf-8 -*-
import sqlite3, sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db')
c = conn.cursor()

# Check columns of key tables
for tbl in ['realtime_quote', 'kline', 'stocks']:
    c.execute(f"PRAGMA table_info({tbl})")
    cols = [row[1] for row in c.fetchall()]
    print(f"{tbl} columns: {cols}")
    c.execute(f"SELECT * FROM {tbl} LIMIT 3")
    rows = c.fetchall()
    for r in rows:
        print(f"  {r}")
    print()
conn.close()
