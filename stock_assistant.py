# -*- coding: utf-8 -*-
"""
选股助手 - 智能分析和建议
"""
import os
import sys
import json
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def load_latest_picks():
    """加载最新选股结果"""
    data_dir = r"C:\Users\Administrator\.qclaw\workspace\quant-24x7\data"
    
    # 查找最新文件
    import glob
    
    patterns = [
        f"{data_dir}/comprehensive_picks_*.json",
        f"{data_dir}/money_flow_picks_*.json",
        f"{data_dir}/picks_*.json"
    ]
    
    latest_file = None
    latest_time = 0
    
    for pattern in patterns:
        for f in glob.glob(pattern):
            mtime = os.path.getmtime(f)
            if mtime > latest_time:
                latest_time = mtime
                latest_file = f
    
    if latest_file:
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f), os.path.basename(latest_file)
    
    return None, None


def analyze_pick(stock):
    """分析单只股票"""
    code = stock['code']
    name = stock.get('name', '')
    price = stock.get('price', 0)
    change = stock.get('change_pct', 0)
    main_inflow = stock.get('main_inflow', 0)
    main_inflow_wan = stock.get('main_inflow_wan', 0)
    turnover = stock.get('turnover', 0)
    market_cap = stock.get('market_cap', 0)
    score = stock.get('total_score', stock.get('score', 0))
    
    # 分析
    signals = []
    risks = []
    suggestions = []
    
    # 趋势分析
    if change >= 5:
        signals.append("强势上涨")
        if change >= 9:
            signals.append("接近涨停")
    elif change >= 3:
        signals.append("温和上涨")
    elif change > 0:
        signals.append("小幅上涨")
    else:
        risks.append("股价下跌")
    
    # 资金分析
    if main_inflow > 1e8:
        signals.append("主力大幅流入")
    elif main_inflow > 5000:
        signals.append("主力流入")
    elif main_inflow > 0:
        signals.append("资金正流入")
    else:
        risks.append("主力流出")
    
    # 活跃度
    if turnover >= 15:
        signals.append("高度活跃")
    elif turnover >= 8:
        signals.append("活跃")
    
    # 市值
    if 30 <= market_cap <= 100:
        signals.append("适中市值")
    elif market_cap > 150:
        risks.append("市值偏大")
    
    # 建议
    if change >= 5 and main_inflow > 0:
        suggestions.append("追涨策略")
    elif change < 0 and main_inflow > 0:
        suggestions.append("超跌反弹关注")
    if turnover >= 10:
        suggestions.append("短线交易机会")
    
    return {
        'signals': signals,
        'risks': risks,
        'suggestions': suggestions
    }


def generate_report():
    """生成分析报告"""
    print("\n" + "="*60)
    print("【选股助手 - 智能分析报告】")
    print("="*60)
    
    # 加载数据
    data, filename = load_latest_picks()
    
    if not data:
        print("\n❌ 未找到选股结果")
        return
    
    print(f"\n📁 数据源: {filename}")
    print(f"📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # 获取候选股票
    candidates = data.get('candidates', data.get('picks', []))
    
    if not candidates:
        print("\n❌ 无候选股票")
        return
    
    print(f"📊 候选股票: {len(candidates)}只")
    
    # TOP 5 分析
    print("\n" + "="*60)
    print("【TOP 5 详细分析】")
    print("="*60)
    
    for i, stock in enumerate(candidates[:5], 1):
        analysis = analyze_pick(stock)
        
        print(f"\n{'─'*40}")
        print(f"#{i} {stock.get('code', '')} {stock.get('name', '')}")
        print(f"{'─'*40}")
        
        # 基本信息
        price = stock.get('price', 0)
        change = stock.get('change_pct', 0)
        score = stock.get('total_score', stock.get('score', 0))
        
        if isinstance(score, dict):
            score = score.get('total', 0)
        
        print(f"  💰 现价: {price:.2f}元")
        print(f"  📈 涨幅: {change:+.2f}%")
        print(f"  ⭐ 评分: {score}")
        
        # 主力资金
        main_wan = stock.get('main_inflow_wan', 0)
        if main_wan >= 10000:
            print(f"  💵 主力流入: {main_wan/10000:.1f}亿")
        else:
            print(f"  💵 主力流入: {main_wan:.0f}万")
        
        # 分析结果
        if analysis['signals']:
            print(f"\n  ✅ 信号:")
            for s in analysis['signals']:
                print(f"     • {s}")
        
        if analysis['risks']:
            print(f"\n  ⚠️ 风险:")
            for r in analysis['risks']:
                print(f"     • {r}")
        
        if analysis['suggestions']:
            print(f"\n  💡 建议:")
            for s in analysis['suggestions']:
                print(f"     • {s}")
        
        # 止损建议
        if price > 0:
            stop = price * 0.95
            profit_1 = price * 1.05
            profit_2 = price * 1.10
            print(f"\n  🛡️ 止损建议:")
            print(f"     止损价: {stop:.2f} (-5%)")
            print(f"     止盈1: {profit_1:.2f} (+5%)")
            print(f"     止盈2: {profit_2:.2f} (+10%)")
    
    # 汇总
    print("\n" + "="*60)
    print("【汇总】")
    print("="*60)
    
    # 统计
    strong = len([c for c in candidates if c.get('change_pct', 0) >= 5])
    inflow = len([c for c in candidates if c.get('main_inflow', 0) > 0])
    high_score = len([c for c in candidates if (c.get('total_score', c.get('score', 0))) >= 80])
    
    print(f"\n  📊 强势股(涨幅>=5%): {strong}只")
    print(f"  📊 资金流入: {inflow}只")
    print(f"  📊 高评分(>=80): {high_score}只")
    
    # 推荐
    print("\n  🎯 今日推荐:")
    if candidates:
        top = candidates[0]
        print(f"     {top.get('code')} {top.get('name')} (评分{top.get('total_score', top.get('score', 0))})")
    
    print()


def chat_mode():
    """对话模式"""
    print("\n" + "="*60)
    print("【选股助手 - 对话模式】")
    print("="*60)
    print("\n输入股票代码查询，或输入 '退出' 结束")
    
    # 加载数据
    data, _ = load_latest_picks()
    candidates = data.get('candidates', data.get('picks', [])) if data else []
    
    stock_map = {s.get('code', ''): s for s in candidates}
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            if not user_input:
                continue
            
            if user_input in ['退出', 'exit', 'quit', 'q']:
                print("再见!")
                break
            
            # 查找股票
            if user_input in stock_map:
                stock = stock_map[user_input]
                analysis = analyze_pick(stock)
                
                print(f"\n{stock.get('name', '')} ({stock.get('code', '')})")
                print(f"现价: {stock.get('price', 0):.2f}元")
                print(f"涨幅: {stock.get('change_pct', 0):+.2f}%")
                
                if analysis['signals']:
                    print("\n信号:", ', '.join(analysis['signals']))
                if analysis['risks']:
                    print("风险:", ', '.join(analysis['risks']))
                if analysis['suggestions']:
                    print("建议:", ', '.join(analysis['suggestions']))
            else:
                print("未找到该股票，请输入股票代码(如 600749)")
        
        except KeyboardInterrupt:
            print("\n再见!")
            break
        except Exception as e:
            print(f"错误: {e}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='选股助手')
    parser.add_argument('--chat', action='store_true', help='对话模式')
    args = parser.parse_args()
    
    if args.chat:
        chat_mode()
    else:
        generate_report()
