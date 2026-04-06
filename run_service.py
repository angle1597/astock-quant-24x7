# -*- coding: utf-8 -*-
"""
Windows服务方式运行24/7自动化选股系统
Run as Windows Scheduled Task or Service
"""
import os
import sys
import time
import logging
from datetime import datetime

os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')
sys.path.insert(0, os.getcwd())

from auto_runner import AutoRunner

def setup_logging():
    """配置日志"""
    os.makedirs('logs', exist_ok=True)
    
    log_file = f'logs/service_{datetime.now().strftime("%Y%m%d")}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def main():
    """主函数"""
    setup_logging()
    logger = logging.getLogger('Service')
    
    logger.info('=' * 50)
    logger.info('Auto Stock Picker Service Starting...')
    logger.info('=' * 50)
    
    try:
        runner = AutoRunner()
        
        # 运行一次完整分析
        runner.run_once()
        
        logger.info('Service initialization completed')
        logger.info('Entering main loop...')
        
        # 持续运行直到被终止
        while True:
            try:
                # 检查市场状态
                status = runner.check_market_status()
                
                if status == 'trading' or status == 'pre_open':
                    # 盘中监控
                    runner.run_monitoring()
                
                elif status == 'after_close':
                    # 尾盘总结
                    runner.run_evening_summary()
                
                # 每5分钟检查一次
                time.sleep(300)
                
            except KeyboardInterrupt:
                logger.info('Received shutdown signal')
                break
            except Exception as e:
                logger.error(f'Error in main loop: {e}')
                time.sleep(60)
        
    except Exception as e:
        logger.error(f'Fatal error: {e}')
        raise
    finally:
        logger.info('Service stopped')

if __name__ == '__main__':
    main()
