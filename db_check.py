# -*- coding: utf-8 -*-
import sqlite3, sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in c.fetchall()]
print("Tables:", tables)
for t in tables:
    c.execute(f"SELECT COUNT(*) FROM {t}")
    print(f"  {t}: {c.fetchone()[0]} rows")
    c.execute(f"SELECT * FROM {t} LIMIT 3")
    for row in c.fetchall():
        print(f"    {row}")
conn.close()
