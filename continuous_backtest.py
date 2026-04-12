# -*- coding: utf-8 -*-
"""
持续回测主程序
使用BaoStock采集真实K线数据，对8种策略进行持续回测
"""
import os
import sys
import time
import json
import sqlite3
import random
import logging
from datetime import datetime, timedelta

os.chdir(r'C:\Users\Administrator\.qclaw\workspace\quant-24x7')
sys.path.insert(0, os.getcwd())

import baostock as bs
import pandas as pd
import numpy as np

from technical_analysis import TechnicalIndicators

# 日志
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)
os.makedirs('reports', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/backtest.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger('Backtest')

# ============================================================
# 目标股票池 - 主板中小盘
# ============================================================
STOCK_POOL = [
    # 上证主板
    ('sh.603585', '苏利股份'),
    ('sh.603122', '合富中国'),
    ('sh.600488', '津药药业'),
    ('sh.600654', '中安科'),
    ('sh.603966', '法兰泰克'),
    ('sh.600106', '重庆路桥'),
    ('sh.603189', '网达软件'),
    ('sh.603206', '嘉环科技'),
    ('sh.603220', '中贝通信'),
    ('sh.600071', '凤凰光学'),
    ('sh.600056', '中国医药'),
    ('sh.600869', '远东股份'),
    ('sh.605589', '圣泉集团'),
    ('sh.605133', '李子园'),
    ('sh.605303', '园林股份'),
    ('sh.603033', '三维股份'),
    ('sh.603067', '振华股份'),
    ('sh.600302', '标准股份'),
    # 深证主板
    ('sz.000950', '重药控股'),
    ('sz.002678', '珠江钢琴'),
    ('sz.002328', '新朋股份'),
    ('sz.002869', '金溢科技'),
    ('sz.002831', '裕同科技'),
    ('sz.002952', '亚世光电'),
    ('sz.000720', '新能泰山'),
    ('sz.000586', '汇源通信'),
    ('sz.002678', '珠江钢琴'),
]

# ============================================================
# 策略定义
# ============================================================
class Strategies:
    def __init__(self):
        self.ti = TechnicalIndicators()

    def golden_cross(self, df):
        """MA5上穿MA20"""
        if len(df) < 25: return False
        c = df['close'].tolist()
        ma5 = sum(c[-5:]) / 5
        ma10 = sum(c[-10:]) / 10
        ma20 = sum(c[-20:]) / 20
        ma5_prev = sum(c[-6:-1]) / 5
        ma20_prev = sum(c[-21:-1]) / 20
        return ma5_prev < ma20_prev and ma5 >= ma20 and ma5 > ma10

    def macd_golden(self, df):
        """MACD金叉"""
        if len(df) < 35: return False
        c = df['close'].tolist()
        dif, dea, _ = self.ti.calculate_macd(c)
        dif_p, dea_p, _ = self.ti.calculate_macd(c[:-1])
        return dif_p < dea_p and dif >= dea and dif < 0

    def rsi_oversold(self, df):
        """RSI超卖"""
        if len(df) < 15: return False
        c = df['close'].tolist()
        rsi = self.ti.calculate_rsi(c)
        return rsi < 35

    def bollinger_lower(self, df):
        """布林下轨"""
        if len(df) < 22: return False
        c = df['close'].tolist()
        _, _, lower = self.ti.calculate_bollinger(c)
        return c[-1] <= lower * 1.01

    def volume_breakout(self, df):
        """放量突破"""
        if len(df) < 22: return False
        c = df['close'].tolist()
        v = df['volume'].tolist()
        ma5 = sum(c[-5:]) / 5
        ma10 = sum(c[-10:]) / 10
        avg_vol = sum(v[-20:-1]) / 19
        vol_ratio = v[-1] / avg_vol if avg_vol > 0 else 0
        return vol_ratio >= 1.8 and c[-1] > ma5 and ma5 > ma10

    def multi_factor(self, df):
        """多因子综合"""
        if len(df) < 30: return False
        c = df['close'].tolist()
        h = df['high'].tolist()
        l = df['low'].tolist()
        v = df['volume'].tolist()

        ma5 = sum(c[-5:]) / 5
        ma10 = sum(c[-10:]) / 10
        ma20 = sum(c[-20:]) / 20
        dif, dea, _ = self.ti.calculate_macd(c)
        rsi = self.ti.calculate_rsi(c)
        k, d, j = self.ti.calculate_kdj(h, l, c)

        score = 0
        if ma5 > ma10 > ma20: score += 40
        elif ma5 > ma10: score += 20
        if dif > dea: score += 25
        if 30 < rsi < 60: score += 20
        elif rsi < 30: score += 30
        if k > d and k < 80: score += 15
        return score >= 65

    def kdj_golden(self, df):
        """KDJ金叉"""
        if len(df) < 12: return False
        c = df['close'].tolist()
        h = df['high'].tolist()
        l = df['low'].tolist()
        k, d, j = self.ti.calculate_kdj(h, l, c)
        k_p, d_p, _ = self.ti.calculate_kdj(h[:-1], l[:-1], c[:-1])
        return k_p < d_p and k >= d and k < 50

    def trend_momentum(self, df):
        """趋势+动量"""
        if len(df) < 25: return False
        c = df['close'].tolist()
        v = df['volume'].tolist()
        ma5 = sum(c[-5:]) / 5
        ma20 = sum(c[-20:]) / 20
        chg5 = (c[-1] - c[-5]) / c[-5] * 100
        avg_vol = sum(v[-20:-1]) / 19
        vol_ratio = v[-1] / avg_vol if avg_vol > 0 else 0
        return ma5 > ma20 and chg5 > 3 and vol_ratio > 1.5

STRATEGY_FUNCS = {
    'GoldenCross':    lambda s, df: s.golden_cross(df),
    'MACDGolden':     lambda s, df: s.macd_golden(df),
    'RSIOversold':    lambda s, df: s.rsi_oversold(df),
    'BollingerLower': lambda s, df: s.bollinger_lower(df),
    'VolumeBreakout': lambda s, df: s.volume_breakout(df),
    'MultiFactor':    lambda s, df: s.multi_factor(df),
    'KDJGolden':      lambda s, df: s.kdj_golden(df),
    'TrendMomentum':  lambda s, df: s.trend_momentum(df),
}

# ============================================================
# 数据采集
# ============================================================
def fetch_klines(code, start='2025-10-01', end='2026-04-06'):
    """用BaoStock采集K线"""
    rs = bs.query_history_k_data_plus(
        code,
        'date,open,high,low,close,volume,turn',
        start_date=start,
        end_date=end,
        frequency='d',
        adjustflag='2'
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
                'turnover': float(r[6]) if r[6] else 0,
            })
        except:
            pass
    return pd.DataFrame(rows)

# ============================================================
# 回测引擎
# ============================================================
def backtest_one(strategy_name, func, strat_obj, df, holding_days=5):
    """对单只股票单个策略回测"""
    trades = []
    if len(df) < 35:
        return trades

    for i in range(30, len(df) - holding_days):
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

def run_full_backtest(holding_days=5):
    """全量回测"""
    strat_obj = Strategies()
    all_results = {name: [] for name in STRATEGY_FUNCS}

    log.info('登录BaoStock...')
    bs.login()

    total = len(STOCK_POOL)
    for idx, (code, name) in enumerate(STOCK_POOL):
        log.info('[%d/%d] %s %s', idx+1, total, code, name)
        df = fetch_klines(code)
        if df.empty or len(df) < 35:
            log.info('  数据不足，跳过')
            continue

        for sname, func in STRATEGY_FUNCS.items():
            trades = backtest_one(sname, func, strat_obj, df, holding_days)
            all_results[sname].extend(trades)

        time.sleep(0.2)

    bs.logout()

    # 汇总
    summary = []
    for sname, trades in all_results.items():
        if not trades:
            summary.append({
                'strategy': sname,
                'trades': 0,
                'win_rate': 0,
                'avg_pnl': 0,
                'max_pnl': 0,
                'min_pnl': 0,
                'target_rate': 0,
            })
            continue

        pnls = [t['pnl'] for t in trades]
        wins = sum(1 for p in pnls if p > 0)
        target = sum(1 for p in pnls if p >= 30)

        summary.append({
            'strategy': sname,
            'trades': len(trades),
            'win_rate': round(wins / len(trades) * 100, 1),
            'avg_pnl': round(np.mean(pnls), 2),
            'max_pnl': round(max(pnls), 2),
            'min_pnl': round(min(pnls), 2),
            'target_rate': round(target / len(trades) * 100, 1),
        })

    summary.sort(key=lambda x: x['avg_pnl'], reverse=True)
    return summary

# ============================================================
# 主循环
# ============================================================
def main():
    log.info('=' * 60)
    log.info('持续回测系统启动')
    log.info('=' * 60)

    round_num = 1
    best_strategy = None

    while True:
        log.info('')
        log.info('=== 第 %d 轮回测 ===', round_num)
        log.info('持有周期: 5天')

        try:
            summary = run_full_backtest(holding_days=5)

            log.info('')
            log.info('--- 回测结果 ---')
            for r in summary:
                log.info('%s: %d笔 胜率%.1f%% 均收益%.2f%% 达标率%.1f%%',
                         r['strategy'], r['trades'], r['win_rate'],
                         r['avg_pnl'], r['target_rate'])

            best = summary[0] if summary else None
            if best:
                best_strategy = best['strategy']
                log.info('')
                log.info('最佳策略: %s (均收益%.2f%%, 胜率%.1f%%)',
                         best['strategy'], best['avg_pnl'], best['win_rate'])

            # 保存结果
            result_file = 'reports/backtest_round_%d.json' % round_num
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'round': round_num,
                    'time': datetime.now().isoformat(),
                    'summary': summary
                }, f, ensure_ascii=False, indent=2)

            log.info('结果已保存: %s', result_file)

        except Exception as e:
            log.error('回测出错: %s', str(e))

        round_num += 1
        log.info('')
        log.info('等待60秒后开始下一轮...')
        time.sleep(60)

if __name__ == '__main__':
    main()
