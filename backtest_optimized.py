# -*- coding: utf-8 -*-
"""
优化版策略 - 提高胜率
基于回测结果优化
"""
import os
import sys
import time
import json
import random
import logging
from datetime import datetime

os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')
sys.path.insert(0, os.getcwd())

import baostock as bs
import pandas as pd
import numpy as np

from technical_analysis import TechnicalIndicators

# 日志
os.makedirs('logs', exist_ok=True)
os.makedirs('reports', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/backtest_v2.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger('BacktestV2')

# 股票池
STOCK_POOL = [
    ('sh.603585', '苏利股份'), ('sh.603122', '合富中国'), ('sh.600488', '津药药业'),
    ('sh.600654', '中安科'), ('sh.603966', '法兰泰克'), ('sh.600106', '重庆路桥'),
    ('sh.603189', '网达软件'), ('sh.603206', '嘉环科技'), ('sh.603220', '中贝通信'),
    ('sh.600071', '凤凰光学'), ('sh.600056', '中国医药'), ('sh.600869', '远东股份'),
    ('sh.605589', '圣泉集团'), ('sh.605133', '李子园'), ('sh.605303', '园林股份'),
    ('sh.603033', '三维股份'), ('sh.603067', '振华股份'), ('sh.600302', '标准股份'),
    ('sz.000950', '重药控股'), ('sz.002678', '珠江钢琴'), ('sz.002328', '新朋股份'),
    ('sz.002869', '金溢科技'), ('sz.002831', '裕同科技'), ('sz.002952', '亚世光电'),
    ('sz.000720', '新能泰山'), ('sz.000586', '汇源通信'),
]

# ============================================================
# 优化策略 - 更严格的条件
# ============================================================
class OptimizedStrategies:
    def __init__(self):
        self.ti = TechnicalIndicators()

    def golden_cross_strict(self, df):
        """金叉策略 - 更严格"""
        if len(df) < 35: return False
        c = df['close'].tolist()
        v = df['volume'].tolist()
        
        ma5 = sum(c[-5:]) / 5
        ma10 = sum(c[-10:]) / 10
        ma20 = sum(c[-20:]) / 20
        ma60 = sum(c[-60:]) / 60 if len(c) >= 60 else ma20
        
        # 条件更严格
        # 1. 多头排列
        if not (ma5 > ma10 > ma20 > ma60 * 0.98):
            return False
        
        # 2. 放量
        avg_vol = sum(v[-20:-1]) / 19
        if v[-1] < avg_vol * 1.2:
            return False
        
        # 3. 涨幅适中 (不要追高)
        chg = (c[-1] - c[-2]) / c[-2] * 100
        if chg > 5 or chg < -3:
            return False
        
        return True

    def bollinger_rebound(self, df):
        """布林带反弹 - 优化"""
        if len(df) < 22: return False
        c = df['close'].tolist()
        v = df['volume'].tolist()
        
        upper, mid, lower = self.ti.calculate_bollinger(c)
        
        # 1. 价格在下轨附近
        if c[-1] > lower * 1.02:
            return False
        
        # 2. 前几天有下跌
        chg5 = (c[-1] - c[-5]) / c[-5] * 100
        if chg5 > -2:  # 需要先跌
            return False
        
        # 3. 今天开始反弹
        chg1 = (c[-1] - c[-2]) / c[-2] * 100
        if chg1 < 0:
            return False
        
        return True

    def rsi_reversal(self, df):
        """RSI反转 - 更严格"""
        if len(df) < 20: return False
        c = df['close'].tolist()
        
        rsi = self.ti.calculate_rsi(c)
        
        # 1. RSI在超卖区间
        if rsi > 25:
            return False
        
        # 2. 前一天RSI更低 (开始反转)
        rsi_prev = self.ti.calculate_rsi(c[:-1])
        if rsi <= rsi_prev:
            return False
        
        # 3. 价格开始反弹
        chg = (c[-1] - c[-2]) / c[-2] * 100
        if chg < 0:
            return False
        
        return True

    def multi_factor_v2(self, df):
        """多因子策略 v2 - 更严格"""
        if len(df) < 40: return False
        c = df['close'].tolist()
        h = df['high'].tolist()
        l = df['low'].tolist()
        v = df['volume'].tolist()
        
        # 均线
        ma5 = sum(c[-5:]) / 5
        ma10 = sum(c[-10:]) / 10
        ma20 = sum(c[-20:]) / 20
        ma60 = sum(c[-60:]) / 60 if len(c) >= 60 else ma20
        
        # 技术指标
        dif, dea, _ = self.ti.calculate_macd(c)
        rsi = self.ti.calculate_rsi(c)
        k, d, j = self.ti.calculate_kdj(h, l, c)
        
        # 量能
        avg_vol = sum(v[-20:-1]) / 19
        vol_ratio = v[-1] / avg_vol if avg_vol > 0 else 0
        
        # 涨跌
        chg5 = (c[-1] - c[-5]) / c[-5] * 100
        chg10 = (c[-1] - c[-10]) / c[-10] * 100
        
        score = 0
        
        # 趋势 (30分)
        if ma5 > ma10 > ma20:
            score += 30
        elif ma5 > ma10:
            score += 15
        
        # MACD (25分)
        if dif > dea and dif < 0:
            score += 25
        elif dif > dea:
            score += 10
        
        # RSI (20分)
        if 25 < rsi < 45:
            score += 20
        elif rsi < 25:
            score += 25
        
        # KDJ (15分)
        if k > d and k < 40:
            score += 15
        elif k > d:
            score += 8
        
        # 量能 (10分)
        if vol_ratio > 1.5:
            score += 10
        elif vol_ratio > 1.2:
            score += 5
        
        # 避免追高
        if chg5 > 10:
            score -= 20
        if chg10 > 20:
            score -= 30
        
        return score >= 70

    def trend_follow_v2(self, df):
        """趋势跟踪 v2"""
        if len(df) < 30: return False
        c = df['close'].tolist()
        v = df['volume'].tolist()
        
        ma5 = sum(c[-5:]) / 5
        ma10 = sum(c[-10:]) / 10
        ma20 = sum(c[-20:]) / 20
        
        # 1. 明确上升趋势
        if not (ma5 > ma10 > ma20):
            return False
        
        # 2. 价格在均线上方
        if c[-1] < ma5:
            return False
        
        # 3. 温和上涨 (不追高)
        chg = (c[-1] - c[-2]) / c[-2] * 100
        if chg > 4 or chg < 0:
            return False
        
        # 4. 量能配合
        avg_vol = sum(v[-10:-1]) / 9
        if v[-1] < avg_vol * 0.8:
            return False
        
        return True

    def support_bounce(self, df):
        """支撑位反弹"""
        if len(df) < 30: return False
        c = df['close'].tolist()
        l = df['low'].tolist()
        v = df['volume'].tolist()
        
        # 找近期低点
        recent_lows = sorted(l[-20:])
        support = recent_lows[0]  # 最低点作为支撑
        
        # 1. 价格接近支撑位
        if c[-1] > support * 1.03:
            return False
        
        # 2. 今天反弹
        chg = (c[-1] - c[-2]) / c[-2] * 100
        if chg < 1:
            return False
        
        # 3. 放量
        avg_vol = sum(v[-10:-1]) / 9
        if v[-1] < avg_vol:
            return False
        
        return True

STRATEGY_FUNCS = {
    'GoldenCrossStrict': lambda s, df: s.golden_cross_strict(df),
    'BollingerRebound':  lambda s, df: s.bollinger_rebound(df),
    'RSIReversal':       lambda s, df: s.rsi_reversal(df),
    'MultiFactorV2':     lambda s, df: s.multi_factor_v2(df),
    'TrendFollowV2':     lambda s, df: s.trend_follow_v2(df),
    'SupportBounce':     lambda s, df: s.support_bounce(df),
}

# ============================================================
# 数据采集
# ============================================================
def fetch_klines(code, start='2025-06-01', end='2026-04-06'):
    rs = bs.query_history_k_data_plus(
        code, 'date,open,high,low,close,volume,turn',
        start_date=start, end_date=end,
        frequency='d', adjustflag='2'
    )
    rows = []
    while rs.error_code == '0' and rs.next():
        r = rs.get_row_data()
        try:
            rows.append({
                'date': r[0],
                'open': float(r[1]) if r[1] else 0,
                'high': float(r[2]) if r[2] else 0,
                'low': float(r[3]) if r[3] else 0,
                'close': float(r[4]) if r[4] else 0,
                'volume': float(r[5]) if r[5] else 0,
            })
        except:
            pass
    return pd.DataFrame(rows)

# ============================================================
# 回测
# ============================================================
def backtest_strategy(func, strat_obj, df, holding_days=5):
    trades = []
    if len(df) < 60:
        return trades
    
    for i in range(50, len(df) - holding_days):
        window = df.iloc[:i+1].copy()
        try:
            signal = func(strat_obj, window)
        except:
            signal = False
        
        if signal:
            buy_price = df.iloc[i]['close']
            sell_price = df.iloc[i + holding_days]['close']
            if buy_price > 0:
                pnl = (sell_price - buy_price) / buy_price * 100
                trades.append({
                    'buy_date': df.iloc[i]['date'],
                    'sell_date': df.iloc[i + holding_days]['date'],
                    'buy_price': round(buy_price, 2),
                    'sell_price': round(sell_price, 2),
                    'pnl': round(pnl, 2),
                })
    return trades

def run_backtest():
    strat_obj = OptimizedStrategies()
    all_results = {name: [] for name in STRATEGY_FUNCS}
    
    log.info('登录BaoStock...')
    bs.login()
    
    total = len(STOCK_POOL)
    for idx, (code, name) in enumerate(STOCK_POOL):
        log.info('[%d/%d] %s %s', idx+1, total, code, name)
        df = fetch_klines(code)
        if df.empty or len(df) < 60:
            continue
        
        for sname, func in STRATEGY_FUNCS.items():
            trades = backtest_strategy(func, strat_obj, df, holding_days=5)
            all_results[sname].extend(trades)
        
        time.sleep(0.2)
    
    bs.logout()
    
    # 汇总
    summary = []
    for sname, trades in all_results.items():
        if not trades:
            summary.append({
                'strategy': sname, 'trades': 0, 'win_rate': 0,
                'avg_pnl': 0, 'max_pnl': 0, 'min_pnl': 0,
                'target_rate': 0, 'sharpe': 0
            })
            continue
        
        pnls = [t['pnl'] for t in trades]
        wins = sum(1 for p in pnls if p > 0)
        target = sum(1 for p in pnls if p >= 30)
        
        # Sharpe比率 (简化)
        avg = np.mean(pnls)
        std = np.std(pnls) if np.std(pnls) > 0 else 1
        sharpe = avg / std if std > 0 else 0
        
        summary.append({
            'strategy': sname,
            'trades': len(trades),
            'win_rate': round(wins / len(trades) * 100, 1),
            'avg_pnl': round(avg, 2),
            'max_pnl': round(max(pnls), 2),
            'min_pnl': round(min(pnls), 2),
            'target_rate': round(target / len(trades) * 100, 1),
            'sharpe': round(sharpe, 2),
        })
    
    summary.sort(key=lambda x: x['win_rate'], reverse=True)
    return summary

def main():
    log.info('=' * 60)
    log.info('优化策略回测 v2')
    log.info('目标: 提高胜率到70%+')
    log.info('=' * 60)
    
    # 多轮回测，不同持有周期
    for holding in [3, 5, 7]:
        log.info('')
        log.info('=== 持有周期: %d天 ===', holding)
        
        strat_obj = OptimizedStrategies()
        all_results = {name: [] for name in STRATEGY_FUNCS}
        
        bs.login()
        for idx, (code, name) in enumerate(STOCK_POOL):
            df = fetch_klines(code)
            if df.empty or len(df) < 60:
                continue
            
            for sname, func in STRATEGY_FUNCS.items():
                trades = backtest_strategy(func, strat_obj, df, holding)
                all_results[sname].extend(trades)
            time.sleep(0.15)
        bs.logout()
        
        # 汇总
        log.info('')
        for sname, trades in all_results.items():
            if not trades:
                continue
            pnls = [t['pnl'] for t in trades]
            wins = sum(1 for p in pnls if p > 0)
            wr = wins / len(trades) * 100
            avg = np.mean(pnls)
            log.info('%s: %d笔 胜率%.1f%% 均收益%.2f%%', sname, len(trades), wr, avg)
    
    log.info('')
    log.info('回测完成')

if __name__ == '__main__':
    main()
