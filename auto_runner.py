# -*- coding: utf-8 -*-
"""
A股24/7自动化运行器
Auto Runner - 24/7 Stock Analysis System
"""

import os
import sys
import time
import logging
import json
from datetime import datetime, timedelta
from threading import Thread, Event
from typing import List, Dict, Optional
import schedule
import random

# 导入本地模块
from data_collector import DataCollector

# 配置日志
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('reports', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('logs/auto_runner.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AutoRunner')

# 全局状态
STOP_EVENT = Event()
SYSTEM_STATE = {
    'start_time': None,
    'last_run': {},
    'pick_count': 0,
    'error_count': 0,
    'is_trading_day': False,
    'market_status': 'closed'  # closed, pre_open, trading, after_close
}


class StockPicker:
    """选股器"""
    
    def __init__(self, collector: DataCollector):
        self.collector = collector
        self.criteria = self._load_criteria()
    
    def _load_criteria(self) -> Dict:
        """加载选股条件"""
        return {
            'price_min': 0.1,
            'price_max': 30,
            'mv_min': 30,  # 亿
            'mv_max': 150,
            'pe_max': 50,
            'exclude_boards': ['688', '300', '8', '4', 'ST'],  # 科创板, 创业板, 北交所
        }
    
    def screen_stocks(self, df) -> List[Dict]:
        """筛选股票"""
        if df.empty:
            return []
        
        criteria = self.criteria
        results = []
        
        for _, row in df.iterrows():
            try:
                code = str(row.get('code', ''))
                name = str(row.get('name', ''))
                price = float(row.get('price', 0))
                change_pct = float(row.get('change_pct', 0))
                vr = float(row.get('vr', 0))
                turnover = float(row.get('turnover', 0))
                pe = float(row.get('pe', 0))
                pb = float(row.get('pb', 0))
                mv = float(row.get('mv', 0)) / 1e8  # 转为亿
                
                # 过滤条件
                if not code:
                    continue
                
                # 板块过滤
                if any(ex in code for ex in criteria['exclude_boards'][:3]):
                    continue
                
                # ST过滤
                if 'ST' in name or '退' in name:
                    continue
                
                # 价格过滤
                if price <= criteria['price_min'] or price >= criteria['price_max']:
                    continue
                
                # 市值过滤
                if mv < criteria['mv_min'] or mv > criteria['mv_max']:
                    continue
                
                # PE过滤
                if pe > criteria['pe_max'] or pe < 0:
                    continue
                
                # 评分
                score = 0
                details = {}
                
                # 涨幅评分 (30分)
                if 3 <= change_pct < 6:
                    score += 20
                    details['change'] = '+20 (3-6%)'
                elif 6 <= change_pct < 10:
                    score += 30
                    details['change'] = '+30 (6-10%)'
                elif change_pct >= 10:
                    score += 25
                    details['change'] = '+25 (涨停附近)'
                elif 0 <= change_pct < 3:
                    score += 10
                    details['change'] = '+10 (0-3%)'
                
                # 量比评分 (30分)
                if vr >= 20:
                    score += 30
                    details['vr'] = '+30 (VR>=20)'
                elif vr >= 5:
                    score += 20
                    details['vr'] = '+20 (VR>=5)'
                elif vr >= 2:
                    score += 10
                    details['vr'] = '+10 (VR>=2)'
                
                # 换手率评分 (20分)
                if turnover >= 10:
                    score += 20
                    details['turnover'] = '+20 (>=10%)'
                elif turnover >= 5:
                    score += 15
                    details['turnover'] = '+15 (>=5%)'
                elif turnover >= 2:
                    score += 10
                    details['turnover'] = '+10 (>=2%)'
                
                # 估值评分 (20分)
                if 0 < pe <= 20:
                    score += 10
                    details['pe'] = '+10 (PE<=20)'
                if 0 < pb <= 3:
                    score += 10
                    details['pb'] = '+10 (PB<=3)'
                
                # 加入结果
                if score >= 50:
                    results.append({
                        'code': code,
                        'name': name,
                        'price': price,
                        'change_pct': change_pct,
                        'vr': vr,
                        'turnover': turnover,
                        'pe': pe,
                        'pb': pb,
                        'mv': round(mv, 1),
                        'score': score,
                        'details': details
                    })
            
            except Exception as e:
                logger.warning(f'Error processing row: {e}')
                continue
        
        # 按评分排序
        results.sort(key=lambda x: x['score'], reverse=True)
        return results


class StrategyOptimizer:
    """策略优化器"""
    
    def __init__(self, collector: DataCollector):
        self.collector = collector
    
    def backtest(self, picks: List[Dict], days: int = 5) -> Dict:
        """简单回测"""
        # 这里实现简单的回测逻辑
        # 实际应该根据历史K线计算收益
        
        results = {
            'total_picks': len(picks),
            'avg_score': sum(p['score'] for p in picks) / len(picks) if picks else 0,
            'picks': picks[:5]  # TOP5
        }
        
        return results
    
    def optimize_criteria(self) -> Dict:
        """优化选股条件"""
        # 根据历史表现调整参数
        # 这里只是示例
        
        return {
            'change_min': 3,
            'change_max': 10,
            'vr_min': 5,
            'turnover_min': 5,
            'pe_max': 30
        }


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self):
        self.report_dir = 'reports'
        os.makedirs(self.report_dir, exist_ok=True)
    
    def generate_daily_report(self, picks: List[Dict], market_data: Dict):
        """生成日报"""
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H:%M:%S')
        
        report = {
            'date': date_str,
            'time': time_str,
            'market_status': market_data.get('status', 'unknown'),
            'picks': picks,
            'summary': {
                'total': len(picks),
                'avg_score': sum(p['score'] for p in picks) / len(picks) if picks else 0
            }
        }
        
        # 保存JSON
        filename = f"{self.report_dir}/pick_{date_str.replace('-', '')}_{time_str.replace(':', '')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f'Report saved: {filename}')
        return report
    
    def generate_markdown_report(self, picks: List[Dict], market_data: Dict) -> str:
        """生成Markdown报告"""
        now = datetime.now()
        
        md = f"""# A股每日选股报告
Generated: {now.strftime('%Y-%m-%d %H:%M')}

## 市场状态
- 状态: {market_data.get('status', 'unknown')}
- 时间: {now.strftime('%H:%M:%S')}

## 选股结果
共筛选出 {len(picks)} 只符合条件的股票

| 排名 | 代码 | 名称 | 现价 | 涨幅 | 量比 | 换手 | 市盈率 | 评分 |
|------|------|------|------|------|------|------|--------|------|
"""
        
        for i, pick in enumerate(picks[:10], 1):
            md += f"| {i} | {pick['code']} | {pick['name']} | {pick['price']:.2f} | {pick['change_pct']:.2f}% | {pick['vr']:.1f} | {pick['turnover']:.1f}% | {pick['pe']:.1f} | {pick['score']} |\n"
        
        md += f"""
## TOP 3 推荐

1. **{picks[0]['code']} {picks[0]['name']}** - 评分 {picks[0]['score']}分
2. **{picks[1]['code']} {picks[1]['name']}** - 评分 {picks[1]['score']}分
3. **{picks[2]['code']} {picks[2]['name']}** - 评分 {picks[2]['score']}分

---
*Generated by Auto Stock Picker v3.0*
"""
        
        return md


class AutoRunner:
    """自动化运行器"""
    
    def __init__(self):
        self.collector = DataCollector()
        self.picker = StockPicker(self.collector)
        self.optimizer = StrategyOptimizer(self.collector)
        self.reporter = ReportGenerator()
        
        SYSTEM_STATE['start_time'] = datetime.now().isoformat()
    
    def check_market_status(self) -> str:
        """检查市场状态"""
        now = datetime.now()
        
        # 周末
        if now.weekday() >= 5:
            return 'weekend'
        
        hour = now.hour
        minute = now.minute
        
        # 9:15-9:30 集合竞价
        if hour == 9 and 15 <= minute <= 30:
            return 'pre_open'
        # 9:30-11:30 上午交易
        elif 9 < hour < 11 or (hour == 11 and minute <= 30):
            return 'trading'
        # 11:30-13:00 午休
        elif hour == 11 and minute > 30 or (hour == 12 and minute < 13):
            return 'lunch'
        # 13:00-15:00 下午交易
        elif 13 <= hour < 15:
            return 'trading'
        # 15:00后收盘
        else:
            return 'after_close'
    
    def run_morning_pick(self):
        """早盘选股"""
        logger.info('=== Running morning pick ===')
        
        try:
            # 采集数据
            df = self.collector.collect_all_realtime()
            
            if df.empty:
                logger.warning('No data collected')
                return
            
            # 筛选
            picks = self.picker.screen_stocks(df)
            
            # 生成报告
            market_data = {'status': self.check_market_status()}
            report = self.reporter.generate_daily_report(picks, market_data)
            
            # 打印TOP3
            logger.info('\n=== TOP 3 PICKS ===')
            for i, pick in enumerate(picks[:3], 1):
                logger.info(f"{i}. {pick['code']} {pick['name']} - Score: {pick['score']}")
            
            SYSTEM_STATE['last_run']['morning_pick'] = datetime.now().isoformat()
            SYSTEM_STATE['pick_count'] += 1
            
        except Exception as e:
            logger.error(f'Morning pick failed: {e}')
            SYSTEM_STATE['error_count'] += 1
    
    def run_monitoring(self):
        """盘中监控"""
        status = self.check_market_status()
        
        if status not in ['trading', 'pre_open']:
            return
        
        logger.info(f'=== Monitoring ({status}) ===')
        
        try:
            df = self.collector.collect_all_realtime()
            
            if df.empty:
                return
            
            picks = self.picker.screen_stocks(df)
            
            market_data = {'status': status}
            self.reporter.generate_daily_report(picks, market_data)
            
            # 只打印高评分变化
            high_score = [p for p in picks if p['score'] >= 80]
            if high_score:
                logger.info(f'Found {len(high_score)} high-score stocks')
                for p in high_score[:3]:
                    logger.info(f"  {p['code']} {p['name']}: {p['score']}pts")
            
            SYSTEM_STATE['last_run']['monitoring'] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f'Monitoring failed: {e}')
            SYSTEM_STATE['error_count'] += 1
    
    def run_evening_summary(self):
        """尾盘总结"""
        logger.info('=== Running evening summary ===')
        
        try:
            df = self.collector.collect_all_realtime()
            picks = self.picker.screen_stocks(df)
            
            market_data = {'status': 'after_close'}
            report = self.reporter.generate_daily_report(picks, market_data)
            
            # 生成Markdown报告
            md_report = self.reporter.generate_markdown_report(picks, market_data)
            
            md_file = f"reports/daily_{datetime.now().strftime('%Y%m%d')}.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(md_report)
            
            logger.info(f'Evening summary saved: {md_file}')
            
            SYSTEM_STATE['last_run']['evening_summary'] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f'Evening summary failed: {e}')
            SYSTEM_STATE['error_count'] += 1
    
    def run_weekly_backtest(self):
        """每周回测"""
        logger.info('=== Running weekly backtest ===')
        
        try:
            # 策略优化
            new_criteria = self.optimizer.optimize_criteria()
            
            # 保存优化结果
            with open('data/optimized_criteria.json', 'w', encoding='utf-8') as f:
                json.dump(new_criteria, f, ensure_ascii=False, indent=2)
            
            logger.info(f'Weekly backtest completed, new criteria: {new_criteria}')
            
        except Exception as e:
            logger.error(f'Weekly backtest failed: {e}')
            SYSTEM_STATE['error_count'] += 1
    
    def run_scheduler(self):
        """调度器"""
        # 每天9:20 早盘选股
        schedule.every().day.at("09:20").do(self.run_morning_pick)
        
        # 交易时段每30分钟监控
        for hour in range(9, 16):
            if hour == 9:
                schedule.every().day.at(f"{hour}:30").do(self.run_monitoring)
            elif 10 <= hour <= 14:
                schedule.every().day.at(f"{hour}:00").do(self.run_monitoring)
                schedule.every().day.at(f"{hour}:30").do(self.run_monitoring)
            elif hour == 15:
                schedule.every().day.at("15:05").do(self.run_evening_summary)
        
        # 每周日20:00 回测
        schedule.every().sunday.at("20:00").do(self.run_weekly_backtest)
        
        # 每小时数据采集
        schedule.every().hour.do(self.collector.collect_all_realtime)
        
        logger.info('Scheduler started')
        
        while not STOP_EVENT.is_set():
            schedule.run_pending()
            time.sleep(30)
    
    def run_once(self):
        """运行一次"""
        logger.info('=== Running one-time analysis ===')
        self.run_morning_pick()
    
    def start(self):
        """启动"""
        logger.info('========================================')
        logger.info('Auto Stock Picker v3.0 Started')
        logger.info('========================================')
        
        # 运行调度器
        self.run_scheduler()
    
    def stop(self):
        """停止"""
        logger.info('Stopping...')
        STOP_EVENT.set()


def main():
    """主入口"""
    runner = AutoRunner()
    
    # 检查参数
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == 'once':
            runner.run_once()
        elif cmd == 'morning':
            runner.run_morning_pick()
        elif cmd == 'monitor':
            runner.run_monitoring()
        elif cmd == 'evening':
            runner.run_evening_summary()
        elif cmd == 'backtest':
            runner.run_weekly_backtest()
        else:
            print(f'Unknown command: {cmd}')
            print('Usage: python auto_runner.py [once|morning|monitor|evening|backtest]')
    else:
        # 24/7运行
        runner.start()


if __name__ == '__main__':
    main()
