# -*- coding: utf-8 -*-
"""
量化选股系统 - 全自动工作引擎
功能:
1. 持续收集市场数据
2. 不断优化选股策略
3. 每周选出最佳股票
4. 自动飞书通知汇报
"""
import os
import sys
import time
import json
import sqlite3
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging

os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')
sys.path.insert(0, os.getcwd())

DB_PATH = 'data/stocks.db'
os.makedirs('data', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/auto_engine.log', encoding='utf-8', mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger('AutoEngine')

# 飞书通知配置
FEISHU_WEBHOOK = os.environ.get('FEISHU_WEBHOOK', '')

class AutoEngine:
    """全自动工作引擎"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self.last_pick_date = None
        self.last_optimize_date = None
        self.current_strategy = {
            'holding_days': 21,
            'chg_range': (8, 15),
            'price_max': 15,
            'vol_ratio': 1.5
        }
        self.best_stocks = []
        self.init_db()
        
        log.info('='*60)
        log.info('量化系统全自动引擎启动')
        log.info('='*60)
    
    def init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS kline (
            code TEXT, date TEXT, name TEXT, open REAL, high REAL, low REAL,
            close REAL, volume REAL, amount REAL,
            UNIQUE(code, date))''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, code TEXT, name TEXT, price REAL,
            chg REAL, amount REAL, score REAL,
            holding_days INTEGER, result REAL, status TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS strategy_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, target_rate REAL, best_params TEXT,
            trades INTEGER, win_rate REAL, avg_return REAL)''')
        
        conn.commit()
        conn.close()
        log.info('数据库初始化完成')
    
    # ==================== 数据收集 ====================
    def collect_realtime_data(self):
        """实时采集市场数据"""
        log.info('开始采集实时数据...')
        
        url = 'https://push2.eastmoney.com/api/qt/clist/get?cb=jQuery&pn=1&pz=300&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16'
        
        try:
            r = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://quote.eastmoney.com/'
            }, timeout=15)
            
            text = r.text
            start = text.find('(') + 1
            end = text.rfind(')')
            data = json.loads(text[start:end])
            
            stocks = data['data']['diff']
            log.info('获取到 %d 只股票', len(stocks))
            
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            count = 0
            today = datetime.now().strftime('%Y-%m-%d')
            
            for s in stocks:
                try:
                    code = str(s.get('f12', ''))
                    name = str(s.get('f14', ''))
                    price = float(s.get('f2', 0))
                    chg = float(s.get('f3', 0))
                    amount = float(s.get('f6', 0)) / 1e8
                    volume = float(s.get('f5', 0))
                    
                    c.execute('''INSERT OR REPLACE INTO kline 
                                (code, name, date, close, volume, amount)
                                VALUES (?, ?, ?, ?, ?, ?)''',
                             (code, name, today, price, volume, amount))
                    count += 1
                except:
                    pass
            
            conn.commit()
            conn.close()
            
            log.info('更新 %d 只股票数据', count)
            return True
            
        except Exception as e:
            log.error('采集失败: %s', str(e))
            return False
    
    def collect_historical_kline(self, code):
        """采集单只股票历史K线"""
        market = '1' if code.startswith('6') else '0'
        end = datetime.now().strftime('%Y%m%d')
        start = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        
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
                                (code, date, open, close, high, low, volume, amount)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                             (code, parts[0], float(parts[1]), float(parts[2]),
                              float(parts[3]), float(parts[4]), float(parts[5]), float(parts[6])))
                
                conn.commit()
                conn.close()
                return len(klines)
        except:
            pass
        return 0
    
    def collect_more_stocks(self, target=200):
        """收集更多股票数据"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(DISTINCT code) FROM kline WHERE date = ?',
                 (datetime.now().strftime('%Y-%m-%d'),))
        current = c.fetchone()[0]
        conn.close()
        
        if current >= target:
            log.info('股票数量已达标: %d/%d', current, target)
            return current
        
        log.info('收集更多股票数据: %d/%d', current, target)
        
        # 获取涨幅榜股票代码
        url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=200&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f12,f14'
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        
        try:
            text = r.text
            start = text.find('(') + 1
            end = text.rfind(')')
            data = json.loads(text[start:end])
            stocks = data['data']['diff']
            
            for s in stocks:
                code = s.get('f12', '')
                if code.startswith('688') or code.startswith('300'):
                    continue
                
                self.collect_historical_kline(code)
                time.sleep(0.3)
                
        except Exception as e:
            log.error('批量采集失败: %s', str(e))
        
        return current
    
    # ==================== 选股引擎 ====================
    def screen_stocks(self):
        """筛选候选股票"""
        log.info('开始筛选股票...')
        
        conn = sqlite3.connect(self.db_path)
        
        # 获取所有K线数据
        df = pd.read_sql('''SELECT code, date, close, volume, turnover as amount
                           FROM kline ORDER BY date DESC''',
                        conn)
        conn.close()
        
        if df.empty:
            log.warning('无数据，跳过筛选')
            return []
        
        candidates = []
        
        for code in df['code'].unique()[:200]:
            stock_df = df[df['code'] == code].sort_values('date')
            
            if len(stock_df) < 30:
                continue
            
            try:
                # 获取基本信息
                name = stock_df.iloc[-1].get('name', code)
                if 'ST' in str(name) or '*' in str(name):
                    continue
                
                # 排除创业板、科创板
                if code.startswith('688') or code.startswith('300') or code.startswith('8'):
                    continue
                
                today_data = stock_df.iloc[-1]
                price = today_data['close']
                
                # 计算各项指标
                closes = stock_df['close'].values
                volumes = stock_df['volume'].values
                
                # 昨日涨幅
                if len(closes) >= 2:
                    chg = (closes[-1] - closes[-2]) / closes[-2] * 100
                else:
                    chg = 0
                
                # 5日涨幅
                if len(closes) >= 6:
                    chg5 = (closes[-1] - closes[-6]) / closes[-6] * 100
                else:
                    chg5 = 0
                
                # 量比
                avg_vol = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
                vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 0
                
                # 评分
                score = self.calculate_score(chg, chg5, vol_ratio, price)
                
                if score >= 60:
                    candidates.append({
                        'code': code,
                        'name': name,
                        'price': price,
                        'chg': chg,
                        'chg5': chg5,
                        'vol_ratio': vol_ratio,
                        'score': score
                    })
                    
            except Exception as e:
                pass
        
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:20]
    
    def calculate_score(self, chg, chg5, vol_ratio, price):
        """计算评分"""
        score = 0
        
        # 涨幅评分
        if 3 <= chg <= 7:
            score += 35
        elif 1 <= chg <= 10:
            score += 25
        
        # 5日涨幅
        if 5 <= chg5 <= 12:
            score += 30
        elif 3 <= chg5 <= 15:
            score += 20
        
        # 量比
        if vol_ratio >= 2.0:
            score += 25
        elif vol_ratio >= 1.5:
            score += 20
        
        # 价格
        if 3 <= price <= 10:
            score += 15
        elif 10 < price <= 15:
            score += 10
        
        return score
    
    # ==================== 通知系统 ====================
    def send_feishu(self, message):
        """发送飞书通知"""
        if not FEISHU_WEBHOOK:
            log.info('飞书Webhook未配置，跳过通知')
            return False
        
        try:
            payload = {
                'msg_type': 'text',
                'content': {'text': message}
            }
            r = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
            return r.status_code == 200
        except Exception as e:
            log.error('飞书通知失败: %s', str(e))
            return False
    
    def notify_pick(self, stock):
        """通知选股结果"""
        msg = f"""📊 量化选股报告
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}

🎯 唯一推荐
━━━━━━━━━━━━━━━━
代码: {stock['code']}
名称: {stock['name']}
价格: {stock['price']:.2f}元
涨幅: {stock['chg']:+.2f}%
5日涨幅: {stock['chg5']:+.2f}%
量比: {stock['vol_ratio']:.2f}x
评分: {stock['score']:.0f}分

📈 操作建议
━━━━━━━━━━━━━━━━
持有: 5-7天
止损: -5%
目标: +20%

⚠️ 风险自负，仅供参考"""
        
        log.info('发送飞书通知...')
        self.send_feishu(msg)
    
    def notify_status(self, status):
        """通知系统状态"""
        msg = f"""🔧 量化系统状态
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}
{status}"""
        self.send_feishu(msg)
    
    # ==================== 主循环 ====================
    def run(self):
        """主循环"""
        log.info('开始全自动工作...')
        
        round_count = 0
        
        while True:
            round_count += 1
            now = datetime.now()
            
            log.info('')
            log.info('='*60)
            log.info('第 %d 轮工作', round_count)
            log.info('时间: %s', now.strftime('%Y-%m-%d %H:%M:%S'))
            log.info('='*60)
            
            try:
                # 1. 采集数据
                self.collect_realtime_data()
                self.collect_more_stocks(200)
                
                # 2. 选股
                candidates = self.screen_stocks()
                
                if candidates:
                    best = candidates[0]
                    log.info('最佳候选: %s %s 评分%.0f',
                            best['code'], best['name'], best['score'])
                    
                    # 如果是新股，发送通知
                    if self.last_pick_date != now.strftime('%Y-%m-%d'):
                        self.notify_pick(best)
                        self.last_pick_date = now.strftime('%Y-%m-%d')
                    
                    # 保存到数据库
                    conn = sqlite3.connect(self.db_path)
                    c = conn.cursor()
                    c.execute('''INSERT INTO picks 
                                (date, code, name, price, chg, score, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                             (now.strftime('%Y-%m-%d'), best['code'], best['name'],
                              best['price'], best['chg'], best['score'], '持有中'))
                    conn.commit()
                    conn.close()
                    
                    self.best_stocks = candidates[:5]
                
                # 3. 定期优化
                if self.last_optimize_date is None or \
                   (now - datetime.strptime(self.last_optimize_date, '%Y-%m-%d')).days >= 7:
                    self.optimize_strategy()
                    self.last_optimize_date = now.strftime('%Y-%m-%d')
                
                log.info('本轮完成，等待下一轮...')
                
            except Exception as e:
                log.error('执行出错: %s', str(e))
            
            # 每15分钟运行一次
            time.sleep(15 * 60)

def main():
    engine = AutoEngine()
    engine.run()

if __name__ == '__main__':
    main()
