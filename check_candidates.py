# -*- coding: utf-8 -*-
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db'
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('''SELECT code, name, price, change_pct, amount, turnover 
             FROM realtime_quote 
             WHERE price > 0 AND price <= 15
             AND change_pct >= 6
             AND code NOT LIKE '688%' 
             AND name NOT LIKE '%ST%'
             ORDER BY change_pct DESC''')
rows = c.fetchall()
conn.close()
print(f'价格≤15元且涨幅≥6%的股票: {len(rows)}只')
print()
print(f'{"代码":^8} {"名称":^10} {"价格":^8} {"涨幅":^8} {"成交额":^8} {"换手":^8}')
print('-' * 60)
for row in rows[:20]:
    code, name, price, change_pct, amount, turnover = row
    try:
        amount_f = float(amount)/1e8 if amount else 0
        print(f'{code:^8} {name:^10} {float(price):^8.2f} {float(change_pct):>+7.2f}% {amount_f:^8.1f} {turnover:^8}')
    except:
        pass
