# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('data/stocks.db')
c = conn.cursor()
c.execute('SELECT COUNT(DISTINCT code) FROM kline')
print('Stocks:', c.fetchone()[0])
c.execute('SELECT MAX(date) FROM kline')
print('Latest:', c.fetchone()[0])
conn.close()
