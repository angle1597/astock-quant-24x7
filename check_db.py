import sqlite3
conn = sqlite3.connect(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print("Tables:", tables)
for t in tables:
    c.execute(f"SELECT COUNT(*) FROM [{t}]")
    cnt = c.fetchone()[0]
    c.execute(f"PRAGMA table_info([{t}])")
    cols = [r[1] for r in c.fetchall()]
    print(f"  {t}: {cnt} rows, cols={cols[:10]}")
conn.close()
