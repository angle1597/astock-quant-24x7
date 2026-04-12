# 飞书通知配置指南

## 1. 创建飞书机器人

### 步骤

1. 打开飞书群聊
2. 点击群设置 (右上角 ⚙️)
3. 选择「群机器人」
4. 点击「添加机器人」
5. 选择「自定义机器人」
6. 设置机器人名称 (如: "量化选股助手")
7. 复制 Webhook URL

### Webhook URL 格式
```
https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

## 2. 配置环境变量

### 方法A: 系统环境变量 (推荐)

**Windows (PowerShell)**:
```powershell
[Environment]::SetEnvironmentVariable("FEISHU_WEBHOOK_URL", "https://open.feishu.cn/open-apis/bot/v2/hook/your-hook-id", "User")
```

**Linux/Mac**:
```bash
echo 'export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/your-hook-id"' >> ~/.bashrc
source ~/.bashrc
```

### 方法B: .env 文件

在项目根目录创建 `.env` 文件:
```
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/your-hook-id
```

### 方法C: 直接传入

在代码中直接传入:
```python
from feishu_notify import FeishuNotifier

notifier = FeishuNotifier(webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/your-hook-id")
```

## 3. 测试通知

```bash
cd C:\Users\Administrator\.qclaw\workspace\quant-24x7
python feishu_notify.py
```

如果配置正确，飞书群会收到测试消息。

## 4. 消息类型

| 类型 | 说明 | 触发时机 |
|------|------|----------|
| 📈 选股结果 | 每日选股TOP10 | 每天 9:20 |
| 🔔 盘中异动 | 涨跌超过3%的股票 | 交易时段每30分钟 |
| 📊 回测报告 | 策略回测结果 | 每周日 20:00 |
| ⚠️ 错误告警 | 系统错误 | 发生错误时 |

## 5. 自定义消息模板

可以在 `feishu_notify.py` 中修改消息格式:

```python
def send_stock_pick(self, picks: List[Dict], date: str) -> bool:
    # 自定义标题
    title = f"📈 {date} 选股结果"
    
    # 自定义内容格式
    lines = [
        f"**日期**: {date}",
        f"**选股数量**: {len(picks)}只",
        # 添加更多自定义内容...
    ]
    
    return self.send_markdown(title, "\n".join(lines))
```

## 6. 安全设置 (可选)

### IP白名单
在飞书机器人设置中添加服务器IP白名单，增强安全性。

### 签名验证
如需更高安全性，可以启用签名验证:

```python
import hmac
import hashlib
import base64
import time

def generate_signature(timestamp: str, secret: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(hmac_code).decode('utf-8')

# 发送时添加签名
timestamp = str(int(time.time()))
sign = generate_signature(timestamp, "your-secret")

message = {
    "timestamp": timestamp,
    "sign": sign,
    "msg_type": "text",
    "content": {"text": "测试消息"}
}
```

## 7. 故障排查

### 问题: 消息发送失败

**检查项**:
1. Webhook URL 是否正确
2. 网络是否能访问 open.feishu.cn
3. 机器人是否被移除
4. 消息格式是否符合飞书规范

### 问题: 收不到消息

**检查项**:
1. 环境变量是否设置成功
2. 是否在交易时段 (非交易时段不发送监控)
3. 选股结果是否为空

## 8. 多群通知

如需发送到多个群，可以配置多个 Webhook:

```python
WEBHOOKS = [
    "https://open.feishu.cn/open-apis/bot/v2/hook/group1",
    "https://open.feishu.cn/open-apis/bot/v2/hook/group2",
]

for url in WEBHOOKS:
    notifier = FeishuNotifier(url)
    notifier.send_stock_pick(picks, date)
```
