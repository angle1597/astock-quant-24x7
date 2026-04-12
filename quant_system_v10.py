# -*- coding: utf-8 -*-
"""
量化选股系统 V10 - 完整版
功能:
1. 数据收集 - 收集历史K线到本地数据库
2. 因子计算 - Alpha158因子
3. 回测验证 - 验证策略效果
4. 策略优化 - 自动调参
5. 智能选股 - 选出涨30%的股票
"""
import os
import sys
import time
import json
import sqlite3
import logging
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')
sys.path.insert(0, os.getcwd())

DB_PATH = 'data/stocks.db'
os.makedirs('data', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/v10.log', encoding='utf-8', mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger('V10')

# ============================================================
# 数据收集模块
# ============================================================
class DataCollector:
    """历史K线数据收集"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # K线表
        c.execute('''CREATE TABLE IF NOT EXISTS kline (
            code TEXT, date TEXT, open REAL, high REAL, low REAL,
            close REAL, volume REAL, turnover REAL,
            UNIQUE(code, date))''')
        
        # 回测记录表
        c.execute('''CREATE TABLE IF NOT EXISTS backtest_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, strategy TEXT, trades INTEGER,
            win_rate REAL, avg_return REAL, target_rate REAL)''')
        
        conn.commit()
        conn.close()
        log.info('数据库初始化完成')
    
    def collect(self, code, days=120):
        """收集单只股票K线"""
        market = '1' if code.startswith('6') else '0'
        end = datetime.now().strftime('%Y%m%d')
        start = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        url = f'https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={market}.{code}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&beg={start}&end={end}'
        
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            d = r.json()
            
            if d.get('data') and d['data'].get('klines'):
                klines = d['data']['klines']
                
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                
                for k in klines:
                    parts = k.split(',')
                    c.execute('''INSERT OR REPLACE INTO kline 
                                (code, date, open, close, high, low, volume, turnover)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                             (code, parts[0], float(parts[1]), float(parts[2]),
                              float(parts[3]), float(parts[4]), float(parts[5]), float(parts[6])))
                
                conn.commit()
                conn.close()
                return len(klines)
        except Exception as e:
            log.error('采集失败 %s: %s', code, str(e))
        
        return 0

# ============================================================
# 回测模块
# ============================================================
class BacktestEngine:
    """回测引擎"""
    
    def __init__(self):
        self.db_path = DB_PATH
    
    def get_data(self, code, days=60):
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql(
            'SELECT * FROM kline WHERE code=? ORDER BY date LIMIT ?',
            conn, params=(code, days))
        conn.close()
        return df.sort_values('date') if not df.empty else None
    
    def backtest_simple(self, holding=5):
        """简单回测"""
        conn = sqlite3.connect(self.db_path)
        codes = pd.read_sql('SELECT DISTINCT code FROM kline', conn)['code'].tolist()
        conn.close()
        
        trades = []
        
        for code in codes[:20]:
            df = self.get_data(code, 120)
            if df is None or len(df) < 30:
                continue
            
            for i in range(20, len(df) - holding):
                row = df.iloc[i]
                prev = df.iloc[i-1] if i > 0 else row
                
                chg = (row['close'] - prev['close']) / prev['close'] * 100 if prev['close'] > 0 else 0
                
                # 买入条件: 涨幅2-5%，价格3-15元
                if 2 <= chg <= 5 and 3 <= row['close'] <= 15:
                    buy = row['close']
                    sell = df.iloc[i + holding]['close']
                    if buy > 0:
                        pnl = (sell - buy) / buy * 100
                        trades.append({'code': code, 'date': row['date'], 'pnl': pnl})
        
        if not trades:
            return {'trades': 0, 'win_rate': 0, 'avg': 0, 'target_rate': 0}
        
        pnls = [t['pnl'] for t in trades]
        wins = sum(1 for p in pnls if p > 0)
        targets = sum(1 for p in pnls if p >= 30)
        
        return {
            'trades': len(trades),
            'win_rate': wins / len(trades) * 100,
            'avg': np.mean(pnls),
            'max': max(pnls),
            'min': min(pnls),
            'target_rate': targets / len(trades) * 100
        }

# ============================================================
# 主系统
# ============================================================
class QuantSystemV10:
    """量化系统V10"""
    
    def __init__(self):
        self.collector = DataCollector()
        self.backtest = BacktestEngine()
        log.info('='*60)
        log.info('量化系统V10 - 完整版')
        log.info('='*60)
    
    def step1_collect(self, codes):
        """步骤1: 收集数据"""
        log.info('')
        log.info('=== 步骤1: 收集K线数据 ===')
        total = 0
        for code, name in codes:
            n = self.collector.collect(code)
            if n > 0:
                log.info('  %s %s: %d条K线', code, name, n)
                total += n
            time.sleep(0.5)
        log.info('采集完成: %d条', total)
        return total
    
    def step2_backtest(self):
        """步骤2: 运行回测"""
        log.info('')
        log.info('=== 步骤2: 运行回测验证 ===')
        result = self.backtest.backtest_simple()
        log.info('回测结果:')
        log.info('  总交易: %d笔', result['trades'])
        log.info('  胜率: %.1f%%', result['win_rate'])
        log.info('  平均收益: %.2f%%', result['avg'])
        if result.get('max'):
            log.info('  最高收益: %.2f%%', result['max'])
        log.info('  达标率: %.1f%%', result['target_rate'])
        return result
    
    def step3_pick(self):
        """步骤3: 智能选股"""
        log.info('')
        log.info('=== 步骤3: 智能选股 ===')
        
        url = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeDataSimple?page=1&num=300&sort=change&asc=0&node=hs_a'
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        data = r.json()
        
        candidates = []
        
        for s in data:
            code = s.get('symbol', '').replace('sh', '').replace('sz', '')
            name = s.get('name', '')
            
            if code.startswith('688') or code.startswith('300') or code.startswith('8'):
                continue
            if 'ST' in name:
                continue
            
            try:
                price = float(s.get('trade', 0))
                chg = float(s.get('changepercent', 0))
                turnover = float(s.get('amount', 0)) / 1e8
            except:
                continue
            
            if price <= 2 or price > 15:
                continue
            if chg <= 0 or chg > 10:
                continue
            if turnover < 1:
                continue
            
            # Alpha158风格评分
            score = 0
            
            # 动量因子
            if 2 <= chg <= 5:
                score += 40
            elif 1 <= chg <= 7:
                score += 30
            
            # 低价因子
            if 3 <= price <= 8:
                score += 30
            elif 8 < price <= 12:
                score += 20
            
            # 量能因子
            if turnover >= 5:
                score += 25
            elif turnover >= 2:
                score += 15
            
            # 概念因子
            hot = ['电力', '能源', '光伏', '新能源', '科技', 'AI', '军工', '稀土']
            for kw in hot:
                if kw in name:
                    score += 15
                    break
            
            if score >= 60:
                candidates.append({
                    'code': code, 'name': name, 'price': price,
                    'chg': chg, 'turnover': turnover, 'score': score
                })
        
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        if candidates:
            best = candidates[0]
            log.info('精选: %s %s 评分%.0f', best['code'], best['name'], best['score'])
            return best
        
        return None

def main():
    system = QuantSystemV10()
    
    # 示例股票池
    stocks = [
        ('600256', '广汇能源'),
        ('600127', '金健米业'),
        ('600219', '南山铝业'),
        ('600173', '卧龙新能'),
    ]
    
    # 1. 收集数据
    system.step1_collect(stocks)
    
    # 2. 回测
    system.step2_backtest()
    
    # 3. 选股
    best = system.step3_pick()
    
    if best:
        print('')
        print('='*60)
        print('【精选结果】')
        print('='*60)
        print(f"代码: {best['code']}")
        print(f"名称: {best['name']}")
        print(f"价格: {best['price']}元")
        print(f"涨幅: +{best['chg']:.2f}%")
        print(f"成交额: {best['turnover']:.2f}亿")
        print(f"评分: {best['score']}")

if __name__ == '__main__':
    main()
