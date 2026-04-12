# -*- coding: utf-8 -*-
"""
每日工作流程脚本
Daily Workflow Script - 自动化量化工作流
"""
import os
import sys
import json
import logging
from datetime import datetime, time
from typing import Dict, List

# 设置编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_workflow.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DailyWorkflow')


class DailyWorkflow:
    """每日工作流程"""
    
    def __init__(self):
        self.date = datetime.now().strftime('%Y-%m-%d')
        self.results = {}
    
    def run_morning_pick(self) -> Dict:
        """早盘选股"""
        logger.info("="*60)
        logger.info("【早盘选股】开始")
        logger.info("="*60)
        
        try:
            # 直接使用requests获取数据
            import requests
            
            # 上证A股
            url1 = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:1+t:2,m:1+t:23&fields=f12,f14,f2,f3,f5,f6,f8,f20,f23,f24'
            # 深证A股
            url2 = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=500&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80&fields=f12,f14,f2,f3,f5,f6,f8,f20,f23,f24'
            
            headers = {'User-Agent': 'Mozilla/5.0'}
            all_stocks = []
            
            for url in [url1, url2]:
                try:
                    resp = requests.get(url, headers=headers, timeout=15)
                    data = resp.json()
                    all_stocks.extend(data['data']['diff'])
                except:
                    pass
            
            # 筛选
            candidates = []
            for s in all_stocks:
                code = s['f12']
                name = s['f14']
                
                # 排除
                if code.startswith('688') or code.startswith('300') or code.startswith('8') or code.startswith('4'):
                    continue
                if 'ST' in name or '退' in name:
                    continue
                
                try:
                    price = float(s['f2']) if s['f2'] != '-' else 0
                    chg = float(s['f3']) if s['f3'] != '-' else 0
                    mv = float(s['f20']) / 1e8 if s['f20'] != '-' else 0
                    turnover = float(s['f8']) if s['f8'] != '-' else 0
                except:
                    continue
                
                # 放宽条件
                if price <= 2 or price > 50:
                    continue
                if chg < -3 or chg > 10:
                    continue
                if mv < 20 or mv > 200:
                    continue
                if turnover < 2:
                    continue
                
                # 评分
                score = 0
                if 4 <= chg <= 8: score += 30
                elif 2 <= chg <= 9: score += 20
                else: score += 10
                
                if turnover >= 8: score += 30
                elif turnover >= 5: score += 25
                elif turnover >= 3: score += 20
                else: score += 5
                
                candidates.append({
                    'code': code,
                    'name': name,
                    'price': price,
                    'change_pct': chg,
                    'market_cap': mv,
                    'turnover': turnover,
                    'score': score
                })
            
            # 排序
            candidates.sort(key=lambda x: x['score'], reverse=True)
            
            # TOP 5
            top5 = candidates[:5]
            
            self.results['morning_pick'] = {
                'total_scanned': len(all_stocks),
                'candidates': len(candidates),
                'top5': top5,
                'status': 'success'
            }
            
            logger.info(f"扫描: {len(all_stocks)}只, 符合条件: {len(candidates)}只")
            
            # 发送飞书通知
            self._notify_pick(top5)
            
            return self.results['morning_pick']
            
        except Exception as e:
            logger.error(f"早盘选股失败: {e}")
            self.results['morning_pick'] = {'status': 'error', 'message': str(e)}
            return self.results['morning_pick']
    
    def run_strategy_analysis(self) -> Dict:
        """策略组合分析"""
        logger.info("\n" + "="*60)
        logger.info("【策略组合分析】开始")
        logger.info("="*60)
        
        try:
            from strategy_ensemble import StrategyEnsemble
            
            ensemble = StrategyEnsemble()
            
            # 使用早盘选股结果
            if 'morning_pick' in self.results and self.results['morning_pick'].get('top5'):
                stocks = self.results['morning_pick']['top5']
            else:
                stocks = []
            
            # 分析组合
            analysis = ensemble.analyze_portfolio(stocks)
            
            self.results['strategy_analysis'] = {
                'top5': analysis['top5'],
                'avg_score': analysis['avg_score'],
                'strategy_consensus': analysis['strategy_consensus'],
                'status': 'success'
            }
            
            logger.info(f"组合评分: {analysis['avg_score']:.1f}")
            
            return self.results['strategy_analysis']
            
        except Exception as e:
            logger.error(f"策略分析失败: {e}")
            self.results['strategy_analysis'] = {'status': 'error', 'message': str(e)}
            return self.results['strategy_analysis']
    
    def run_stop_loss_check(self) -> Dict:
        """止损检查"""
        logger.info("\n" + "="*60)
        logger.info("【止损检查】")
        logger.info("="*60)
        
        try:
            from stop_loss import StopLossStrategy
            
            stop_loss = StopLossStrategy()
            
            # 检查持仓 (模拟)
            positions = []  # 实际应从数据库读取
            
            stop_suggestions = []
            for pos in positions:
                # 计算止损价格
                stop_prices = stop_loss.calculate_stop_price(pos['buy_price'])
                stop_suggestions.append({
                    'code': pos['code'],
                    'name': pos['name'],
                    'buy_price': pos['buy_price'],
                    'stop_prices': stop_prices
                })
            
            self.results['stop_loss'] = {
                'positions_checked': len(positions),
                'stop_suggestions': stop_suggestions,
                'status': 'success'
            }
            
            logger.info(f"检查持仓: {len(positions)}只")
            
            return self.results['stop_loss']
            
        except Exception as e:
            logger.error(f"止损检查失败: {e}")
            self.results['stop_loss'] = {'status': 'error', 'message': str(e)}
            return self.results['stop_loss']
    
    def _notify_pick(self, picks: List[Dict]):
        """发送选股通知"""
        try:
            from feishu_notify import get_notifier
            
            notifier = get_notifier()
            
            # 构建消息
            date_str = self.date
            notifier.send_stock_pick(picks, date_str)
            
            logger.info("飞书通知已发送")
            
        except Exception as e:
            logger.warning(f"飞书通知失败: {e}")
    
    def save_results(self):
        """保存结果"""
        output_file = f'data/workflow_{self.date}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'date': self.date,
                'timestamp': datetime.now().isoformat(),
                'results': self.results
            }, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"\n结果已保存: {output_file}")
    
    def run(self):
        """运行完整流程"""
        print("\n" + "="*60)
        print(f"【每日工作流程】{self.date}")
        print("="*60)
        
        # 1. 早盘选股
        self.run_morning_pick()
        
        # 2. 策略组合分析
        self.run_strategy_analysis()
        
        # 3. 止损检查
        self.run_stop_loss_check()
        
        # 4. 保存结果
        self.save_results()
        
        # 5. 汇总
        print("\n" + "="*60)
        print("【工作流程完成】")
        print("="*60)
        
        for step, result in self.results.items():
            status = "✅" if result.get('status') == 'success' else "❌"
            print(f"  {status} {step}: {result.get('status', 'unknown')}")


def main():
    """主函数"""
    workflow = DailyWorkflow()
    workflow.run()


if __name__ == '__main__':
    main()
