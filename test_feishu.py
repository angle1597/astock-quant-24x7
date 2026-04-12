# -*- coding: utf-8 -*-
"""
飞书通知测试脚本
测试飞书Webhook是否正常工作
"""
import os
import sys
import requests
from datetime import datetime

# 设置编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def test_webhook():
    """测试飞书Webhook"""
    
    # 获取Webhook URL
    webhook_url = os.environ.get('FEISHU_WEBHOOK_URL')
    
    if not webhook_url:
        print("❌ 未配置 FEISHU_WEBHOOK_URL")
        print("\n请先配置Webhook URL:")
        print("  PowerShell: [Environment]::SetEnvironmentVariable('FEISHU_WEBHOOK_URL', '你的URL', 'User')")
        print("  或在代码中: notifier = FeishuNotifier('你的URL')")
        return False
    
    print(f"✅ Webhook URL: {webhook_url[:50]}...")
    
    # 发送测试消息
    test_message = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🧪 飞书通知测试"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n**状态**: ✅ 连接成功！\n\n这是一条测试消息，用于验证飞书通知配置是否正确。"
                },
                {
                    "tag": "divider"
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "来自量化选股系统"
                        }
                    ]
                }
            ]
        }
    }
    
    try:
        print("\n📤 发送测试消息...")
        response = requests.post(
            webhook_url,
            json=test_message,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('StatusCode') == 0:
                print("✅ 消息发送成功!")
                print(f"   响应: {result}")
                return True
            else:
                print(f"❌ 发送失败: {result}")
                return False
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False


def create_test_group_message():
    """创建测试群消息卡片"""
    
    webhook_url = os.environ.get('FEISHU_WEBHOOK_URL')
    if not webhook_url:
        print("❌ 未配置 Webhook URL")
        return
    
    # 群通知卡片
    message = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "📊 量化选股系统通知"
                },
                "template": "green"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": "**系统状态**: 运行中 ✅\n**测试时间**: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                },
                {
                    "tag": "divider"
                },
                {
                    "tag": "markdown", 
                    "content": "**通知类型**: 测试消息\n**功能**: 验证飞书机器人配置"
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "查看详情"
                            },
                            "type": "primary"
                        }
                    ]
                }
            ]
        }
    }
    
    try:
        resp = requests.post(webhook_url, json=message, timeout=10)
        print("📤 群消息卡片发送:", resp.json())
    except Exception as e:
        print(f"❌ 发送失败: {e}")


def test_with_sample_picks():
    """用示例选股结果测试"""
    
    webhook_url = os.environ.get('FEISHU_WEBHOOK_URL')
    if not webhook_url:
        print("❌ 未配置 Webhook URL")
        return
    
    # 示例选股结果
    picks = [
        {'code': '002083', 'name': '孚日股份', 'price': 12.82, 'change_pct': 6.83, 'score': 115},
        {'code': '002701', 'name': '奥瑞金', 'price': 5.40, 'change_pct': 6.09, 'score': 110},
        {'code': '002104', 'name': '恒宝股份', 'price': 16.30, 'change_pct': 5.91, 'score': 110},
    ]
    
    # 构建Markdown表格
    lines = [
        f"**日期**: {datetime.now().strftime('%Y-%m-%d')}",
        f"**选股数量**: {len(picks)}只",
        "",
        "| 排名 | 代码 | 名称 | 现价 | 涨幅 | 评分 |",
        "|:---:|:---:|:---:|:---:|:---:|:---:|"
    ]
    
    for i, stock in enumerate(picks, 1):
        lines.append(f"| {i} | {stock['code']} | {stock['name']} | {stock['price']:.2f} | {stock['change_pct']:+.2f}% | {stock['score']} |")
    
    message = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text", 
                    "content": "📈 选股结果通知"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": "\n".join(lines)
                },
                {
                    "tag": "divider"
                },
                {
                    "tag": "markdown",
                    "content": "⚠️ 市场环境评分30分，建议观望"
                }
            ]
        }
    }
    
    try:
        resp = requests.post(webhook_url, json=message, timeout=10)
        print("📤 选股结果发送:", resp.json())
    except Exception as e:
        print(f"❌ 发送失败: {e}")


if __name__ == '__main__':
    print("="*60)
    print("飞书通知测试")
    print("="*60)
    
    # 测试1: 基础连接测试
    print("\n[测试1] 基础连接测试")
    success = test_webhook()
    
    if success:
        # 测试2: 群消息卡片
        print("\n[测试2] 群消息卡片")
        create_test_group_message()
        
        # 测试3: 选股结果卡片
        print("\n[测试3] 选股结果卡片")
        test_with_sample_picks()
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
