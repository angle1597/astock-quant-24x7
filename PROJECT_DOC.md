# A股量化选股系统 - 项目文档

**版本**: v8.0 (2026-04-10)
**状态**: 🟢 运行中

---

## 一、项目概述

### 目标
- 每周精选3只股票
- 目标收益: 每周涨幅30%+
- 风控: 止损-5%、止盈+10%

### 核心功能
1. 多源数据采集 (东方财富、同花顺、新浪)
2. 多策略选股 (趋势、资金、动量、基本面)
3. 风险控制 (止损、止盈、时间止损)
4. 自动化运行 (定时任务、飞书通知)

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      量化选股系统 v8                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  数据层                    策略层                   输出层       │
│  ─────                    ─────                   ─────       │
│  data_collector.py       comprehensive_pick_v8.py  → 选股结果│
│  money_flow_pick_v7.py   strategy_ensemble.py      → 组合评分│
│  deep_pick_v5.py         stop_loss.py             → 止损建议 │
│                                                              │
│  风控层                    自动化                    通知层    │
│  ─────                    ─────                    ─────      │
│  market_filter.py        setup_tasks.py           → 飞书推送 │
│  stop_loss.py            daily_workflow.py        → 定时执行  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、选股策略

### v5: 基础优化选股
```python
# 筛选条件
price: 2-50元
market_cap: 20-200亿
change: -3%~10%
turnover: >2%
```

### v6: 智能选股
- 趋势动量 (40分)
- 成交量 (25分)
- 主力资金 (20分)
- 超跌反弹 (15分)

### v7: 资金流专项
- 主力净流入排名
- 资金活跃度分析
- 追涨/抄底分类

### v8: 综合融合 (推荐)
| 维度 | 权重 | 指标 |
|------|------|------|
| 趋势 | 30分 | 涨幅 |
| 资金 | 30分 | 主力净流入 |
| 动量 | 25分 | 换手率 |
| 基本面 | 15分 | 市盈率 |

---

## 四、风控机制

### 止损策略
```python
class StopLoss:
    fixed_stop = -0.05      # 固定止损 -5%
    trailing_stop = 0.03     # 移动止盈 3%
    max_hold_days = 5        # 时间止损 5天
```

### 市场过滤
```python
class MarketFilter:
    # 综合评分 = 趋势(40%) + 动量(30%) + 情绪(30%)
    # <40: 观望, 40-60: 持有, >60: 买入
```

---

## 五、文件清单

### 核心脚本
| 文件 | 功能 | 版本 |
|------|------|------|
| comprehensive_pick_v8.py | 综合选股 | v8 |
| money_flow_pick_v7.py | 资金流选股 | v7 |
| deep_pick_v5.py | 基础选股 | v5 |
| strategy_ensemble.py | 策略组合 | - |
| stop_loss.py | 止损策略 | - |
| market_filter.py | 市场过滤 | - |
| backtest_v3.py | 回测模拟 | v3 |

### 自动化
| 文件 | 功能 |
|------|------|
| setup_tasks.py | 定时任务配置 |
| daily_workflow.py | 每日工作流 |
| auto_runner.py | 24/7运行 |

### 通知
| 文件 | 功能 |
|------|------|
| feishu_notify.py | 飞书通知 |
| test_feishu.py | 通知测试 |

### 配置
| 文件 | 功能 |
|------|------|
| QUICK_START.md | 快速启动 |
| FEISHU_SETUP.md | 飞书配置 |
| FEISHU_QUICK_START.md | 飞书快速配置 |

---

## 六、使用指南

### 1. 每日选股
```powershell
cd C:\Users\Administrator\.qclaw\workspace\quant-24x7

# 综合选股 v8 (推荐)
py comprehensive_pick_v8.py

# 资金流选股 v7
py money_flow_pick_v7.py

# 基础选股 v5
py deep_pick_v5.py
```

### 2. 配置飞书通知
1. 在飞书群创建机器人
2. 复制 Webhook URL
3. 配置环境变量:
```powershell
[Environment]::SetEnvironmentVariable("FEISHU_WEBHOOK_URL", "你的URL", "User")
```
4. 测试通知:
```powershell
py test_feishu.py
```

### 3. 配置定时任务
```powershell
py setup_tasks.py
# 选择 1 创建定时任务
```

---

## 七、选股结果

### 数据存储
```
data/
├── picks_*.json              # v5选股结果
├── money_flow_picks_*.json   # v7资金流结果
├── comprehensive_picks_*.json # v8综合结果
├── backtest_*.json           # 回测结果
└── workflow_*.json          # 工作流日志
```

### 今日选股 (2026-04-10)
| 排名 | 代码 | 名称 | 涨幅 | 主力流入 | 评分 |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 600749 | 西藏旅游 | +7.2% | 1.1亿 | 95 |
| 2 | 603123 | 翠微股份 | +5.8% | 1469万 | 95 |
| 3 | 600590 | 泰豪科技 | +5.2% | 1.1亿 | 95 |
| 4 | 002083 | 孚日股份 | +6.8% | 1.1亿 | 95 |
| 5 | 002104 | 恒宝股份 | +5.9% | 1.1亿 | 95 |

---

## 八、下一步计划

### 短期
- [ ] 配置飞书通知
- [ ] 设置定时任务
- [ ] 回测验证

### 中期
- [ ] 小资金实盘测试
- [ ] 策略参数优化
- [ ] 增加更多数据源

### 长期
- [ ] 机器学习预测
- [ ] 组合优化
- [ ] 实盘对接

---

## 九、联系方式

如有问题，请查看:
- `QUICK_START.md` - 快速启动
- `FEISHU_QUICK_START.md` - 飞书配置

---

**文档更新**: 2026-04-10
**版本**: v8.0
