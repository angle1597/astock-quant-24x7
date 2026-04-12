# -*- coding: utf-8 -*-
"""
飞书通知模块
Feishu Notification Module for quant-24x7
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional

class FeishuNotifier:
    """飞书通知器"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        初始化
        
        Args:
            webhook_url: 飞书机器人Webhook URL
                        获取方式: 飞书群 → 设置 → 群机器人 → 添加机器人 → 自定义机器人
        """
        self.webhook_url = webhook_url or os.environ.get('FEISHU_WEBHOOK_URL')
        
        if not self.webhook_url:
            print("[Warning] FEISHU_WEBHOOK_URL not configured, notifications disabled")
            self.enabled = False
        else:
            self.enabled = True
    
    def send_message(self, content: Dict) -> bool:
        """
        发送消息到飞书
        
        Args:
            content: 消息内容 (飞书消息格式)
        
        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            return False
        
        try:
            response = requests.post(
                self.webhook_url,
                json=content,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('StatusCode') == 0:
                    return True
                else:
                    print(f"[Feishu] Error: {result}")
                    return False
            else:
                print(f"[Feishu] HTTP Error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[Feishu] Exception: {e}")
            return False
    
    def send_text(self, text: str) -> bool:
        """
        发送文本消息
        
        Args:
            text: 文本内容
        
        Returns:
            bool: 是否发送成功
        """
        content = {
            "msg_type": "text",
            "content": {
                "text": text
            }
        }
        return self.send_message(content)
    
    def send_markdown(self, title: str, content: str) -> bool:
        """
        发送Markdown消息
        
        Args:
            title: 标题
            content: Markdown内容
        
        Returns:
            bool: 是否发送成功
        """
        message = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": content
                    }
                ]
            }
        }
        return self.send_message(message)
    
    def send_stock_pick(self, picks: List[Dict], date: str) -> bool:
        """
        发送选股结果
        
        Args:
            picks: 选股结果列表
            date: 日期
        
        Returns:
            bool: 是否发送成功
        """
        if not picks:
            return self.send_text(f"📊 {date} 选股完成，今日无符合条件的股票")
        
        # 构建Markdown内容
        lines = [
            f"**日期**: {date}",
            f"**选股数量**: {len(picks)}只",
            "",
            "| 排名 | 代码 | 名称 | 现价 | 涨幅 | 评分 |",
            "|:---:|:---:|:---:|:---:|:---:|:---:|"
        ]
        
        for i, stock in enumerate(picks[:10], 1):  # 最多显示10只
            code = stock.get('code', '')
            name = stock.get('name', '')
            price = stock.get('price', 0)
            change = stock.get('change_pct', 0)
            score = stock.get('score', 0)
            
            lines.append(f"| {i} | {code} | {name} | {price:.2f} | {change:+.2f}% | {score} |")
        
        content = "\n".join(lines)
        
        return self.send_markdown(f"📈 {date} 选股结果", content)
    
    def send_monitoring(self, stocks: List[Dict], time_str: str) -> bool:
        """
        发送盘中监控结果
        
        Args:
            stocks: 监控股票列表
            time_str: 时间
        
        Returns:
            bool: 是否发送成功
        """
        if not stocks:
            return False
        
        # 筛选有异动的股票
        alerts = [s for s in stocks if abs(s.get('change_pct', 0)) > 3]
        
        if not alerts:
            return False  # 无异动不发送
        
        lines = [
            f"**时间**: {time_str}",
            f"**异动股票**: {len(alerts)}只",
            "",
            "| 代码 | 名称 | 涨幅 | 异动 |",
            "|:---:|:---:|:---:|:---:|"
        ]
        
        for stock in alerts[:5]:
            code = stock.get('code', '')
            name = stock.get('name', '')
            change = stock.get('change_pct', 0)
            alert = "📈大涨" if change > 3 else "📉大跌"
            
            lines.append(f"| {code} | {name} | {change:+.2f}% | {alert} |")
        
        content = "\n".join(lines)
        
        return self.send_markdown(f"🔔 盘中异动提醒 {time_str}", content)
    
    def send_backtest_result(self, result: Dict) -> bool:
        """
        发送回测结果
        
        Args:
            result: 回测结果
        
        Returns:
            bool: 是否发送成功
        """
        lines = [
            f"**回测周期**: {result.get('period', '')}",
            f"**总交易次数**: {result.get('total_trades', 0)}",
            f"**胜率**: {result.get('win_rate', 0):.1%}",
            f"**平均收益**: {result.get('avg_return', 0):.2%}",
            f"**最大回撤**: {result.get('max_drawdown', 0):.2%}",
            "",
            "**优化建议**:",
        ]
        
        suggestions = result.get('suggestions', [])
        for s in suggestions[:3]:
            lines.append(f"- {s}")
        
        content = "\n".join(lines)
        
        return self.send_markdown("📊 策略回测报告", content)
    
    def send_error_alert(self, error_type: str, error_msg: str) -> bool:
        """
        发送错误告警
        
        Args:
            error_type: 错误类型
            error_msg: 错误信息
        
        Returns:
            bool: 是否发送成功
        """
        content = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "⚠️ 系统错误告警"
                    },
                    "template": "red"
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": f"**错误类型**: {error_type}\n**错误信息**: {error_msg}\n**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                ]
            }
        }
        return self.send_message(content)


# 全局实例
_notifier = None

def get_notifier(webhook_url: Optional[str] = None) -> FeishuNotifier:
    """获取飞书通知器实例"""
    global _notifier
    if _notifier is None:
        _notifier = FeishuNotifier(webhook_url)
    return _notifier


# 测试
if __name__ == '__main__':
    # 测试发送
    notifier = get_notifier()
    
    # 测试文本消息
    notifier.send_text("🧪 飞书通知测试成功!")
    
    # 测试选股结果
    test_picks = [
        {'code': '000001', 'name': '平安银行', 'price': 10.5, 'change_pct': 2.5, 'score': 85},
        {'code': '000002', 'name': '万科A', 'price': 8.2, 'change_pct': 1.8, 'score': 80},
    ]
    notifier.send_stock_pick(test_picks, "2026-04-08")
