"""
量化系统V11 - 双策略融合 V2
改进：更宽松的融合条件 + 今日候选扩展
"""

import sqlite3
import json
from datetime import datetime, timedelta

DB_PATH = 'data/stocks.db'

def get_db():
    return sqlite3.connect(DB_PATH)

def calc_ema(prices, period):
    if len(prices) < period:
        return None
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * (2/(period+1)) + ema * (1 - 2/(period+1))
    return ema

def calc_macd(prices, fast=12, slow=26, signal=9):
    """计算MACD，返回列表 [(dea, macd, dif), ...] 与prices对齐"""
    if len(prices) < slow + signal:
        return []
    
    difs = []
    for i in range(len(prices)):
        e12 = calc_ema(prices[:i+1], 12) if i+1 >= 12 else None
        e26 = calc_ema(prices[:i+1], 26) if i+1 >= 26 else None
        if e12 is not None and e26 is not None:
            difs.append(e12 - e26)
        else:
            difs.append(None)
    
    # DEA = EMA(DIF, 9)
    result = []
    valid_dea = None
    for i, dif in enumerate(difs):
        if dif is None:
            result.append(None)
        else:
            if valid_dea is None:
                valid_hist = [d for d in difs[:i] if d is not None]
                if len(valid_hist) >= signal:
                    valid_dea = sum(valid_hist[-signal:]) / signal
                elif len(valid_hist) > 0:
                    valid_dea = sum(valid_hist) / len(valid_hist)
                else:
                    valid_dea = dif
            
            if len(result) >= 1:
                valid_dea = valid_dea * (1 - 2/(signal+1)) + dif * (2/(signal+1))
            else:
                valid_hist = [d for d in difs[:i] if d is not None]
                if len(valid_hist) >= signal:
                    valid_dea = sum(valid_hist[-signal:]) / signal
            
            macd = (dif - valid_dea) * 2
            result.append((round(valid_dea, 4), round(macd, 4), round(dif, 4)))
    
    return result

def get_stock_klines(code):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT date, open, high, low, close, volume FROM kline WHERE code=? ORDER BY date ASC", (code,))
    rows = c.fetchall()
    conn.close()
    return rows

def is_limit_up(close, prev_close):
    if prev_close is None or prev_close <= 0 or close is None:
        return False
    return (close - prev_close) / prev_close >= 0.095

def check_macd_golden_cross_at_idx(macd_data, idx):
    """idx位置的MACD金叉: DIF从负转正 或 DIF上穿DEA"""
    if idx < 1 or idx >= len(macd_data) or macd_data[idx-1] is None or macd_data[idx] is None:
        return False
    dea_prev, macd_prev, dif_prev = macd_data[idx-1]
    dea_cur, macd_cur, dif_cur = macd_data[idx]
    if all(v is not None for v in [dif_prev, dif_cur, dea_prev, dea_cur]):
        return (dif_prev < 0 and dif_cur > 0) or (dif_prev < dea_prev and dif_cur > dea_cur)
    return False

def main():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT DISTINCT code FROM kline ORDER BY code")
    all_codes = [r[0] for r in c.fetchall()]
    conn.close()
    
    print("=" * 60)
    print("V11 双策略融合回测 (改进版)")
    print("=" * 60)
    print(f"共 {len(all_codes)} 只股票\n")
    
    all_macd_trades = []     # MACD单策略
    all_lu_trades = []       # 涨停回调单策略
    fusion_trades = []       # 融合策略
    
    for code in all_codes:
        klines = get_stock_klines(code)
        if len(klines) < 60:
            continue
        
        prices = [row[4] for row in klines]
        dates = [row[0] for row in klines]
        macd_data = calc_macd(prices, 12, 26, 9)
        
        if len(macd_data) < 10:
            continue
        
        for idx in range(35, len(klines) - 1):
            entry_price = klines[idx][4]
            if entry_price is None or entry_price <= 0 or entry_price > 10:
                continue
            
            # ===== MACD金叉 =====
            is_gc = check_macd_golden_cross_at_idx(macd_data, idx)
            
            # ===== 涨停检测 (向前1-3天) =====
            limitup_days = []
            for lb in range(1, 4):
                if idx - lb < 0:
                    break
                prev_close = klines[idx - lb - 1][4] if idx - lb - 1 >= 0 else None
                curr_close_lu = klines[idx - lb][4]
                if prev_close and is_limit_up(curr_close_lu, prev_close):
                    limitup_days.append(lb)
            
            # ===== 涨停回调检测 =====
            lu_pullback = False
            lu_pct = 0
            for lb in range(1, 4):
                if idx - lb < 0:
                    break
                prev_close = klines[idx - lb - 1][4] if idx - lb - 1 >= 0 else None
                curr_close_lu = klines[idx - lb][4]
                if prev_close and is_limit_up(curr_close_lu, prev_close):
                    # 从涨停日到现在回调幅度
                    curr_close_cur = klines[idx][4]
                    pullback = (curr_close_lu - curr_close_cur) / curr_close_lu
                    if pullback >= 0.02:
                        lu_pullback = True
                        lu_pct = pullback
                        lu_lb = lb
                        break
            
            if is_gc:
                # MACD单策略: 持有28天，看最大涨幅
                exit_idx = min(idx + 28, len(klines) - 1)
                entry = entry_price
                max_gain = max((klines[i][4] - entry) / entry for i in range(idx+1, exit_idx+1) if klines[i][4])
                hit = 0.08 <= max_gain <= 0.15
                all_macd_trades.append({
                    'code': code, 'date': dates[idx], 'entry': entry,
                    'max_gain': round(max_gain*100, 2), 'hit': hit
                })
                
                # 融合: MACD金叉 + 近期涨停(含回调)
                if limitup_days or lu_pullback:
                    # 持有5天看收益
                    exit5 = min(idx + 5, len(klines) - 1)
                    gains_5d = [(klines[i][4] - entry) / entry for i in range(idx+1, exit5+1) if klines[i][4]]
                    avg_5d = sum(gains_5d) / len(gains_5d) if gains_5d else 0
                    win_5d = sum(1 for g in gains_5d if g > 0) / len(gains_5d) if gains_5d else 0
                    fusion_trades.append({
                        'code': code, 'date': dates[idx], 'entry': entry,
                        'macd_gc': True,
                        'limitup_days': limitup_days,
                        'pullback': round(lu_pct*100, 2) if lu_pullback else 0,
                        'avg_gain_5d': round(avg_5d*100, 2),
                        'win_rate_5d': round(win_5d*100, 1),
                        'macd_hit': hit,
                        'macd_max_gain': round(max_gain*100, 2)
                    })
            
            if lu_pullback:
                # 涨停回调单策略: 持有5天
                exit5 = min(idx + 5, len(klines) - 1)
                gains_5d = [(klines[i][4] - entry_price) / entry_price for i in range(idx+1, exit5+1) if klines[i][4]]
                if gains_5d:
                    avg_5d = sum(gains_5d) / len(gains_5d)
                    win_5d = sum(1 for g in gains_5d if g > 0) / len(gains_5d)
                    all_lu_trades.append({
                        'code': code, 'date': dates[idx], 'entry': entry_price,
                        'pullback': round(lu_pct*100, 2),
                        'lookback': lu_lb,
                        'avg_gain_5d': round(avg_5d*100, 2),
                        'win_rate_5d': round(win_5d*100, 1)
                    })
    
    # ========== 统计 ==========
    macd_rate = sum(1 for t in all_macd_trades if t['hit']) / len(all_macd_trades) * 100 if all_macd_trades else 0
    macd_avg = sum(t['max_gain'] for t in all_macd_trades) / len(all_macd_trades) if all_macd_trades else 0
    
    lu_avg = sum(t['avg_gain_5d'] for t in all_lu_trades) / len(all_lu_trades) if all_lu_trades else 0
    lu_win = sum(1 for t in all_lu_trades if t['avg_gain_5d'] > 0) / len(all_lu_trades) * 100 if all_lu_trades else 0
    
    fusion_rate = sum(1 for t in fusion_trades if t['macd_hit']) / len(fusion_trades) * 100 if fusion_trades else 0
    fusion_avg = sum(t['avg_gain_5d'] for t in fusion_trades) / len(fusion_trades) if fusion_trades else 0
    fusion_win = sum(1 for t in fusion_trades if t['avg_gain_5d'] > 0) / len(fusion_trades) * 100 if fusion_trades else 0
    
    # 融合 vs 单策略提升
    fusion_vs_macd = fusion_rate - macd_rate
    fusion_vs_lu = fusion_avg - lu_avg
    
    print(f"[MACD金叉策略] 次数:{len(all_macd_trades)} 达标率:{macd_rate:.1f}% 均涨幅:{macd_avg:.1f}%")
    print(f"[涨停回调策略] 次数:{len(all_lu_trades)} 均收益:{lu_avg:.2f}% 胜率:{lu_win:.1f}%")
    print(f"[融合策略]     次数:{len(fusion_trades)} MACD达标率:{fusion_rate:.1f}% 均收益:{fusion_avg:.2f}% 胜率:{fusion_win:.1f}%")
    print(f"融合相对MACD达标率提升: +{fusion_vs_macd:.1f}%")
    print(f"融合相对涨停回调收益提升: +{fusion_vs_lu:.2f}%")
    
    # ========== 今日候选 ==========
    print(f"\n{'='*60}")
    print("今日候选 (2026-04-11)")
    print("="*60)
    
    # 今日有数据的股票 (扩展到最近几天)
    today_date = '2026-04-11'
    candidates_all = []
    
    for code in all_codes:
        klines = get_stock_klines(code)
        prices = [row[4] for row in klines]
        dates = [row[0] for row in klines]
        
        # 用最后一天作为"今日"
        if len(klines) < 10:
            continue
        today_idx = len(klines) - 1
        today_date_str = dates[today_idx]
        today_close = klines[today_idx][4]
        
        if today_close is None or today_close <= 0 or today_close > 10:
            continue
        
        macd_data = calc_macd(prices, 12, 26, 9)
        
        score = 0
        reasons = []
        tags = []
        
        # 涨停回调信号 (最近1-3天)
        for lb in range(1, 4):
            if today_idx - lb < 0:
                break
            prev_close = klines[today_idx - lb - 1][4] if today_idx - lb - 1 >= 0 else None
            lu_close = klines[today_idx - lb][4]
            if prev_close and is_limit_up(lu_close, prev_close):
                pullback = (lu_close - today_close) / lu_close
                score += 40
                tags.append(f'涨停回调{lb}天')
                reasons.append(f"{lb}天前涨停({round((lu_close-prev_close)/prev_close*100,1)}%),当前回调{round(pullback*100,1)}%")
                break
        
        # MACD金叉 (最近30天内)
        gc_found = False
        for look_idx in range(max(35, today_idx - 30), today_idx):
            if check_macd_golden_cross_at_idx(macd_data, look_idx):
                gc_found = True
                gc_date = dates[look_idx]
                days_since = today_idx - look_idx
                score += 30
                tags.append('MACD金叉')
                reasons.append(f"近{days_since}天MACD金叉({gc_date})")
                break
        
        # MACD当前多头
        if len(macd_data) >= 2 and macd_data[-1]:
            dea, macd, dif = macd_data[-1]
            if dif and dea and dif > 0 and dea > 0:
                score += 20
                tags.append('MACD多头')
                reasons.append(f"MACD多头排列(DIF>{round(dif,2)})")
        
        # 价格优势
        if today_close <= 5:
            score += 15
            tags.append('低价')
            reasons.append(f"低价{round(today_close,2)}元(优质)")
        elif today_close <= 10:
            score += 10
            reasons.append(f"价格{round(today_close,2)}元")
        
        # 成交量放大
        if len(klines) >= 6:
            vol_today = klines[today_idx][5]
            vol_avg5 = sum(klines[i][5] for i in range(today_idx-4, today_idx+1) if klines[i][5]) / 5
            if vol_today and vol_avg5 and vol_today > vol_avg5 * 1.5:
                score += 10
                tags.append('放量')
                reasons.append(f"放量({round(vol_today/vol_avg5,1)}x均量)")
        
        if score >= 40:
            candidates_all.append({
                'code': code,
                'score': score,
                'close': round(today_close, 2),
                'date': today_date_str,
                'reasons': reasons,
                'tags': tags,
                'macd_gc': 'MACD金叉' in tags,
                'lu_pullback': '涨停回调' in tags
            })
    
    candidates_all.sort(key=lambda x: (-x['score'], -x['close']))
    
    print(f"候选股票: {len(candidates_all)} 只\n")
    for i, c in enumerate(candidates_all[:15], 1):
        print(f"  {i:2d}. {c['code']} 评分:{c['score']} 价:{c['close']} [{','.join(c['tags'])}]")
        for r in c['reasons']:
            print(f"       - {r}")
    
    # ========== 保存 ==========
    results = {
        'version': 'V11',
        'timestamp': datetime.now().isoformat(),
        'stats': {
            'macd': {'trades': len(all_macd_trades), 'hit_rate': round(macd_rate,2), 'avg_gain': round(macd_avg,2)},
            'limitup': {'trades': len(all_lu_trades), 'avg_gain': round(lu_avg,2), 'win_rate': round(lu_win,1)},
            'fusion': {'trades': len(fusion_trades), 'macd_hit_rate': round(fusion_rate,2), 'avg_gain': round(fusion_avg,2), 'win_rate': round(fusion_win,1)}
        },
        'fusion_improvement': {
            'vs_macd_rate': round(fusion_vs_macd, 1),
            'vs_lu_avg': round(fusion_vs_lu, 2)
        },
        'today_candidates': candidates_all[:20],
        'top_pick': candidates_all[0] if candidates_all else None
    }
    
    with open('data/v11_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存 data/v11_results.json")
    
    if candidates_all:
        best = candidates_all[0]
        print(f"\n[TOP PICK] {best['code']} 评分:{best['score']} 收盘:{best['close']}")
        for r in best['reasons']:
            print(f"  - {r}")

if __name__ == '__main__':
    main()
