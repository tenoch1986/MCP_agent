#!/usr/bin/env python3
"""
测试修复后的服务器管理器功能
"""

import json
import os
import sys
import time
from mcp_server_manager import MCPServerManager

def test_server_manager():
    """测试服务器管理器功能"""
    print("=" * 60)
    print("测试服务器管理器修复")
    print("=" * 60)
    
    # 创建管理器实例
    manager = MCPServerManager()
    
    print("\n1. 列出当前服务器状态:")
    servers = manager.list_servers()
    for server in servers:
        print(f"  - {server['name']}: {server['status']} (健康: {server['health']})")
    
    print("\n2. 测试服务器发现功能:")
    manager.discover_running_servers()
    
    print("\n3. 再次列出服务器状态:")
    servers = manager.list_servers()
    for server in servers:
        print(f"  - {server['name']}: {server['status']} (健康: {server['health']})")
    
    print("\n4. 检查配置文件内容:")
    if os.path.exists("mcp_servers.json"):
        with open("mcp_servers.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print("配置文件中的服务器:")
        for name, data in config.items():
            print(f"  - {name}: {data.get('status', 'unknown')} (端口: {data.get('port', 'N/A')})")
    
    print("\n5. 测试重复服务器检测:")
    # 检查是否有重复的服务器
    port_servers = {}
    for name, config in manager.servers.items():
        if config.port:
            if config.port in port_servers:
                print(f"⚠️  发现重复端口 {config.port}: {port_servers[config.port]} 和 {name}")
            else:
                port_servers[config.port] = name
    
    print(f"\n✅ 测试完成！共管理 {len(manager.servers)} 个服务器")

if __name__ == "__main__":
    test_server_manager()
