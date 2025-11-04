#!/usr/bin/env python3
"""
MCP 多服务器客户端 - 真正的流式输出版本

功能特性：
1. 自动从配置文件加载所有 MCP 服务器
2. 支持动态工具发现和路由
3. 使用 LLM 自动决定工具调用
4. 真正的流式输出处理过程
"""

import asyncio
import os
import sys
import json
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()

class MCPTransportType(Enum):
    """MCP 传输类型"""
    SSE = "sse"
    STDIO = "stdio"

@dataclass
class MCPToolInfo:
    """MCP 工具信息"""
    name: str
    description: str
    parameters: Dict[str, Any]
    server_name: str  # 所属服务器名称
    
    def __str__(self):
        return f"{self.name} (来自 {self.server_name}): {self.description}"

@dataclass
class MCPServerInfo:
    """MCP 服务器信息"""
    name: str
    description: str
    transport_type: MCPTransportType
    url_or_command: str
    tools: List[MCPToolInfo] = None
    
    def __post_init__(self):
        if self.tools is None:
            self.tools = []

class MCPTrueStreamClient:
    """
    MCP 多服务器客户端 - 真正的流式输出版本
    支持连接和管理多个 MCP 服务器，提供真正的流式输出体验
    """
    
    def __init__(self, llm_model: str = "deepseek-chat"):
        self.llm = ChatDeepSeek(
            model=llm_model,
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            temperature=0.7
        )
        
        self.servers: Dict[str, MCPServerInfo] = {}
        self.all_tools: Dict[str, MCPToolInfo] = {}  # 工具名 -> 工具信息
        self.config_file = "mcp_servers.json"
        self.log_file = "mcp_true_stream_debug.log"
        
        # 清空日志文件
        self._clear_log()
        
    def _clear_log(self):
        """清空日志文件"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write("MCP 真正流式客户端调试日志\n")
            f.write("=" * 50 + "\n\n")
    
    def _log_context(self, step_name, data):
        """记录上下文数据"""
        import json
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n[{timestamp}] {step_name}\n")
            f.write("-" * 40 + "\n")
            f.write(json.dumps(data, ensure_ascii=False, indent=2))
            f.write("\n" + "=" * 50 + "\n")
    
    def _stream_print(self, message: str, delay: float = 0.1):
        """流式打印消息，模拟打字机效果"""
        import sys
        for char in message:
            print(char, end='', flush=True)
            time.sleep(delay)
        print()  # 换行
        
    async def load_servers_from_config(self) -> bool:
        """从配置文件加载所有服务器"""
        if not os.path.exists(self.config_file):
            print(f"[ERROR] 配置文件不存在: {self.config_file}")
            print("请先运行 MCP 服务器管理器来创建配置")
            return False
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            print(f"[INFO] 从配置加载 {len(config_data)} 个服务器")
            
            for server_name, server_config in config_data.items():
                # 检查服务器是否运行
                if server_config.get('status') != 'running':
                    print(f"[WARN] 服务器 {server_name} 未运行，跳过")
                    continue
                    
                server_info = MCPServerInfo(
                    name=server_name,
                    description=server_config.get('description', ''),
                    transport_type=MCPTransportType(server_config.get('transport_type', 'sse')),
                    url_or_command=server_config.get('url') or server_config.get('command', '')
                )
                
                # 连接到服务器并获取工具列表
                success = await self._connect_and_load_tools(server_info)
                if success:
                    self.servers[server_name] = server_info
                    print(f"[SUCCESS] 加载服务器 {server_name}: {len(server_info.tools)} 个工具")
                else:
                    print(f"[ERROR] 连接服务器 {server_name} 失败")
                    
            print(f"[INFO] 总共加载了 {len(self.all_tools)} 个工具")
            return len(self.servers) > 0
            
        except Exception as e:
            print(f"[ERROR] 加载配置文件失败: {e}")
            return False
            
    async def _connect_and_load_tools(self, server_info: MCPServerInfo) -> bool:
        """连接到服务器并加载工具列表"""
        try:
            if server_info.transport_type == MCPTransportType.SSE:
                return await self._connect_sse(server_info)
            elif server_info.transport_type == MCPTransportType.STDIO:
                return await self._connect_stdio(server_info)
            else:
                print(f"[ERROR] 不支持的传输类型: {server_info.transport_type}")
                return False
                
        except Exception as e:
            print(f"[ERROR] 连接服务器 {server_info.name} 失败: {e}")
            return False
            
    async def _connect_sse(self, server_info: MCPServerInfo) -> bool:
        """连接到 SSE 服务器"""
        try:
            async with sse_client(url=server_info.url_or_command, timeout=30.0) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # 获取工具列表
                    tools_response = await session.list_tools()
                    for tool in tools_response.tools:
                        tool_info = MCPToolInfo(
                            name=tool.name,
                            description=tool.description or "No description",
                            parameters=tool.inputSchema or {},
                            server_name=server_info.name
                        )
                        server_info.tools.append(tool_info)
                        self.all_tools[tool.name] = tool_info
                        
                    return True
                    
        except Exception as e:
            print(f"[ERROR] SSE 连接失败: {e}")
            return False
            
    async def _connect_stdio(self, server_info: MCPServerInfo) -> bool:
        """连接到 STDIO 服务器"""
        try:
            cmd_parts = server_info.url_or_command.split()
            server_params = StdioServerParameters(
                command=cmd_parts[0],
                args=cmd_parts[1:] if len(cmd_parts) > 1 else []
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # 获取工具列表
                    tools_response = await session.list_tools()
                    for tool in tools_response.tools:
                        tool_info = MCPToolInfo(
                            name=tool.name,
                            description=tool.description or "No description",
                            parameters=tool.inputSchema or {},
                            server_name=server_info.name
                        )
                        server_info.tools.append(tool_info)
                        self.all_tools[tool.name] = tool_info
                        
                    return True
                    
        except Exception as e:
            print(f"[ERROR] STDIO 连接失败: {e}")
            return False
            
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """调用指定的 MCP 工具"""
        if tool_name not in self.all_tools:
            return f"错误：工具 {tool_name} 不存在"
            
        tool_info = self.all_tools[tool_name]
        server_info = self.servers.get(tool_info.server_name)
        
        if not server_info:
            return f"错误：服务器 {tool_info.server_name} 未连接"
            
        try:
            if server_info.transport_type == MCPTransportType.SSE:
                return await self._call_tool_sse(server_info, tool_name, arguments)
            elif server_info.transport_type == MCPTransportType.STDIO:
                return await self._call_tool_stdio(server_info, tool_name, arguments)
            else:
                return f"错误：不支持的传输类型 {server_info.transport_type}"
                
        except Exception as e:
            return f"调用工具失败: {e}"
            
    async def _call_tool_sse(self, server_info: MCPServerInfo, tool_name: str, arguments: Dict[str, Any]) -> str:
        """通过 SSE 调用工具"""
        async with sse_client(url=server_info.url_or_command, timeout=30.0) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                # 提取文本内容
                if hasattr(result.content, '__iter__') and len(result.content) > 0:
                    return result.content[0].text
                else:
                    return str(result.content)
                
    async def _call_tool_stdio(self, server_info: MCPServerInfo, tool_name: str, arguments: Dict[str, Any]) -> str:
        """通过 STDIO 调用工具"""
        cmd_parts = server_info.url_or_command.split()
        server_params = StdioServerParameters(
            command=cmd_parts[0],
            args=cmd_parts[1:] if len(cmd_parts) > 1 else []
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return result.content
                
    async def process_query_true_stream(self, user_input: str) -> str:
        """处理用户查询的智能逻辑 - 真正的流式输出版本"""
        
        # 记录用户输入
        self._log_context("1. 用户输入", {"user_input": user_input})
        
        # 构建工具列表描述
        tools_list = "\n".join([f"- {tool.name}: {tool.description} (来自 {tool.server_name})" 
                              for tool in self.all_tools.values()])
        
        system_message = f"""你是一个智能助手，可以访问各种工具来帮助用户。

可用的工具：
{tools_list}

使用指南：
1. 分析用户请求，判断是否需要使用工具
2. 如果需要使用工具，请使用以下格式调用：
<function_calls>
<invoke name="工具名称">
<parameter name="参数名">参数值</parameter>
</invoke>
</function_calls>

3. 保持对话自然流畅，用中文回复"""

        # 记录工具列表详细信息
        tools_details = []
        for tool in self.all_tools.values():
            tools_details.append({
                "name": tool.name,
                "description": tool.description,
                "server": tool.server_name,
                "parameters": tool.parameters
            })
        
        # 记录 system prompt 和工具列表
        self._log_context("1.1 System Prompt", {"system_message": system_message})
        self._log_context("1.2 可用工具列表", {"tools": tools_details})
        
        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=user_input)
        ]
        
        try:
            # 流式输出初始思考
            self._stream_print("🤔 正在思考...", 0.05)
            
            # 使用真正的流式输出
            full_response = ""
            async for chunk in self.llm.astream(messages):
                if hasattr(chunk, 'content'):
                    content = chunk.content
                    if content:
                        # 真正的流式输出
                        print(content, end='', flush=True)
                        full_response += content
            
            print()  # 换行
            
            self._log_context("2. LLM 初始响应", {"response": full_response})
            
            # 检查是否包含工具调用
            if "<function_calls>" in full_response and "</function_calls>" in full_response:
                # 提取工具调用信息
                tool_calls = self._extract_tool_calls(full_response)
                self._log_context("3. 提取的工具调用", {"tool_calls": tool_calls})
                
                if tool_calls:
                    # 流式输出工具调用信息
                    for tool_call in tool_calls:
                        tool_name = tool_call["name"]
                        arguments = tool_call["arguments"]
                        self._stream_print(f"🔧 正在调用工具: {tool_name}", 0.03)
                        self._stream_print(f"   参数: {arguments}", 0.02)
                    
                    # 执行工具调用
                    tool_results = []
                    for tool_call in tool_calls:
                        tool_name = tool_call["name"]
                        arguments = tool_call["arguments"]
                        
                        print(f"[INFO] 调用工具: {tool_name} 参数: {arguments}")
                        tool_result = await self.call_tool(tool_name, arguments)
                        tool_results.append({
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "result": tool_result
                        })
                    
                    self._log_context("4. 工具调用结果", {"tool_results": tool_results})
                    
                    # 流式输出工具结果
                    self._stream_print("✅ 工具调用完成", 0.05)
                    self._stream_print("🤔 正在整合结果...", 0.05)
                    
                    # 使用 LLM 加工工具结果 - 同样使用流式输出
                    final_result = await self._process_tool_results_with_true_stream(
                        user_input, tool_results, full_response
                    )
                    self._log_context("5. LLM 最终处理结果", {"final_result": final_result})
                    
                    return final_result
            
            # 如果没有工具调用，直接返回响应
            return full_response
            
        except Exception as e:
            error_msg = f"LLM 处理失败: {e}"
            self._log_context("ERROR", {"error": error_msg})
            self._stream_print(f"❌ {error_msg}", 0.05)
            return error_msg
    
    async def _process_tool_results_with_true_stream(self, user_input: str, tool_results: List[Dict], original_response: str) -> str:
        """使用 LLM 加工工具调用结果 - 真正的流式输出版本"""
        # 构建工具结果描述
        tool_results_text = ""
        for result in tool_results:
            tool_results_text += f"工具 {result['tool_name']} 返回结果: {result['result']}\n"
        
        system_message = f"""你是一个智能助手。你刚刚调用了工具来回答用户的问题。

原始响应：{original_response}
工具调用结果：
{tool_results_text}

请根据工具返回的结果，用自然流畅的中文回答用户的原始问题。请准确反映工具返回的信息，不要添加或修改工具返回的具体数据内容。"""

        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=f"用户的问题：{user_input}")
        ]
        
        try:
            # 使用真正的流式输出
            final_result = ""
            async for chunk in self.llm.astream(messages):
                if hasattr(chunk, 'content'):
                    content = chunk.content
                    if content:
                        # 真正的流式输出
                        print(content, end='', flush=True)
                        final_result += content
            
            print()  # 换行
            return final_result
            
        except Exception as e:
            return f"处理工具结果失败: {e}"
    
    def _extract_tool_calls(self, response_content: str) -> List[Dict[str, Any]]:
        """从 LLM 响应中提取工具调用信息"""
        import re
        
        tool_calls = []
        
        # 查找所有工具调用块
        function_call_pattern = r'<function_calls>(.*?)</function_calls>'
        function_call_matches = re.findall(function_call_pattern, response_content, re.DOTALL)
        
        for call_block in function_call_matches:
            # 提取工具名称
            tool_name_pattern = r'<invoke name="([^"]+)">'
            tool_name_match = re.search(tool_name_pattern, call_block)
            
            if tool_name_match:
                tool_name = tool_name_match.group(1)
                arguments = {}
                
                # 提取参数
                param_pattern = r'<parameter name="([^"]+)">([^<]+)</parameter>'
                param_matches = re.findall(param_pattern, call_block)
                
                for param_name, param_value in param_matches:
                    arguments[param_name] = param_value
                
                tool_calls.append({
                    "name": tool_name,
                    "arguments": arguments
                })
        
        return tool_calls
            
    def list_servers_and_tools(self):
        """列出所有服务器和工具"""
        print("\n" + "=" * 50)
        print("已连接的 MCP 服务器和工具")
        print("=" * 50)
        
        for server_name, server_info in self.servers.items():
            print(f"\n📡 {server_name}: {server_info.description}")
            print(f"   传输类型: {server_info.transport_type.value}")
            print(f"   地址: {server_info.url_or_command}")
            print(f"   工具 ({len(server_info.tools)} 个):")
            for tool in server_info.tools:
                print(f"     - {tool.name}: {tool.description}")

async def main():
    """主程序"""
    client = MCPTrueStreamClient()
    
    print("=" * 60)
    print("MCP 真正流式输出客户端")
    print("=" * 60)
    
    # 从配置文件加载服务器
    print("[INFO] 正在从配置文件加载 MCP 服务器...")
    success = await client.load_servers_from_config()
    
    if not success:
        print("[ERROR] 无法加载任何 MCP 服务器")
        print("请确保：")
        print("  1. 已运行 MCP 服务器管理器: python mcp_server_manager.py")
        print("  2. 已启动需要的 MCP 服务器")
        print("  3. 配置文件 mcp_servers.json 存在且正确")
        sys.exit(1)
    
    # 显示服务器和工具信息
    client.list_servers_and_tools()
    
    print("\n" + "=" * 40)
    print("MCP 真正流式输出客户端已就绪！")
    print("=" * 40)
    print("示例查询：")
    print("  - 北京今天天气如何？")
    print("  - 上海的温度怎么样？")
    print("  - 查询员工D0005的位置")
    print("  - 输入 'quit' 退出")
    print()
    
    # 交互循环
    while True:
        try:
            user_input = input("💬 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                break
            if not user_input:
                continue
            
            print("🤖 Assistant: ", end='', flush=True)
            await client.process_query_true_stream(user_input)
            print()  # 空行
            
        except KeyboardInterrupt:
            print("\n[INFO] 用户中断")
            break
        except Exception as e:
            print(f"[ERROR] 处理查询时出错: {e}\n")
    
    print("[INFO] 程序已退出")

if __name__ == "__main__":
    asyncio.run(main())
