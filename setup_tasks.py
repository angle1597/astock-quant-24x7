# -*- coding: utf-8 -*-
"""
定时任务配置 - Windows任务计划程序
"""
import os
import sys
import subprocess

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def create_scheduled_tasks():
    """创建Windows定时任务"""
    
    project_path = r"C:\Users\Administrator\.qclaw\workspace\quant-24x7"
    
    tasks = [
        {
            'name': 'DailyStockPick',
            'description': '每日选股 - 综合选股v8',
            'script': 'comprehensive_pick_v8.py',
            'trigger': 'Daily',
            'time': '09:20',
            'days': None
        },
        {
            'name': 'WeeklyBacktest',
            'description': '每周回测验证',
            'script': 'backtest_runner_v2.py',
            'trigger': 'Weekly',
            'time': '20:00',
            'days': 'Sunday'
        },
        {
            'name': 'MoneyFlowPick',
            'description': '资金流选股每日',
            'script': 'money_flow_pick_v7.py',
            'trigger': 'Daily',
            'time': '14:30',
            'days': None
        }
    ]
    
    print("="*60)
    print("创建Windows定时任务")
    print("="*60)
    
    for task in tasks:
        print(f"\n创建任务: {task['name']}")
        print(f"  脚本: {task['script']}")
        print(f"  时间: {task['time']}")
        
        # 构建命令
        cmd = [
            'powershell',
            '-ExecutionPolicy', 'Bypass',
            '-Command',
            f'''
            $action = New-ScheduledTaskAction -Execute "py" -Argument "{task['script']}" -WorkingDirectory "{project_path}"
            $trigger = New-ScheduledTaskTrigger -{"Daily" if task['trigger'] == 'Daily' else 'Weekly"} -At {task['time']}{f" -DaysOfWeek {task['days']}" if task['days'] else ""}
            $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
            Register-ScheduledTask -TaskName "{task['name']}" -Action $action -Trigger $trigger -Settings $settings -Description "{task['description']}" -User "Administrator" -Force
            '''
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"  ✅ 创建成功")
            else:
                print(f"  ❌ 创建失败: {result.stderr}")
        except Exception as e:
            print(f"  ❌ 异常: {e}")
    
    print("\n" + "="*60)
    print("任务创建完成")
    print("="*60)


def list_tasks():
    """列出已创建的任务"""
    print("\n已创建的定时任务:")
    print("-"*40)
    
    cmd = ['powershell', '-Command', 'Get-ScheduledTask | Where-Object {$_.TaskName -like "*Stock*" -or $_.TaskName -like "*Backtest*" -or $_.TaskName -like "*MoneyFlow*"} | Select-Object TaskName, State, TaskPath | Format-Table -AutoSize']
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(result.stdout)
    except Exception as e:
        print(f"❌ 列出任务失败: {e}")


def delete_tasks():
    """删除所有定时任务"""
    print("\n删除定时任务...")
    
    tasks = ['DailyStockPick', 'WeeklyBacktest', 'MoneyFlowPick']
    
    for task_name in tasks:
        cmd = ['powershell', '-Command', f'Unregister-ScheduledTask -TaskName "{task_name}" -Confirm:$false']
        try:
            subprocess.run(cmd, capture_output=True, timeout=10)
            print(f"  删除: {task_name}")
        except:
            pass
    
    print("✅ 删除完成")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("量化系统定时任务配置")
    print("="*60)
    
    print("\n选项:")
    print("  1. 创建定时任务")
    print("  2. 列出已创建任务")
    print("  3. 删除所有任务")
    print("  4. 退出")
    
    choice = input("\n请选择 (1-4): ").strip()
    
    if choice == '1':
        create_scheduled_tasks()
    elif choice == '2':
        list_tasks()
    elif choice == '3':
        delete_tasks()
    else:
        print("退出")
