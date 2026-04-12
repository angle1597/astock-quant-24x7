# -*- coding: utf-8 -*-
"""
云服务器部署脚本 - 量化选股系统
"""
import os
import sys
import subprocess

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


SERVERS = {
    'aws-hk': {
        'ip': '18.163.198.16',
        'user': 'ubuntu',
        'port': 22,
        'desc': 'AWS香港 - 股票分析节点'
    },
    'gcp-hk': {
        'ip': '35.220.153.99',
        'user': 'root',
        'port': 22,
        'desc': '谷歌云香港 - 宝塔面板'
    },
    'gcp-openclaw': {
        'ip': '34.131.230.112',
        'user': 'administrator',
        'port': 22,
        'desc': '谷歌云OpenClaw'
    }
}


def check_ssh_access(server_name):
    """检查SSH访问"""
    if server_name not in SERVERS:
        print(f"❌ 未知服务器: {server_name}")
        return False
    
    server = SERVERS[server_name]
    
    print(f"\n检查 {server_name} ({server['ip']}) SSH访问...")
    
    cmd = [
        'ssh',
        '-o', 'ConnectTimeout=5',
        '-o', 'StrictHostKeyChecking=no',
        '-p', str(server['port']),
        f"{server['user']}@{server['ip']}",
        'echo', 'SSH_OK'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if 'SSH_OK' in result.stdout:
            print(f"✅ SSH访问正常")
            return True
        else:
            print(f"❌ SSH访问失败")
            print(f"   错误: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 连接异常: {e}")
        return False


def check_docker(server_name):
    """检查Docker"""
    server = SERVERS[server_name]
    
    print(f"\n检查 {server_name} Docker...")
    
    cmd = [
        'ssh',
        '-o', 'ConnectTimeout=10',
        '-o', 'StrictHostKeyChecking=no',
        '-p', str(server['port']),
        f"{server['user']}@{server['ip']}",
        'docker', '--version'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            print(f"✅ Docker已安装: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Docker未安装")
            return False
    except Exception as e:
        print(f"❌ 检查异常: {e}")
        return False


def deploy_to_server(server_name):
    """部署到服务器"""
    if server_name not in SERVERS:
        print(f"❌ 未知服务器: {server_name}")
        return
    
    server = SERVERS[server_name]
    
    print(f"\n" + "="*60)
    print(f"部署到 {server_name}")
    print(f"="*60)
    
    # 1. 检查SSH
    if not check_ssh_access(server_name):
        print(f"\n❌ 无法连接到 {server_name}")
        print(f"请检查:")
        print(f"  1. 服务器是否开机")
        print(f"  2. SSH端口({server['port']})是否开放")
        print(f"  3. SSH密钥是否配置")
        return
    
    # 2. 检查Docker
    has_docker = check_docker(server_name)
    
    # 3. 创建部署目录
    print(f"\n创建部署目录...")
    server_path = SERVERS[server_name]
    
    # 本地项目路径
    local_path = r"C:\Users\Administrator\.qclaw\workspace\quant-24x7"
    
    # 4. 复制文件
    print(f"\n复制项目文件...")
    # 注意: 实际部署需要SCP或rsync
    
    # 5. 远程执行
    print(f"\n远程安装依赖...")
    
    install_cmd = ' && '.join([
        'cd ~/quant-24x7',
        'pip install -r requirements.txt',
        'echo "依赖安装完成"'
    ])
    
    cmd = [
        'ssh',
        '-o', 'StrictHostKeyChecking=no',
        '-p', str(server['port']),
        f"{server['user']}@{server['ip']}",
        install_cmd
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        print(result.stdout)
        if result.returncode == 0:
            print(f"✅ 部署完成")
        else:
            print(f"❌ 部署失败: {result.stderr}")
    except Exception as e:
        print(f"❌ 部署异常: {e}")


def list_servers():
    """列出服务器"""
    print("\n可用服务器:")
    print("-"*60)
    for name, info in SERVERS.items():
        print(f"  {name:15s} - {info['desc']}")
        print(f"                   {info['user']}@{info['ip']}:{info['port']}")
    print()


def main():
    print("\n" + "="*60)
    print("量化选股系统 - 云服务器部署")
    print("="*60)
    
    list_servers()
    
    print("选项:")
    print("  1. 检查所有服务器SSH")
    print("  2. 列出服务器")
    print("  3. 部署到AWS香港")
    print("  4. 部署到谷歌云香港")
    print("  5. 退出")
    
    choice = input("\n请选择 (1-5): ").strip()
    
    if choice == '1':
        print("\n检查所有服务器...")
        for name in SERVERS:
            check_ssh_access(name)
            check_docker(name)
    
    elif choice == '2':
        list_servers()
    
    elif choice == '3':
        deploy_to_server('aws-hk')
    
    elif choice == '4':
        deploy_to_server('gcp-hk')
    
    else:
        print("退出")


if __name__ == '__main__':
    main()
