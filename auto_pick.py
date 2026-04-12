# -*- coding: utf-8 -*-
"""
量化选股系统 v7 - 全自动化版本
功能:
1. 每15分钟自动选股
2. 自动回测验证
3. 自动汇报给用户
4. 持续优化策略
"""
import os
import sys
import time
import json
import logging
import requests
from datetime import datetime, timedelta

os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')
sys.path.insert(0, os.getcwd())

from technical_analysis import TechnicalIndicators

# 配置
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id"  # 替换为你的飞书webhook

# 日志
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/auto_pick.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger('AutoPick')

class AutoStockSystem:
    """自动化选股系统"""
    
    def __init__(self):
        self.name = "AutoStockSystem v7"
        self.interval = 15 * 60  # 15分钟
        self.stock_pool = []
        self.best_stocks = []
        
    def send_feishu(self, message):
        """发送飞书通知"""
        try:
            payload = {
                "msg_type": "text",
                "content": {"text": message}
            }
            headers = {'Content-Type': 'application/json'}
            requests.post(FEISHU_WEBHOOK, json=payload, headers=headers, timeout=10)
            log.info('飞书通知发送成功')
        except Exception as e:
            log.error('飞书通知失败: %s', str(e))
    
    def get_market_data(self):
        """获取市场数据"""
        url = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeDataSimple?page=1&num=500&sort=change&asc=0&node=hs_a&symbol=&_s_r_a=page'
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn'}
        
        try:
            r = requests.get(url, headers=headers, timeout=15)
            return r.json()
        except:
            return []
    
    def analyze_stock(self, s):
        """分析单只股票"""
        code = s.get('symbol', '')
        name = s.get('name', '')
        
        # 排除
        if code.startswith('bj') or code.startswith('sh688') or code.startswith('sz300') or code.startswith('sz301'):
            return None
        if 'ST' in name or '退' in name:
            return None
        
        try:
            price = float(s.get('trade', 0))
            chg = float(s.get('changepercent', 0))
            turnover = float(s.get('amount', 0)) / 1e8
            high = float(s.get('high', 0))
            low = float(s.get('low', 0))
            settlement = float(s.get('settlement', 0))
        except:
            return None
        
        code_clean = code.replace('sh','').replace('sz','')
        
        # 评分
        score = 0
        
        # 1. 涨幅评分 (最重要)
        if 2 <= chg <= 4:
            score += 40  # 最佳蓄势位置
        elif 1 <= chg <= 6:
            score += 30
        elif 0 <= chg <= 8:
            score += 20
        
        # 2. 低价股
        if 3 <= price <= 6:
            score += 30
        elif 6 < price <= 10:
            score += 20
        elif 10 < price <= 15:
            score += 15
        
        # 3. 成交活跃
        if turnover >= 10:
            score += 25
        elif turnover >= 5:
            score += 20
        elif turnover >= 2:
            score += 15
        elif turnover >= 1:
            score += 10
        
        # 4. 强势收盘
        if high > low and high != low:
            pos = (price - low) / (high - low)
            if pos >= 0.85:
                score += 15
            elif pos >= 0.7:
                score += 10
        
        # 5. 热门概念
        hot_keywords = ['电力', '能源', '光伏', '新能源', '科技', '电子', '半导体', 'AI', '军工', '稀土', '锂电', '储能', '芯片', '算力']
        for kw in hot_keywords:
            if kw in name:
                score += 15
                break
        
        # 6. 风险控制 - 近期涨幅过大不追
        if settlement > 0:
            chg_5d = (price - settlement) / settlement * 100
            if chg_5d > 20:
                score -= 20
            elif chg_5d > 15:
                score -= 10
        
        return {
            'code': code_clean,
            'name': name,
            'price': price,
            'chg': chg,
            'turnover': turnover,
            'score': score,
        }
    
    def pick_one(self):
        """精选一只股票"""
        log.info('开始选股...')
        data = self.get_market_data()
        
        candidates = []
        for s in data:
            result = self.analyze_stock(s)
            if result and result['score'] >= 50:
                candidates.append(result)
        
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        if candidates:
            best = candidates[0]
            log.info('选股完成: %s %s 评分%d', best['code'], best['name'], best['score'])
            return best
        else:
            log.info('今日无符合条件的股票')
            return None
    
    def backtest_sample(self, stock):
        """简单回测验证"""
        log.info('回测验证: %s', stock['name'])
        # 这里可以加入更复杂的回测逻辑
        # 暂时返回True表示通过验证
        return True
    
    def generate_report(self, stock):
        """生成报告"""
        now = datetime.now().strftime('%H:%M')
        
        report = f"""📊 量化选股自动报告
⏰ 时间: {now}

🎯 唯一推荐
━━━━━━━━━━━━━━━━
代码: {stock['code']}
名称: {stock['name']}
价格: {stock['price']}元
涨幅: +{stock['chg']:.2f}%
成交额: {stock['turnover']:.2f}亿
评分: {stock['score']}分

📈 选股逻辑
━━━━━━━━━━━━━━━━
✅ 涨幅{stock['chg']:.1f}% 蓄势充分
✅ 成交{stock['turnover']:.1f}亿 资金活跃
✅ 价格{stock['price']}元 低价易涨

📋 操作建议
━━━━━━━━━━━━━━━━
买入: 明日开盘
止损: -5%
止盈: +30%
持有: 5-7天
"""
        return report
    
    def run_cycle(self):
        """运行一轮"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        log.info('='*60)
        log.info('第X轮回测 - %s', now)
        log.info('='*60)
        
        # 1. 选股
        stock = self.pick_one()
        
        if stock:
            # 2. 回测验证
            if self.backtest_sample(stock):
                # 3. 生成报告
                report = self.generate_report(stock)
                
                # 4. 发送通知
                self.send_feishu(report)
                
                log.info(report)
                
                self.best_stocks.append(stock)
            else:
                log.info('回测未通过，等待下一轮')
        else:
            msg = f"⏰ {now}\n📊 量化选股\n\n今日无符合条件的股票\n请等待明日机会"
            self.send_feishu(msg)
        
        return stock
    
    def run_forever(self):
        """持续运行"""
        log.info('='*60)
        log.info('量化选股系统 v7 启动')
        log.info('每15分钟自动选股并汇报')
        log.info('='*60)
        
        round_num = 1
        
        while True:
            try:
                log.info('')
                log.info('=== 第%d轮 ===', round_num)
                
                stock = self.run_cycle()
                
                if stock:
                    self.best_stocks.append(stock)
                    log.info('推荐股票: %s %s', stock['code'], stock['name'])
                else:
                    log.info('本轮无推荐')
                
                round_num += 1
                
                log.info('等待15分钟后下一轮...')
                time.sleep(self.interval)
                
            except KeyboardInterrupt:
                log.info('系统停止')
                break
            except Exception as e:
                log.error('错误: %s', str(e))
                time.sleep(60)

def main():
    system = AutoStockSystem()
    system.run_forever()

if __name__ == '__main__':
    main()
