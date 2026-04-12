# -*- coding: utf-8 -*-
"""
量化系统看门狗 - 监控任务执行
确保系统持续运行并汇报进展
"""
import os
import sys
import time
import sqlite3
from datetime import datetime

os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')
sys.path.insert(0, os.getcwd())

class QuantWatcher:
    """看门狗"""
    
    def __init__(self):
        self.db_path = 'data/stocks.db'
        self.last_check = None
        self.running = True
    
    def check_data_collection(self):
        """检查数据收集进度"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # 股票数量
        c.execute('SELECT COUNT(DISTINCT code) FROM kline')
        stock_count = c.fetchone()[0]
        
        # K线数量
        c.execute('SELECT COUNT(*) FROM kline')
        kline_count = c.fetchone()[0]
        
        # 最新更新时间
        c.execute('SELECT MAX(date) FROM kline')
        latest = c.fetchone()[0]
        
        conn.close()
        
        return {
            'stocks': stock_count,
            'klines': kline_count,
            'latest': latest
        }
    
    def check_backtest_results(self):
        """检查回测结果"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''SELECT strategy, trades, win_rate, avg_return, target_rate 
                    FROM backtest_log ORDER BY id DESC LIMIT 5''')
        results = c.fetchall()
        
        conn.close()
        
        return results
    
    def report(self):
        """生成状态报告"""
        data = self.check_data_collection()
        
        print('='*60)
        print('【量化系统看门狗】')
        print('='*60)
        print(f'时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        print('')
        print('【数据收集状态】')
        print(f'  股票数量: {data["stocks"]}只')
        print(f'  K线数量: {data["klines"]}条')
        print(f'  最新更新: {data["latest"]}')
        print('')
        
        # 检查回测结果
        results = self.check_backtest_results()
        if results:
            print('【回测结果】')
            for r in results[:3]:
                print(f'  {r[0]}: 交易{r[1]}笔 胜率{r[2]:.1f}% 均收益{r[3]:.2f}% 达标率{r[4]:.1f}%')
        else:
            print('【回测结果】暂无')
        
        print('')
        
        # 检查是否达标
        if data['stocks'] >= 50:
            print('✅ 数据收集进度: 良好 (50+只)')
        elif data['stocks'] >= 20:
            print('⚠️ 数据收集进度: 进行中 (20+只)')
        else:
            print('❌ 数据收集进度: 需加快')
        
        return data
    
    def run(self):
        """持续监控"""
        print('看门狗启动...')
        
        while self.running:
            try:
                data = self.report()
                
                # 如果数据不足50只，提示收集
                if data['stocks'] < 50:
                    print('')
                    print('建议: 需要收集更多股票数据!')
                    print('可以调用 collect_more_data() 收集数据')
                
                print('')
                print('下次检查: 15分钟后')
                print('')
                
                time.sleep(15 * 60)  # 15分钟
                
            except KeyboardInterrupt:
                print('看门狗停止')
                self.running = False
            except Exception as e:
                print(f'错误: {e}')
                time.sleep(60)

if __name__ == '__main__':
    watcher = QuantWatcher()
    watcher.run()
