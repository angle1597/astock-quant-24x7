"""
量化系统V11 - 双策略融合
MACD金叉策略 + 涨停回调策略 融合回测
"""

import sqlite3
import json
from datetime import datetime, timedelta

DB_PATH = 'data/stocks.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    return conn

def calc_ema(prices, period):
    """计算EMA"""
    if len(prices) < period:
        return None
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * (2/(period+1)) + ema * (1 - 2/(period+1))
    return ema

def calc_macd(prices, fast=12, slow=26, signal=9):
    """计算MACD，返回(dea, macd, signal)序列"""
    if len(prices) < slow + signal:
        return []
    
    emas = []
    for i in range(len(prices)):
        e12 = calc_ema(prices[:i+1], 12) if len(prices[:i+1]) >= 12 else None
        e26 = calc_ema(prices[:i+1], 26) if len(prices[:i+1]) >= 26 else None
        emas.append((e12, e26))
    
    difs = []
    for e12, e26 in emas:
        if e12 and e26:
            difs.append(e12 - e26)
        else:
            difs.append(None)
    
    # DEA signal line (EMA of DIF)
    valid_difs = [d for d in difs if d is not None]
    if len(valid_difs) < signal:
        return []
    
    dea = sum(valid_difs[:signal]) / signal
    result = []
    for i, dif in enumerate(difs):
        if dif is None:
            result.append(None)
        else:
            if len(result) >= signal:
                valid_hist = [r for r in result if r is not None]
                if len(valid_hist) >= signal:
                    dea = dea * (1 - 2/(signal+1)) + dif * (2/(signal+1))
            else:
                # Build up DEA
                valid_hist = [r for r in result if r is not None]
                if len(valid_hist) < signal:
                    dea = sum(valid_hist + [dif]) / (len(valid_hist) + 1)
                else:
                    dea = dea * (1 - 2/(signal+1)) + dif * (2/(signal+1))
            macd = (dif - dea) * 2
            result.append((dea, macd, dif))
    return result

def get_stock_klines(code):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT date, open, high, low, close, volume FROM kline WHERE code=? ORDER BY date ASC", (code,))
    rows = c.fetchall()
    conn.close()
    return rows

def is_limit_up(kline_row, prev_close):
    """判断是否涨停 (close = prev_close * 1.1 or >= 9.9%)"""
    date, open_, high, low, close, vol = kline_row
    if prev_close is None or prev_close <= 0 or close is None:
        return False
    pct = (close - prev_close) / prev_close
    return pct >= 0.095  # >= 9.5% 视为涨停

def check_macd_golden_cross(prices, dates, idx):
    """检查idx位置是否是MACD金叉 (DIF从负转正，DIF上穿DEA)"""
    if idx < 34:
        return False
    
    macd_data = calc_macd(prices[:idx+1], 12, 26, 9)
    if len(macd_data) < 2 or macd_data[-1] is None:
        return False
    
    dea_prev, macd_prev, dif_prev = macd_data[-2]
    dea_cur, macd_cur, dif_cur = macd_data[-1]
    
    if dea_prev is None or macd_prev is None or dif_prev is None:
        return False
    if dea_cur is None or macd_cur is None or dif_cur is None:
        return False
    
    # 金叉：DIF从负转正 或 DIF上穿DEA
    golden_cross = (dif_prev < 0 and dif_cur > 0) or (dif_prev < dea_prev and dif_cur > dea_cur)
    return golden_cross

def check_limit_up_pullback(klines, idx, pullback_days=(1,3), min_pullback=0.02):
    """
    检查idx位置是否满足：前几日有涨停，且当前回调>=min_pullback
    idx = 今日（最后一天），向前看1-3天找涨停
    """
    if idx < 3:
        return False, None, None
    
    # 向前找涨停
    for lookback in range(pullback_days[0], pullback_days[1]+1):
        prev_idx = idx - lookback
        if prev_idx < 0:
            continue
        curr_close = klines[idx][4]
        prev_close = klines[prev_idx-1][4] if prev_idx > 0 else None
        
        if prev_close is None or prev_close <= 0:
            continue
        
        pct = (klines[prev_idx][4] - prev_close) / prev_close
        if pct >= 0.095:  # 涨停
            # 计算从涨停日到今日的回调幅度
            limit_close = klines[prev_idx][4]
            curr_close_px = curr_close
            pullback = (limit_close - curr_close_px) / limit_close
            
            if pullback >= min_pullback:
                return True, pullback, lookback
    return False, None, None

def check_macd_momentum(prices, dates, idx, min_days=10):
    """检查idx之前是否有MACD金叉，在最近min_days天内"""
    if idx < 40:
        return False
    
    macd_data = calc_macd(prices[:idx], 12, 26, 9)
    for i in range(len(macd_data)-min_days, len(macd_data)):
        if i < 1:
            continue
        if macd_data[i] is None or macd_data[i-1] is None:
            continue
        dea_prev, macd_prev, dif_prev = macd_data[i-1]
        dea_cur, macd_cur, dif_cur = macd_data[i]
        if dea_prev and macd_prev and dif_prev and dea_cur and macd_cur and dif_cur:
            if dif_prev < 0 and dif_cur > 0:
                return True
            if dif_prev < dea_prev and dif_cur > dea_cur:
                return True
    return False

def backtest_macd_strategy(klines, golden_cross_idx, hold_days=28, target_low=0.08, target_high=0.15, price_limit=10.0):
    """
    从金叉点开始持有28天，统计达标情况
    达标：持有期内最大涨幅在8-15%之间，价格<=10元
    """
    if golden_cross_idx + hold_days > len(klines):
        return None
    
    entry_price = klines[golden_cross_idx][4]  # close price
    if entry_price is None or entry_price <= 0 or entry_price > price_limit:
        return None
    
    max_gain = -999
    exit_idx = min(golden_cross_idx + hold_days, len(klines))
    
    for i in range(golden_cross_idx + 1, exit_idx):
        price = klines[i][4]
        if price:
            gain = (price - entry_price) / entry_price
            if gain > max_gain:
                max_gain = gain
    
    # 达标：最大涨幅在8-15%之间
    hit = target_low <= max_gain <= target_high
    
    return {
        'entry_date': klines[golden_cross_idx][0],
        'entry_price': entry_price,
        'hold_days': exit_idx - golden_cross_idx - 1,
        'max_gain': round(max_gain * 100, 2),
        'hit': hit,
        'exit_date': klines[exit_idx-1][0] if exit_idx > golden_cross_idx else None
    }

def backtest_limitup_strategy(klines, pullback_idx, hold_days=5, price_limit=10.0):
    """
    从回调买点持有5天
    """
    if pullback_idx + hold_days > len(klines):
        return None
    
    entry_price = klines[pullback_idx][4]
    if entry_price is None or entry_price <= 0 or entry_price > price_limit:
        return None
    
    gains = []
    for i in range(pullback_idx + 1, pullback_idx + hold_days + 1):
        if i >= len(klines):
            break
        price = klines[i][4]
        if price:
            gain = (price - entry_price) / entry_price
            gains.append(gain)
    
    if not gains:
        return None
    
    avg_gain = sum(gains) / len(gains)
    win_rate = sum(1 for g in gains if g > 0) / len(gains)
    
    return {
        'entry_date': klines[pullback_idx][0],
        'entry_price': entry_price,
        'hold_days': len(gains),
        'avg_gain': round(avg_gain * 100, 2),
        'win_rate': round(win_rate * 100, 2),
        'exit_date': klines[min(pullback_idx + hold_days, len(klines)-1)][0]
    }

def main():
    print("=" * 60)
    print("量化系统V11 - 双策略融合回测")
    print("=" * 60)
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT DISTINCT code FROM kline ORDER BY code")
    all_codes = [r[0] for r in c.fetchall()]
    conn.close()
    
    print(f"共 {len(all_codes)} 只股票")
    
    # === 第一阶段：扫描所有股票的历史信号 ===
    all_macd_signals = []
    all_limitup_signals = []
    all_macd_trades = []
    all_limitup_trades = []
    
    for code in all_codes:
        klines = get_stock_klines(code)
        if len(klines) < 50:
            continue
        
        prices = [row[4] for row in klines]  # close prices
        dates = [row[0] for row in klines]
        
        for idx in range(34, len(klines) - 1):
            # MACD金叉检测
            if check_macd_golden_cross(prices, dates, idx):
                entry_price = klines[idx][4]
                if entry_price and 0 < entry_price <= 10:
                    result = backtest_macd_strategy(klines, idx, hold_days=28)
                    if result:
                        result['code'] = code
                        result['signal_date'] = klines[idx][0]
                        all_macd_trades.append(result)
            
            # 涨停回调检测 (跳过最后一天，用倒数第二天作为今日)
            if idx < len(klines) - 2:
                is_lu, pullback, lookback = check_limit_up_pullback(klines, idx, (1,3), 0.02)
                if is_lu:
                    entry_price = klines[idx][4]
                    if entry_price and 0 < entry_price <= 10:
                        result = backtest_limitup_strategy(klines, idx, hold_days=5)
                        if result:
                            result['code'] = code
                            result['signal_date'] = klines[idx][0]
                            result['pullback'] = round(pullback * 100, 2)
                            result['lookback_days'] = lookback
                            all_limitup_trades.append(result)
    
    print(f"\nMACD金叉信号总数: {len(all_macd_trades)}")
    print(f"涨停回调信号总数: {len(all_limitup_trades)}")
    
    # === 第二阶段：融合策略 - 找同时满足两个条件的股票 ===
    # 涨停回调 + 同时近期有MACD金叉
    
    fusion_trades = []
    
    for lu_trade in all_limitup_trades:
        code = lu_trade['code']
        signal_date = lu_trade['signal_date']
        
        # 在该股历史中找最近30天内的MACD金叉
        klines = get_stock_klines(code)
        prices = [row[4] for row in klines]
        dates = [row[0] for row in klines]
        
        # 找信号日期对应的索引
        signal_idx = None
        for i, d in enumerate(dates):
            if d == signal_date:
                signal_idx = i
                break
        
        if signal_idx is None or signal_idx < 34:
            continue
        
        # 往前30天内找MACD金叉
        macd_in_range = False
        macd_result = None
        for look_idx in range(max(34, signal_idx - 30), signal_idx):
            if check_macd_golden_cross(prices, dates, look_idx):
                macd_in_range = True
                # 获取MACD金叉后的持有收益
                macd_result = backtest_macd_strategy(klines, look_idx, hold_days=28)
                break
        
        if macd_in_range:
            lu_trade['macd_confirmed'] = True
            lu_trade['macd_max_gain'] = macd_result['max_gain'] if macd_result else None
            lu_trade['macd_hit'] = macd_result['hit'] if macd_result else False
            lu_trade['macd_entry_price'] = macd_result['entry_price'] if macd_result else None
            fusion_trades.append(lu_trade)
    
    print(f"融合策略信号总数: {len(fusion_trades)}")
    
    # === 第三阶段：统计结果 ===
    
    # MACD策略统计
    macd_hit = [t for t in all_macd_trades if t['hit']]
    macd_rate = len(macd_hit) / len(all_macd_trades) * 100 if all_macd_trades else 0
    macd_avg_gain = sum(t['max_gain'] for t in all_macd_trades) / len(all_macd_trades) if all_macd_trades else 0
    
    # 涨停回调策略统计
    lu_avg_gain = sum(t['avg_gain'] for t in all_limitup_trades) / len(all_limitup_trades) if all_limitup_trades else 0
    lu_win_rate = sum(1 for t in all_limitup_trades if t['avg_gain'] > 0) / len(all_limitup_trades) * 100 if all_limitup_trades else 0
    
    # 融合策略统计
    fusion_hit = [t for t in fusion_trades if t['macd_hit']]
    fusion_rate = len(fusion_hit) / len(fusion_trades) * 100 if fusion_trades else 0
    fusion_avg_gain = sum(t['avg_gain'] for t in fusion_trades) / len(fusion_trades) if fusion_trades else 0
    fusion_win_rate = sum(1 for t in fusion_trades if t['avg_gain'] > 0) / len(fusion_trades) * 100 if fusion_trades else 0
    
    print(f"\n{'='*60}")
    print("回测结果汇总")
    print(f"{'='*60}")
    print(f"\n【策略1】MACD金叉策略:")
    print(f"  总交易次数: {len(all_macd_trades)}")
    print(f"  达标率(8-15%): {macd_rate:.1f}%")
    print(f"  平均最大涨幅: {macd_avg_gain:.1f}%")
    
    print(f"\n【策略2】涨停回调策略:")
    print(f"  总交易次数: {len(all_limitup_trades)}")
    print(f"  5日平均收益: {lu_avg_gain:.2f}%")
    print(f"  胜率: {lu_win_rate:.1f}%")
    
    print(f"\n【融合策略】MACD+涨停回调:")
    print(f"  总交易次数: {len(fusion_trades)}")
    print(f"  MACD达标率: {fusion_rate:.1f}%")
    print(f"  5日平均收益: {fusion_avg_gain:.2f}%")
    print(f"  胜率: {fusion_win_rate:.1f}%")
    
    # === 第四阶段：选出今日最佳候选 ===
    print(f"\n{'='*60}")
    print("今日最佳候选股票 (2026-04-11)")
    print(f"{'='*60}")
    
    # 今日有K线数据的股票
    today_codes = []
    today_klines_map = {}
    for code in all_codes:
        klines = get_stock_klines(code)
        for k in klines:
            if k[0] == '2026-04-11':
                today_codes.append(code)
                today_klines_map[code] = klines
                break
    
    print(f"今日有数据股票: {len(today_codes)} 只")
    
    # 对今日每只股票进行双策略评分
    candidates = []
    
    for code in today_codes:
        klines = today_klines_map[code]
        prices = [row[4] for row in klines]
        dates = [row[0] for row in klines]
        today_idx = len(klines) - 1
        today_close = klines[today_idx][4]
        
        if today_close is None or today_close <= 0:
            continue
        
        score = 0
        reasons = []
        
        # 1. 涨停回调检查 (最近1-3天)
        is_lu, pullback, lookback = check_limit_up_pullback(klines, today_idx, (1, 3), 0.02)
        if is_lu:
            score += 40
            reasons.append(f"涨停回调{lookback}天,回调{pullback*100:.1f}%")
        
        # 2. MACD金叉检查 (最近30天内)
        has_macd = check_macd_momentum(prices, dates, today_idx, min_days=30)
        if has_macd:
            score += 30
            reasons.append("30日内MACD金叉")
        
        # 3. MACD当前状态 (DIF>0且在0轴上)
        macd_data = calc_macd(prices, 12, 26, 9)
        if len(macd_data) >= 2:
            last = macd_data[-1]
            if last and last[0] is not None and last[2] is not None:
                dea, macd, dif = last
                if dif > 0 and dea > 0:
                    score += 20
                    reasons.append(f"MACD多头(DIF>{dif:.2f})")
        
        # 4. 价格适中 (<=10元 + 低价格加分)
        if today_close <= 10:
            score += 10
            if today_close <= 5:
                score += 5
                reasons.append(f"低价{today_close}元(优质)")
            else:
                reasons.append(f"价格{today_close}元(适中)")
        
        if score >= 50:
            candidates.append({
                'code': code,
                'score': score,
                'close': today_close,
                'reasons': reasons,
                'limitup': is_lu,
                'macd': has_macd
            })
    
    # 按分数排序
    candidates.sort(key=lambda x: (-x['score'], -x['close']))
    
    print(f"\n候选股票 (分数>=50): {len(candidates)} 只")
    print()
    for i, c in enumerate(candidates[:10], 1):
        print(f"  {i}. {c['code']} 分数:{c['score']} 收盘:{c['close']}")
        print(f"     原因: {' | '.join(c['reasons'])}")
    
    # === 第五阶段：输出结果文件 ===
    results = {
        'version': 'V11',
        'timestamp': datetime.now().isoformat(),
        'strategy1': {
            'name': 'MACD金叉策略',
            'params': {'hold_days': 28, 'target_low': 0.08, 'target_high': 0.15, 'price_limit': 10.0},
            'total_trades': len(all_macd_trades),
            'hit_rate': round(macd_rate, 2),
            'avg_max_gain': round(macd_avg_gain, 2)
        },
        'strategy2': {
            'name': '涨停回调策略',
            'params': {'hold_days': 5, 'min_pullback': 0.02, 'pullback_days': '1-3', 'price_limit': 10.0},
            'total_trades': len(all_limitup_trades),
            'avg_gain_5d': round(lu_avg_gain, 2),
            'win_rate': round(lu_win_rate, 2)
        },
        'fusion': {
            'name': 'MACD+涨停回调融合',
            'total_trades': len(fusion_trades),
            'macd_hit_rate': round(fusion_rate, 2),
            'avg_gain_5d': round(fusion_avg_gain, 2),
            'win_rate': round(fusion_win_rate, 2),
            'improvement': round(fusion_rate - 34.2, 1)  # vs MACD单策略34.2%
        },
        'today_candidates': candidates[:20],
        'top_pick': candidates[0] if candidates else None
    }
    
    with open('data/v11_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到 data/v11_results.json")
    
    # 打印最佳选股
    if candidates:
        best = candidates[0]
        print(f"\n🏆 今日最佳: {best['code']} (分数:{best['score']})")
        print(f"   收盘价: {best['close']}元")
        print(f"   原因: {' | '.join(best['reasons'])}")
    
    return results

if __name__ == '__main__':
    main()
