# A股24/7自动化量化选股系统
## Auto-Trading System v3.0

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    24/7 自动化运行核心                            │
├─────────────────────────────────────────────────────────────────┤
│  数据层                                                           │
│  ├── 东方财富爬虫 (push2.eastmoney.com)                          │
│  ├── 同花顺爬虫 (d.10jqka.com.cn)                               │
│  ├── 新浪财经爬虫 (finance.sina.com.cn)                         │
│  ├── 腾讯证券 (stockapp.finance.qq.com)                         │
│  ├── 网易财经 (money.163.com)                                   │
│  └── Tushare API (备用)                                         │
├─────────────────────────────────────────────────────────────────┤
│  策略层                                                           │
│  ├── 基础筛选 (市值, 股价, 板块过滤)                             │
│  ├── 技术指标 (MA, MACD, KDJ, RSI, BOLL)                       │
│  ├── 资金流分析 (主力净流入, 超大单, 大单)                       │
│  ├── 情绪指标 (涨停数, 跌停数, 涨跌停比)                        │
│  └── ML预测 (LightGBM, 随机森林)                                │
├─────────────────────────────────────────────────────────────────┤
│  执行层                                                           │
│  ├── 每日选股 (9:30前完成)                                      │
│  ├── 盘中监控 (每15分钟)                                         │
│  ├── 策略优化 (每周自动回测+调参)                               │
│  └── 报告生成 (飞书/微信推送)                                    │
└─────────────────────────────────────────────────────────────────┘
```

## 数据获取策略

### 1. 东方财富 (主力数据源)
```python
# 实时行情
url = "https://push2.eastmoney.com/api/qt/clist/get"
# 参数: pn=页码, pz=每页数量, fs=市场筛选, fields=字段
```

### 2. 同花顺 (基本面数据)
```python
# 财务数据
url = "https://d.10jqka.com.cn/v6/line/hs_{code}/01/last20.js"
```

### 3. 新浪财经 (实时行情)
```python
# 实时价格
url = "https://hq.sinajs.cn/list={code}"
```

### 4. 腾讯证券 (资金流)
```python
# 资金流向
url = "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfund/FundDetail"
```

## 自动化任务

| 任务 | 时间 | 频率 |
|------|------|------|
| 早盘选股 | 09:15 | 每日 |
| 盘中监控 | 09:30-15:00 | 每15分钟 |
| 尾盘总结 | 15:05 | 每日 |
| 数据采集 | 全天 | 每小时 |
| 策略回测 | 周日 20:00 | 每周 |
| 策略优化 | 周一 08:00 | 每周 |
| 模型训练 | 每月1日 | 每月 |

## 安装依赖

```bash
pip install requests pandas numpy scikit-learn lightgbm
pip install akshare efinance baostock tushare
pip install schedule apscheduler
```

## 运行

```bash
# 启动24/7运行
python auto_runner.py

# 只运行数据采集
python data_collector.py

# 只运行策略回测
python backtest_engine.py
```

## 数据存储

- SQLite: 历史K线, 选股结果
- CSV: 每日报告, 回测结果
- JSON: 配置, API响应缓存
