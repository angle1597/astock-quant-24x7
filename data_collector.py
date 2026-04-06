# -*- coding: utf-8 -*-
"""
A股多源数据采集器
Multi-source Data Collector for A-Stocks
"""

import requests
import pandas as pd
import sqlite3
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import random

# 配置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

PROXIES = {
    # 'http': 'http://127.0.0.1:7890',
    # 'https': 'http://127.0.0.1:7890',
}

class DataCollector:
    """多源数据采集器"""
    
    def __init__(self, db_path: str = 'data/stocks.db'):
        self.db_path = db_path
        self.logger = self._setup_logger()
        self.session = self._create_session()
        self._init_db()
        
    def _setup_logger(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            handlers=[
                logging.FileHandler('logs/collector.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger('DataCollector')
    
    def _create_session(self):
        session = requests.Session()
        session.headers.update(HEADERS)
        return session
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 股票基本信息
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                code TEXT PRIMARY KEY,
                name TEXT,
                market TEXT,
                sector TEXT,
                updated_at TEXT
            )
        ''')
        
        # 日线数据
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_kline (
                code TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                PRIMARY KEY (code, date)
            )
        ''')
        
        # 实时行情
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS realtime_quote (
                code TEXT PRIMARY KEY,
                name TEXT,
                price REAL,
                change REAL,
                change_pct REAL,
                volume REAL,
                amount REAL,
                vr REAL,
                turnover REAL,
                pe REAL,
                pb REAL,
                mv REAL,
                updated_at TEXT
            )
        ''')
        
        # 资金流
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS money_flow (
                code TEXT,
                date TEXT,
                main_net REAL,
                main_net_pct REAL,
                retail_net REAL,
                PRIMARY KEY (code, date)
            )
        ''')
        
        conn.commit()
        conn.close()
        self.logger.info(f'Database initialized: {self.db_path}')
    
    def _request_with_retry(self, url: str, params: dict = None, 
                           retries: int = 3, delay: float = 1.0) -> Optional[dict]:
        """带重试的请求"""
        for i in range(retries):
            try:
                time.sleep(delay + random.uniform(0, 0.5))
                response = self.session.get(url, params=params, 
                                         proxies=PROXIES if PROXIES else None,
                                         timeout=15)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                self.logger.warning(f'Request failed (attempt {i+1}/{retries}): {e}')
                if i < retries - 1:
                    time.sleep(delay * (i + 1))
        return None
    
    # ==================== 东方财富数据源 ====================
    
    def get_realtime_quotes_eastmoney(self, codes: List[str] = None) -> pd.DataFrame:
        """东方财富实时行情"""
        if codes:
            fs = ','.join([('1.' if c.startswith('6') else '0.') + c for c in codes])
        else:
            fs = 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23'  # 全市场
        
        url = 'https://push2.eastmoney.com/api/qt/clist/get'
        params = {
            'pn': 1,
            'pz': 500,
            'po': 1,
            'np': 1,
            'fltt': 2,
            'invt': 2,
            'fid': 'f3',
            'fs': fs,
            'fields': 'f12,f14,f2,f3,f4,f5,f6,f8,f10,f15,f16,f17,f18,f20,f21,f22,f23,f24,f25,f30,f31,f32,f33,f34,f35'
        }
        
        data = self._request_with_retry(url, params)
        if not data or 'data' not in data or not data['data'].get('diff'):
            return pd.DataFrame()
        
        records = []
        for item in data['data']['diff']:
            records.append({
                'code': item.get('f12', ''),
                'name': item.get('f14', ''),
                'price': item.get('f2', 0),
                'change': item.get('f3', 0),
                'change_pct': item.get('f4', 0),
                'volume': item.get('f5', 0),
                'amount': item.get('f6', 0),
                'vr': item.get('f10', 0),
                'turnover': item.get('f8', 0),
                'pe': item.get('f23', 0),
                'pb': item.get('f24', 0),
                'mv': item.get('f20', 0),
                'high52': item.get('f15', 0),
                'low52': item.get('f16', 0),
            })
        
        df = pd.DataFrame(records)
        self.logger.info(f'Eastmoney quotes: {len(df)} stocks')
        return df
    
    def get_kline_eastmoney(self, code: str, period: str = '101', 
                            start: str = None, end: str = None) -> pd.DataFrame:
        """东方财富K线数据"""
        market = '1' if code.startswith('6') else '0'
        secid = f'{market}.{code}'
        
        url = f'https://push2his.eastmoney.com/api/qt/stock/kline/get'
        params = {
            'secid': secid,
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'klt': period,  # 101=日K
            'fqt': 1,  # 前复权
            'end': end or '20500101',
            'lmt': 120
        }
        
        data = self._request_with_retry(url, params)
        if not data or 'data' not in data or not data['data'].get('klines'):
            return pd.DataFrame()
        
        records = []
        for line in data['data']['klines']:
            parts = line.split(',')
            records.append({
                'code': code,
                'date': parts[0],
                'open': float(parts[1]),
                'high': float(parts[2]),
                'low': float(parts[3]),
                'close': float(parts[4]),
                'volume': float(parts[5]),
                'amount': float(parts[6]) if len(parts) > 6 else 0
            })
        
        df = pd.DataFrame(records)
        self.logger.info(f'Eastmoney kline {code}: {len(df)} bars')
        return df
    
    # ==================== 新浪财经数据源 ====================
    
    def get_realtime_quote_sina(self, codes: List[str]) -> Dict:
        """新浪财经实时行情"""
        codes_str = ','.join([('sh' if c.startswith('6') else 'sz') + c for c in codes])
        url = f'https://hq.sinajs.cn/list={codes_str}'
        
        data = self._request_with_retry(url)
        if not data:
            return {}
        
        result = {}
        for item in data.get('data', {}).values() if isinstance(data.get('data'), dict) else []:
            pass  # 解析逻辑
        
        return result
    
    # ==================== 同花顺数据源 ====================
    
    def get_financial_sina(self, code: str) -> Dict:
        """同花顺财务数据"""
        url = f'https://d.10jqka.com.cn/v6/line/hs_{code}/01/last20.js'
        # 需要特殊处理
        
        return {}
    
    # ==================== 数据库操作 ====================
    
    def save_realtime_quotes(self, df: pd.DataFrame):
        """保存实时行情到数据库"""
        if df.empty:
            return
        
        df['updated_at'] = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        
        # 使用 REPLACE 模式
        for _, row in df.iterrows():
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO realtime_quote 
                (code, name, price, change, change_pct, volume, amount, vr, turnover, pe, pb, mv, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['code'], row['name'], row['price'], row['change'], row['change_pct'],
                row['volume'], row['amount'], row['vr'], row['turnover'], row['pe'], row['pb'], row['mv'],
                row['updated_at']
            ))
        
        conn.commit()
        conn.close()
        self.logger.info(f'Saved {len(df)} quotes to database')
    
    def save_klines(self, df: pd.DataFrame):
        """保存K线数据"""
        if df.empty:
            return
        
        conn = sqlite3.connect(self.db_path)
        
        for _, row in df.iterrows():
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO daily_kline 
                (code, date, open, high, low, close, volume, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['code'], row['date'], row['open'], row['high'], row['low'],
                row['close'], row['volume'], row['amount']
            ))
        
        conn.commit()
        conn.close()
        self.logger.info(f'Saved {len(df)} klines to database')
    
    def get_historical_quotes(self, code: str, days: int = 30) -> pd.DataFrame:
        """获取历史行情"""
        conn = sqlite3.connect(self.db_path)
        
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        df = pd.read_sql_query('''
            SELECT * FROM realtime_quote 
            WHERE code = ? AND updated_at >= ?
            ORDER BY updated_at DESC
        ''', conn, params=(code, start_date))
        
        conn.close()
        return df
    
    # ==================== 批量采集 ====================
    
    def collect_all_realtime(self):
        """采集全市场实时行情"""
        self.logger.info('=== Starting full market collection ===')
        
        # 东方财富
        df = self.get_realtime_quotes_eastmoney()
        if not df.empty:
            self.save_realtime_quotes(df)
        
        self.logger.info('=== Full market collection completed ===')
        return df
    
    def collect_stocks_klines(self, codes: List[str]):
        """批量采集K线数据"""
        for code in codes:
            df = self.get_kline_eastmoney(code)
            if not df.empty:
                self.save_klines(df)
            time.sleep(0.5)  # 避免请求过快
        
        self.logger.info(f'Collected klines for {len(codes)} stocks')


def main():
    """测试运行"""
    import os
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    collector = DataCollector()
    
    # 测试采集
    df = collector.collect_all_realtime()
    print(f'\nCollected {len(df)} stocks')
    
    if not df.empty:
        print('\nTop 5 by change:')
        print(df.nlargest(5, 'change_pct')[['code', 'name', 'price', 'change_pct']])


if __name__ == '__main__':
    main()
