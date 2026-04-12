# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('data/stocks.db')
c = conn.cursor()

# 检查K线数据
c.execute('SELECT COUNT(*) FROM kline')
total = c.fetchone()[0]
print(f'K线总数: {total}')

c.execute('SELECT COUNT(DISTINCT code) FROM kline')
stocks = c.fetchone()[0]
print(f'股票数: {stocks}')

# 检查最新日期
c.execute('SELECT MAX(date), MIN(date) FROM kline')
max_d, min_d = c.fetchone()
print(f'日期范围: {min_d} - {max_d}')

# 检查表结构
c.execute('PRAGMA table_info(kline)')
print('\n表结构:')
for row in c.fetchall():
    print(f'  {row[1]}: {row[2]}')

# 采集实时数据测试
import requests
import json
from datetime import datetime

url = 'https://push2.eastmoney.com/api/qt/clist/get?cb=jQuery&pn=1&pz=50&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14'

try:
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://quote.eastmoney.com/'}, timeout=15)
    text = r.text
    start = text.find('(') + 1
    end = text.rfind(')')
    data = json.loads(text[start:end])
    
    stocks_data = data['data']['diff']
    print(f'\n实时数据: {len(stocks_data)} 只')
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 插入测试
    c.execute('DELETE FROM kline WHERE date = ?', (today,))
    
    for s in stocks_data[:10]:
        try:
            code = str(s.get('f12', ''))
            price = float(s.get('f2', 0))
            chg = float(s.get('f3', 0))
            volume = float(s.get('f5', 0))
            amount = float(s.get('f6', 0))
            
            c.execute('''INSERT INTO kline (code, date, close, volume, turnover)
                        VALUES (?, ?, ?, ?, ?)''',
                     (code, today, price, volume, amount))
        except:
            pass
    
    conn.commit()
    print(f'插入测试: 成功')
    
except Exception as e:
    print(f'实时数据获取失败: {e}')

conn.close()
print('\n完成!')
