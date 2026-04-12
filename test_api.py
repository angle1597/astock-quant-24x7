# -*- coding: utf-8 -*-
import sqlite3, sys, requests, pandas as pd
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'

conn = sqlite3.connect(DB_PATH)
df_quotes = pd.read_sql(
    '''SELECT code, name, price, change, turnover, amount, mv
       FROM realtime_quote
       WHERE code NOT LIKE '688%' AND code NOT LIKE '300%'
       AND code NOT LIKE '8%' AND name NOT LIKE '%ST%' ''',
    conn)
conn.close()

print(f"Candidates from DB: {len(df_quotes)}")
print(df_quotes.head(5).to_string())
