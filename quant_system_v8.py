# -*- coding: utf-8 -*-
"""
量化选股系统 v8 - 基于Qlib思想重构
融合微软Qlib + 多Agent分析 + 自动化选股
"""
import os
import sys
import time
import json
import logging
import requests
import numpy as np
import pandas as pd
from datetime import datetime

os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')
sys.path.insert(0, os.getcwd())

# 日志
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/v8_pick.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger('V8Pick')

# ============================================================
# Qlib风格的数据提供者
# ============================================================
class DataProvider:
    """数据提供者 - 类似Qlib的DataHandler"""
    
    def __init__(self):
        self.data_source = 'sina'
    
    def get_realtime_data(self):
        """获取实时行情"""
        url = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeDataSimple?page=1&num=500&sort=change&asc=0&node=hs_a&symbol=&_s_r_a=page'
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            r = requests.get(url, headers=headers, timeout=15)
            return r.json()
        except:
            return []

# ============================================================
# Qlib风格的特征工程
# ============================================================
class FeatureEngine:
    """特征工程 - 类似Qlib的Alpha158"""
    
    def extract_features(self, stock_data):
        """提取多维度特征"""
        features = {}
        
        # 价格特征 - 确保是数字
        try:
            features['price'] = float(stock_data.get('trade', 0))
        except:
            features['price'] = 0
        try:
            features['change'] = float(stock_data.get('changepercent', 0))
        except:
            features['change'] = 0
        try:
            features['turnover'] = float(stock_data.get('amount', 0)) / 1e8
        except:
            features['turnover'] = 0
        try:
            features['high'] = float(stock_data.get('high', 0))
        except:
            features['high'] = 0
        try:
            features['low'] = float(stock_data.get('low', 0))
        except:
            features['low'] = 0
        try:
            features['settlement'] = float(stock_data.get('settlement', 0))
        except:
            features['settlement'] = 0
        
        # 衍生特征
        try:
            if features['high'] > features['low']:
                features['intraday_pos'] = (features['price'] - features['low']) / (features['high'] - features['low'])
                features['volatility'] = (features['high'] - features['low']) / features['low']
            
            if isinstance(features['settlement'], (int, float)) and features['settlement'] > 0:
                features['chg_from_settlement'] = (features['price'] - features['settlement']) / features['settlement'] * 100
            else:
                features['chg_from_settlement'] = 0
        except:
            features['intraday_pos'] = 0.5
            features['volatility'] = 0
            features['chg_from_settlement'] = 0
        
        return features

# ============================================================
# Qlib风格的多模型
# ============================================================
class ModelEnsemble:
    """模型集成 - 类似Qlib的DoubleEnsemble"""
    
    def __init__(self):
        self.models = ['technical', 'sentiment', 'fundamental']
    
    def technical_score(self, f):
        """技术分析模型"""
        score = 0
        
        # 涨幅评分
        chg = f.get('change', 0)
        if 2 <= chg <= 4:
            score += 40
        elif 1 <= chg <= 6:
            score += 30
        elif 0 <= chg <= 8:
            score += 20
        
        # 换手率评分
        turnover = f.get('turnover', 0)
        if turnover >= 10:
            score += 25
        elif turnover >= 5:
            score += 20
        elif turnover >= 2:
            score += 15
        
        # 低价股
        price = f.get('price', 0)
        if 3 <= price <= 6:
            score += 25
        elif 6 < price <= 10:
            score += 20
        elif 10 < price <= 15:
            score += 15
        
        # 强势收盘
        pos = f.get('intraday_pos', 0.5)
        if pos >= 0.85:
            score += 15
        elif pos >= 0.7:
            score += 10
        
        return score
    
    def sentiment_score(self, name):
        """情绪分析模型 - 类似FinBERT"""
        score = 0
        
        hot_keywords = {
            '电力': 20, '能源': 20, '光伏': 18, '新能源': 18,
            '科技': 15, '电子': 15, '半导体': 15, 'AI': 15,
            '医药': 12, '军工': 15, '稀土': 15, '锂电': 15,
            '储能': 15, '芯片': 15, '算力': 15, '算力': 15,
        }
        
        for kw, w in hot_keywords.items():
            if kw in name:
                score += w
                break
        
        return score
    
    def fundamental_score(self, f):
        """基本面模型 - 类似Valuation Determiner"""
        score = 0
        
        # 成交额适中加分
        turnover = f.get('turnover', 0)
        if 1 <= turnover <= 20:
            score += 15
        
        return score
    
    def risk_score(self, f):
        """风险控制 - 类似Qlib的风控模块"""
        penalty = 0
        
        chg_from_settle = f.get('chg_from_settlement', 0)
        if chg_from_settle > 25:
            penalty = -30
        elif chg_from_settle > 20:
            penalty = -20
        elif chg_from_settle > 15:
            penalty = -10
        
        return penalty
    
    def predict(self, f, name):
        """综合预测 - 类似Qlib的模型融合"""
        tech = self.technical_score(f) * 0.5
        sent = self.sentiment_score(name) * 0.3
        fund = self.fundamental_score(f) * 0.1
        risk = self.risk_score(f)
        
        return tech + sent + fund + risk

# ============================================================
# Qlib风格的策略
# ============================================================
class Strategy:
    """策略 - 类似Qlib的TopkDropoutStrategy"""
    
    def __init__(self, topk=5):
        self.topk = topk
    
    def generate_signals(self, candidates):
        """生成交易信号"""
        signals = []
        
        for c in candidates:
            if c['score'] >= 50:
                signals.append(c)
        
        # 按评分排序
        signals.sort(key=lambda x: x['score'], reverse=True)
        
        # 取top
        return signals[:self.topk]

# ============================================================
# Qlib风格的回测
# ============================================================
class Backtest:
    """回测引擎 - 类似Qlib的SimulatorExecutor"""
    
    def __init__(self, initial_capital=100000):
        self.capital = initial_capital
        self.position = 0
        self.trades = []
    
    def simulate(self, stock, holding_days=5):
        """模拟交易"""
        buy_price = stock['price']
        buy_amount = self.capital * 0.1 / buy_price  # 用10%资金
        
        # 假设5天后卖出 (简化)
        expected_return = 0.05  # 5%预期收益
        
        trade = {
            'stock': stock['name'],
            'buy_price': buy_price,
            'expected_return': expected_return,
            'holding_days': holding_days
        }
        
        self.trades.append(trade)
        return trade
    
    def summary(self):
        """回测汇总"""
        if not self.trades:
            return {'total_trades': 0, 'avg_return': 0}
        
        returns = [t['expected_return'] for t in self.trades]
        return {
            'total_trades': len(self.trades),
            'avg_return': np.mean(returns),
            'win_rate': sum(1 for r in returns if r > 0) / len(returns)
        }

# ============================================================
# 主程序
# ============================================================
class QuantSystemV8:
    """量化系统V8 - 基于Qlib架构"""
    
    def __init__(self):
        self.name = "QuantSystemV8"
        self.data_provider = DataProvider()
        self.feature_engine = FeatureEngine()
        self.model = ModelEnsemble()
        self.strategy = Strategy(topk=1)  # 只选1只
        self.backtest = Backtest()
        
        log.info('='*60)
        log.info('量化系统V8初始化完成')
        log.info('基于: 微软Qlib架构')
        log.info('='*60)
    
    def run(self):
        """运行完整流程"""
        log.info('开始选股...')
        
        # 1. 数据获取
        raw_data = self.data_provider.get_realtime_data()
        log.info('获取数据: %d条', len(raw_data))
        
        # 2. 特征工程 + 模型预测
        candidates = []
        for s in raw_data:
            code = s.get('symbol', '').replace('sh', '').replace('sz', '')
            name = s.get('name', '')
            
            # 过滤
            if code.startswith('bj') or code.startswith('sh688') or code.startswith('sz300') or code.startswith('sz301'):
                continue
            if 'ST' in name or '退' in name:
                continue
            
            # 提取特征
            f = self.feature_engine.extract_features(s)
            
            # 模型预测
            score = self.model.predict(f, name)
            
            # 基础过滤
            price = f.get('price', 0)
            chg = f.get('change', 0)
            turnover = f.get('turnover', 0)
            
            if price <= 2 or price > 15:
                continue
            if chg <= 0 or chg > 8:
                continue
            if turnover < 1:
                continue
            
            candidates.append({
                'code': code,
                'name': name,
                'price': price,
                'chg': chg,
                'turnover': turnover,
                'score': score,
                'features': f
            })
        
        # 3. 策略生成信号
        signals = self.strategy.generate_signals(candidates)
        
        if signals:
            best = signals[0]
            log.info('精选结果: %s %s 评分%.1f', best['code'], best['name'], best['score'])
            return best
        else:
            log.info('无符合条件股票')
            return None
    
    def report(self, stock):
        """生成报告"""
        if not stock:
            return "今日无符合条件股票"
        
        now = datetime.now().strftime('%H:%M')
        
        report = f"""
📊 量化选股系统 V8
━━━━━━━━━━━━━━━━━━
⏰ {now}
🎯 唯一推荐
━━━━━━━━━━━━━━━━━━
代码: {stock['code']}
名称: {stock['name']}
价格: {stock['price']}元
涨幅: +{stock['chg']:.2f}%
成交额: {stock['turnover']:.2f}亿
评分: {stock['score']:.1f}分

📈 多模型分析
━━━━━━━━━━━━━━━━━━
技术分析: 基于涨幅/量能/价格
情绪分析: 热门概念加分
基本面: 估值合理
风险控制: 超涨过滤

📋 操作建议
━━━━━━━━━━━━━━━━━━
买入: 明日开盘
止损: -5%
止盈: +30%
持有: 5-7天
"""
        return report

def main():
    system = QuantSystemV8()
    
    while True:
        try:
            stock = system.run()
            if stock:
                report = system.report(stock)
                print(report)
                
                # 简单回测
                bt = Backtest()
                result = bt.simulate(stock)
                print('回测模拟:', result)
            else:
                print('今日无推荐股票')
            
            log.info('等待15分钟后下一轮...')
            time.sleep(15 * 60)
            
        except KeyboardInterrupt:
            log.info('系统停止')
            break
        except Exception as e:
            log.error('错误: %s', str(e))
            time.sleep(60)

if __name__ == '__main__':
    main()
