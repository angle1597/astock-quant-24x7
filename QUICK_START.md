# A股量化系统自动化运行指南

## 快速启动

### 方式1: 手动运行
```powershell
# 进入项目目录
cd C:\Users\Administrator\.qclaw\workspace\quant-24x7

# 运行优化版选股
py deep_pick_v5.py

# 运行策略组合分析
py strategy_ensemble.py

# 运行回测
py backtest_runner_v2.py
```

### 方式2: 自动运行 (24/7)
```powershell
# 启动自动化运行器
py auto_runner.py

# 后台运行 (推荐)
Start-Process py -ArgumentList "auto_runner.py" -WindowStyle Hidden
```

### 方式3: Windows任务计划
```powershell
# 创建每日早盘选股任务 (每天9:20)
$action = New-ScheduledTaskAction -Execute "py" -Argument "C:\Users\Administrator\.qclaw\workspace\quant-24x7\deep_pick_v5.py" -WorkingDirectory "C:\Users\Administrator\.qclaw\workspace\quant-24x7"
$trigger = New-ScheduledTaskTrigger -Daily -At 09:20
Register-ScheduledTask -TaskName "DailyStockPick" -Action $action -Trigger $trigger -User "Administrator" -Force

# 创建每周回测任务 (每周日20:00)
$action2 = New-ScheduledTaskAction -Execute "py" -Argument "C:\Users\Administrator\.qclaw\workspace\quant-24x7\backtest_runner_v2.py" -WorkingDirectory "C:\Users\Administrator\.qclaw\workspace\quant-24x7"
$trigger2 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 20:00
Register-ScheduledTask -TaskName "WeeklyBacktest" -Action $action2 -Trigger $trigger2 -User "Administrator" -Force
```

## 模块说明

### 核心模块
| 模块 | 功能 | 用途 |
|------|------|------|
| deep_pick_v5.py | 优化版选股 | 放宽条件+止损建议 |
| strategy_ensemble.py | 多策略组合 | 综合评分 |
| stop_loss.py | 止损策略 | 风险控制 |
| market_filter.py | 市场判断 | 环境过滤 |
| feishu_notify.py | 飞书通知 | 结果推送 |

### 数据模块
| 模块 | 功能 |
|------|------|
| data_collector.py | 多源数据采集 |
| backtest_engine.py | 策略回测 |
| technical_analysis.py | 技术指标计算 |

### 配置文件
| 文件 | 内容 |
|------|------|
| requirements.txt | Python依赖 |
| data/picks_*.json | 选股结果 |
| data/backtest_v2_results.json | 回测结果 |

## 飞书通知配置

1. 创建飞书群机器人
2. 复制 Webhook URL
3. 设置环境变量:
```powershell
[Environment]::SetEnvironmentVariable("FEISHU_WEBHOOK_URL", "https://open.feishu.cn/open-apis/bot/v2/hook/your-hook-id", "User")
```

4. 测试通知:
```powershell
py -c "from feishu_notify import get_notifier; get_notifier().send_text('测试通知')"
```

## 通知类型

| 类型 | 触发时机 | 内容 |
|------|----------|------|
| 选股结果 | 每天9:20 | TOP 10股票 |
| 盘中异动 | 每30分钟 | 涨跌>3% |
| 回测报告 | 每周日20:00 | 胜率、收益 |
| 错误告警 | 实时 | 错误信息 |

## 数据存储

```
data/
├── stocks.db          # SQLite数据库
├── picks_*.json       # 选股结果
├── backtest_*.json    # 回测结果
└── optimized_*.json  # 优化参数

logs/
├── collector.log      # 数据采集日志
├── auto_runner.log    # 运行日志
└── backtest.log       # 回测日志
```

## 故障排查

### 问题: 选股结果为空
**原因**: 市场休市或数据未更新
**解决**: 检查 `data/stocks.db` 是否有最新数据

### 问题: 飞书通知失败
**原因**: Webhook URL未配置或机器人被移除
**解决**: 检查环境变量和群机器人状态

### 问题: 回测无交易
**原因**: 历史数据不足
**解决**: 运行 `py data_collector.py` 采集更多数据

## 下一步

- [ ] 配置飞书通知
- [ ] 设置定时任务
- [ ] 验证回测效果
- [ ] 小资金实盘测试
