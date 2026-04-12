# 飞书通知完整配置指南

**更新**: 2026-04-10

---

## 一分钟快速配置

### 步骤1: 创建飞书机器人

1. 打开任意飞书群聊
2. 点击群设置 (右上角 ⚙️)
3. 选择「群机器人」
4. 点击「添加机器人」→「自定义机器人」
5. 设置名称: `量化选股助手`
6. 复制 Webhook URL (格式: `https://open.feishu.cn/open-apis/bot/v2/hook/xxx`)

### 步骤2: 配置Webhook URL

**方式A - 临时测试** (重启后失效):
```powershell
$env:FEISHU_WEBHOOK_URL = "你的Webhook URL"
cd C:\Users\Administrator\.qclaw\workspace\quant-24x7
py test_feishu.py
```

**方式B - 永久配置** (推荐):
```powershell
[Environment]::SetEnvironmentVariable(
    "FEISHU_WEBHOOK_URL", 
    "你的Webhook URL", 
    "User"
)
```

### 步骤3: 验证配置

```powershell
cd C:\Users\Administrator\.qclaw\workspace\quant-24x7
py test_feishu.py
```

看到 "✅ 消息发送成功" 即配置成功！

---

## 飞书机器人创建详细步骤

### 图文教程

```
飞书群聊
    ↓
点击右上角「···」或「设置」
    ↓
选择「群机器人」
    ↓
点击「添加机器人」
    ↓
选择「自定义机器人」(最后一个)
    ↓
设置名称: 量化选股助手
    ↓
点击「添加」
    ↓
复制 Webhook URL
```

### Webhook URL 示例
```
https://open.feishu.cn/open-apis/bot/v2/hook/7c1b34e5-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

---

## 通知功能一览

| 功能 | 触发时机 | 内容 |
|------|----------|------|
| 📈 选股结果 | 每天9:20 | TOP 10股票 |
| 🔔 盘中异动 | 每30分钟 | 涨跌>3%提醒 |
| 📊 回测报告 | 每周日20:00 | 胜率、收益 |
| ⚠️ 错误告警 | 实时 | 系统错误 |

---

## 测试脚本

```powershell
cd C:\Users\Administrator\.qclaw\workspace\quant-24x7
py test_feishu.py
```

测试内容:
1. 基础连接测试
2. 群消息卡片
3. 选股结果卡片

---

## 常见问题

### Q: 消息发送失败?
**A**: 检查Webhook URL是否正确，是否被移除

### Q: 重启后配置失效?
**A**: 使用永久配置方式: `[Environment]::SetEnvironmentVariable(..., 'User')`

### Q: 群机器人不见了?
**A**: 机器人可能被管理员移除，需要重新创建

---

## 完成后验证

运行测试后，飞书群应该收到:

1. **基础测试消息**: "飞书通知测试"
2. **群通知卡片**: "量化选股系统通知"  
3. **选股结果卡片**: 包含3只股票的表格

---

**配置完成后告诉我，我来验证通知是否正常工作！**
