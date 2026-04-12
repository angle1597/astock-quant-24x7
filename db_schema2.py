# -*- coding: utf-8 -*-
import sqlite3, sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db')
c = conn.cursor()

# Check stocks table
c.execute("SELECT * FROM stocks LIMIT 10")
rows = c.fetchall()
print(f"stocks: {len(rows)} rows")
for r in rows:
    print(f"  {r}")

# Check realtime_quote - how many non-ST, non-688, non-300
c.execute("SELECT COUNT(*) FROM realtime_quote WHERE NOT code LIKE '688%' AND NOT code LIKE '300%' AND NOT code LIKE '8%' AND NOT name LIKE '%ST%'")
print(f"\nFiltered realtime_quote (non-ST/non-科创/北交所): {c.fetchone()[0]}")

# Show sample with change column
c.execute("SELECT code, name, price, change, turnover, amount FROM realtime_quote WHERE NOT code LIKE '688%' AND NOT code LIKE '300%' AND NOT name LIKE '%ST%' LIMIT 10")
print("\nSample filtered:")
for r in c.fetchall():
    print(f"  {r}")

conn.close()
