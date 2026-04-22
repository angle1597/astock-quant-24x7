# ============================================================
# 量化选股策略优化挑战系统
# Quantitative Stock Strategy Optimization Challenge
# ============================================================
# 
# 目标：设计一个高效、自动化的策略优化工作流
# 原则：
#   1. 分层优化：先粗筛(快速)再精筛(精准)
#   2. 并行回测：同时测试多个条件组合
#   3. 增量验证：在最优基础上微调
#   4. 过拟合检测：确保样本统计显著
#
# ============================================================

STRATEGY_CHALLENGE = {
    "name": "量化选股策略优化挑战",
    "version": "1.0",
    
    # 核心指标目标
    "targets": {
        "10pct_rate": 60,      # 10%达标率目标 (%)
        "30pct_rate": 40,       # 30%达标率目标 (%)
        "win_rate": 75,         # 胜率目标 (%)
        "min_trades": 100,     # 最小交易数(统计显著)
        "avg_return": 20,       # 平均收益目标 (%)
    },
    
    # 优化阶段
    "phases": [
        {
            "name": "Phase 1: 因子发现",
            "duration": "1-2天",
            "goal": "找出有效因子",
            "methods": [
                "- 单因子测试(每个因子独立评估)",
                "- 简单条件组合(2-3个因子)",
                "- 快速粗筛(阈值宽松)",
            ],
            "target_count": 10,  # 目标发现10个有效因子
        },
        {
            "name": "Phase 2: 组合优化",
            "duration": "2-3天",
            "goal": "找到最优组合",
            "methods": [
                "- 网格搜索(Grid Search)",
                "- 逐步添加因子",
                "- 验证过拟合",
            ],
            "target_count": 5,  # 目标找到5个有效组合
        },
        {
            "name": "Phase 3: 精细调优",
            "duration": "3-5天",
            "goal": "参数微调+过拟合检测",
            "methods": [
                "- 参数扫描(阈值细化)",
                "- 样本外测试",
                "- 不同市场环境测试",
            ],
            "target_count": 3,  # 目标3个稳健策略
        },
        {
            "name": "Phase 4: 实盘验证",
            "duration": "长期",
            "goal": "实盘跟踪+持续优化",
            "methods": [
                "- 每日监控信号",
                "- 周度复盘",
                "- 月度策略调整",
            ],
        },
    ],
    
    # 已验证有效的因子(来自V91-V96)
    "verified_factors": {
        # 因子名: (基础达标率, 说明)
        "consec_4": (21.9, "连涨4天,基础信号"),
        "consec_3": (15.0, "连涨3天,更频繁信号"),
        "shrink": (+27.0, "缩量,增加10%达标率"),
        "range_shrink": (+10.0, "振幅收缩,额外提升"),
        "uniform": (+5.0, "均匀上涨,无暴涨"),
        "vol_ratio_60": (5.0, "量比<60%"),
        "rsi_filter": (5.0, "RSI过滤"),
        "price_10": (0, "价格<10元,小盘股"),
    },
    
    # 最优组合(来自V96)
    "best_combinations": {
        "V96": {
            "conditions": ["consec>=4", "shrink", "range_shrink"],
            "hold_days": 80,
            "10pct_rate": 65.1,
            "30pct_rate": 33.3,
            "win_rate": 71.4,
            "avg_return": 31.59,
            "trade_count": 63,
            "limitation": "信号极其稀少",
        },
        "V94": {
            "conditions": ["consec>=4", "shrink", "uniform", "range_shrink"],
            "hold_days": 60,
            "10pct_rate": 59.3,
            "30pct_rate": 22.0,
            "win_rate": 69.5,
            "avg_return": 25.13,
            "trade_count": 59,
            "limitation": "信号稀少",
        },
        "V90": {
            "conditions": ["consec>=3", "shrink", "score>=75"],
            "hold_days": 60,
            "10pct_rate": 44.6,
            "30pct_rate": 18.8,
            "win_rate": 69.3,
            "avg_return": 14.30,
            "trade_count": 1680,
            "limitation": "信号适中",
        },
    },
    
    # 优化策略
    "optimization_strategies": {
        "grid_search": "网格搜索: 系统性测试所有阈值组合",
        "bayesian": "贝叶斯优化: 智能搜索最优参数",
        "genetic": "遗传算法: 模拟进化找到最优组合",
        "ensemble": "集成学习: 多个策略组合",
        "regime_switch": "状态切换: 根据市场状态切换策略",
    },
    
    # 过拟合检测
    "overfitting_tests": {
        "train_test_split": "训练/测试集分割(80/20)",
        "walk_forward": "Walk-forward分析",
        "monte_carlo": "蒙特卡洛模拟",
        "sensitivity": "参数敏感性分析",
        "out_of_sample": "样本外验证",
    },
    
    # 效率优化
    "efficiency_tips": [
        "1. 预处理数据: 预先计算常用指标(RSI, MACD, 均线等)",
        "2. 向量化计算: 使用NumPy/Pandas批量计算",
        "3. 数据库索引: 为code, date添加索引",
        "4. 增量回测: 只回测变化的参数组合",
        "5. 缓存结果: 存储中间计算结果",
        "6. 并行计算: 使用multiprocessing多核并行",
        "7. 早停策略: 表现差的组合提前终止",
    ],
    
    # 挑战任务
    "challenges": [
        {
            "id": "C01",
            "name": "因子挖掘挑战",
            "description": "发现新的有效因子",
            "difficulty": "中等",
            "reward": "因子库+1",
        },
        {
            "id": "C02",
            "name": "过拟合检测挑战",
            "description": "确保策略稳健性",
            "difficulty": "困难",
            "reward": "策略可信度+1",
        },
        {
            "id": "C03",
            "name": "信号频率挑战",
            "description": "在保持高胜率同时增加信号频率",
            "difficulty": "极难",
            "reward": "突破性进展",
        },
        {
            "id": "C04",
            "name": "多策略组合挑战",
            "description": "设计策略组合覆盖不同市场",
            "difficulty": "困难",
            "reward": "系统鲁棒性+1",
        },
        {
            "id": "C05",
            "name": "实时数据挑战",
            "description": "接入盘中数据实现盘中选股",
            "difficulty": "中等",
            "reward": "时效性+1",
        },
    ],
}

def print_challenge():
    print("=" * 70)
    print("量化选股策略优化挑战系统 v1.0")
    print("=" * 70)
    print()
    print("目标: 10%达标率>60%, 30%达标率>40%, 胜率>75%")
    print()
    
    print("--- 优化阶段 ---")
    for phase in STRATEGY_CHALLENGE["phases"]:
        print(f"\n[{phase['name']}] {phase['duration']}")
        print(f"  目标: {phase['goal']}")
        print(f"  方法:")
        for m in phase["methods"]:
            print(f"    {m}")
    
    print("\n--- 已验证因子 ---")
    for factor, (rate, desc) in STRATEGY_CHALLENGE["verified_factors"].items():
        print(f"  {factor}: +{rate:.1f}% | {desc}")
    
    print("\n--- 当前最优策略 ---")
    for name, strat in STRATEGY_CHALLENGE["best_combinations"].items():
        print(f"\n  {name}:")
        print(f"    条件: {', '.join(strat['conditions'])}")
        print(f"    持有: {strat['hold_days']}天")
        print(f"    10%={strat['10pct_rate']:.1f}%, 30%={strat['30pct_rate']:.1f}%, 胜率={strat['win_rate']:.1f}%")
        print(f"    限制: {strat['limitation']}")
    
    print("\n--- 效率优化 ---")
    for tip in STRATEGY_CHALLENGE["efficiency_tips"]:
        print(f"  {tip}")
    
    print("\n--- 挑战任务 ---")
    for c in STRATEGY_CHALLENGE["challenges"]:
        print(f"  [{c['id']}] {c['name']} ({c['difficulty']})")
        print(f"      {c['description']}")
        print(f"      奖励: {c['reward']}")
    
    print("\n" + "=" * 70)
    print("下一步: 选择一个挑战开始!")
    print("=" * 70)

if __name__ == "__main__":
    print_challenge()
