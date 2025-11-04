#!/usr/bin/env python3
"""
测试多工具调用功能
"""

import asyncio
import sys
import os

# 添加当前目录到路径
sys.path.append(os.path.dirname(__file__))

from mcp_true_stream_client import MCPTrueStreamClient

async def test_multi_tool_calls():
    """测试多工具调用功能"""
    print("正在测试多工具调用功能...")
    
    client = MCPTrueStreamClient()
    
    # 从配置文件加载服务器
    print("[INFO] 正在从配置文件加载 MCP 服务器...")
    success = await client.load_servers_from_config()
    
    if not success:
        print("[ERROR] 无法加载任何 MCP 服务器")
        return
    
    print(f"[INFO] 成功加载 {len(client.servers)} 个服务器，{len(client.all_tools)} 个工具")
    
    # 测试用例
    test_cases = [
        "查询员工D0005的姓名和当前位置",
        "告诉我D0001的姓名和位置",
        "查询D0002的姓名和位置信息",
        "获取D0003的姓名和当前位置"
    ]
    
    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"测试用例: {test_case}")
        print(f"{'='*60}")
        
        try:
            print("🤖 Assistant: ", end='', flush=True)
            result = await client.process_query_true_stream(test_case)
            print()  # 空行
            
        except Exception as e:
            print(f"[ERROR] 测试失败: {e}")
    
    print("\n测试完成！")

if __name__ == "__main__":
    asyncio.run(test_multi_tool_calls())
