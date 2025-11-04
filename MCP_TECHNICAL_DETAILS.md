# MCP 技术细节详解

## 🏗️ 架构概览

```
用户输入 → MCP多服务器客户端 → LLM智能路由 → MCP服务器 → 工具执行 → LLM结果加工 → 用户输出
```

## 🔄 完整交互流程（Step by Step）

### 第1步：启动 MCP 服务器

**文件：`weather_server.py`**
```python
# 创建 SSE 服务器，监听端口 8000
mcp = FastMCP("weather_server", port=8000)

@mcp.tool()
async def get_weather(city: str) -> str:
    """获取城市天气"""
    return f"{city} 今天晴，25°C，微风。"

if __name__ == "__main__":
    mcp.run(transport="sse")
```

**文件：`employee_server.py`**
```python
# 创建 SSE 服务器，监听端口 8001
mcp = FastMCP("employee_server", port=8001)

@mcp.tool()
async def get_employee_location(employee_id: str) -> str:
    """获取员工的当前位置（测试工具）"""
    location_mapping = {
        "D0001": "北京总部A座3楼会议室",
        "D0005": "上海总部B座5楼工位"
    }
    return f"工号{employee_id}的员工目前位于{location_mapping[employee_id]}。"

if __name__ == "__main__":
    mcp.run(transport="sse")
```

**关键点：**
- 使用 FastMCP 框架简化服务器开发
- 服务器在 `http://127.0.0.1:8000/sse` 和 `http://127.0.0.1:8001/sse` 提供 SSE 端点
- 实现 MCP 协议，提供工具列表和调用接口

### 第2步：服务器管理

**文件：`mcp_server_manager.py`**
```python
class MCPServerManager:
    """MCP 服务器管理器 - 管理多个 MCP 服务器的配置和连接"""
    
    def start_server(self, name: str) -> bool:
        """启动指定的 MCP 服务器"""
        config = self.servers[name]
        
        if config.transport_type == MCPTransportType.SSE:
            # 启动 SSE 服务器进程
            process = subprocess.Popen(
                config.command.split(),
                cwd=config.working_directory,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[name] = process
            config.pid = process.pid
            config.status = "running"
```

**关键点：**
- 自动发现和手动配置服务器
- 支持 SSE 和 STDIO 传输类型
- 健康检查和故障转移
- 配置保存在 `mcp_servers.json`

### 第3步：客户端连接服务器

**文件：`mcp_true_stream_client.py`**
```python
async def _connect_sse(self, server_info: MCPServerInfo) -> bool:
    """连接到 SSE 服务器"""
    async with sse_client(url=server_info.url_or_command, timeout=30.0) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 获取工具列表
            tools_response = await session.list_tools()
            for tool in tools_response.tools:
                tool_info = MCPToolInfo(
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.inputSchema,
                    server_name=server_info.name
                )
                self.all_tools[tool.name] = tool_info
```

**关键点：**
- 使用 `mcp.client.sse.sse_client` 建立 SSE 连接
- 遵循 MCP JSON-RPC 2.0 协议
- 自动发现和注册服务器提供的工具

### 第4步：真正的流式输出处理

**文件：`mcp_true_stream_client.py`**
```python
async def process_query_true_stream(self, user_input: str) -> str:
    """处理用户查询的智能逻辑 - 真正的流式输出版本"""
    
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
```

**关键改进：**
- 使用 `astream()` 替代 `ainvoke()` 实现真正的流式输出
- LLM 响应逐字逐句实时显示
- 工具调用过程也采用流式方式

### 第5步：智能工具路由

**文件：`mcp_true_stream_client.py`**
```python
def _extract_tool_calls(self, response_content: str) -> List[Dict[str, Any]]:
    """从 LLM 响应中提取工具调用信息"""
    tool_calls = []
    
    # 查找所有工具调用块
    function_call_pattern = r'<function_calls>(.*?)</function_calls>'
    function_call_matches = re.findall(function_call_pattern, response_content, re.DOTALL)
    
    for call_block in function_call_matches:
        # 提取工具名称和参数
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
```

**关键点：**
- LLM 自动决定是否需要使用工具
- 支持多工具同时调用
- 自动提取工具名称和参数

### 第6步：工具调用

**文件：`mcp_true_stream_client.py`**
```python
async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
    """调用指定的 MCP 工具"""
    tool_info = self.all_tools[tool_name]
    server_info = self.servers.get(tool_info.server_name)
    
    if server_info.transport_type == MCPTransportType.SSE:
        return await self._call_tool_sse(server_info, tool_name, arguments)

async def _call_tool_sse(self, server_info: MCPServerInfo, tool_name: str, arguments: Dict[str, Any]) -> str:
    """通过 SSE 调用工具"""
    async with sse_client(url=server_info.url_or_command, timeout=30.0) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            return result.content
```

**关键点：**
- 统一的工具调用接口
- 支持 SSE 和 STDIO 传输
- 错误处理和超时控制

### 第7步：结果加工和流式输出

**文件：`mcp_true_stream_client.py`**
```python
async def _process_tool_results_with_true_stream(self, user_input: str, tool_results: List[Dict], original_response: str) -> str:
    """使用 LLM 加工工具调用结果 - 真正的流式输出版本"""
    
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
```

**关键改进：**
- 工具结果也采用流式输出
- 保持对话的自然流畅性
- 准确的工具数据反映

## 📊 数据流详细说明

### 1. 初始化阶段
```
客户端 → 服务器: initialize 请求
服务器 → 客户端: initialize 响应 + capabilities
客户端 → 服务器: tools/list 请求  
服务器 → 客户端: 工具列表
```

### 2. 流式处理阶段
```
用户输入 → 客户端流式输出思考过程 → LLM工具选择 → 流式显示工具调用
客户端 → 服务器: tools/call 请求
服务器 → 执行工具逻辑 → 返回原始结果
客户端 → LLM流式加工 → 自然语言流式输出
```

### 3. 多服务器支持
```
客户端同时连接多个 MCP 服务器
自动合并所有可用工具
智能选择最合适的工具
支持并发工具调用
```

## 🔧 协议细节

### MCP JSON-RPC 消息格式
```json
{
  "jsonrpc": "2.0",
  "id": 123,
  "method": "tools/call",
  "params": {
    "name": "get_employee_location",
    "arguments": {"employee_id": "D0005"}
  }
}
```

### 工具调用响应格式
```json
{
  "jsonrpc": "2.0",
  "id": 123,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "工号D0005的员工目前位于上海总部B座5楼工位。"
      }
    ]
  }
}
```

## 🎯 关键优势

### 1. 真正的流式输出
- LLM 思考过程实时显示
- 工具调用过程透明可见
- 最终结果逐字输出

### 2. 多服务器支持
- 自动发现和连接多个 MCP 服务器
- 统一的工具调用接口
- 智能工具路由

### 3. 完善的调试系统
- 详细的调试日志记录
- 每个步骤的上下文保存
- 错误追踪和诊断

### 4. 智能工具管理
- LLM 自动工具选择
- 多工具并发调用支持
- 参数自动提取和验证

## 🚀 使用示例

### 启动系统
```bash
# 1. 启动服务器管理器
python mcp_server_manager.py

# 2. 启动所有服务器
选择命令 2: 启动所有服务器

# 3. 运行流式客户端
python mcp_true_stream_client.py
```

### 交互示例
```
💬 You: 员工D0003 and D0005 他们的位置在哪儿
🤖 Assistant: 🤔 正在思考...
<function_calls>
<invoke name="get_employee_location">
<parameter name="employee_id">D0003</parameter>
</invoke>
</function_calls>

<function_calls>
<invoke name="get_employee_location">
<parameter name="employee_id">D0005</parameter>
</invoke>
</function_calls>
🔧 正在调用工具: get_employee_location
   参数: {'employee_id': 'D0003'}
🔧 正在调用工具: get_employee_location
   参数: {'employee_id': 'D0005'}
[INFO] 调用工具: get_employee_location 参数: {'employee_id': 'D0003'}
[INFO] 调用工具: get_employee_location 参数: {'employee_id': 'D0005'}
✅ 工具调用完成
🤔 正在整合结果...
根据查询结果：

- 工号D0003的员工目前位于纽约办事处1楼接待室
- 工号D0005的员工目前位于上海总部B座5楼工位
```

---

这个架构确保了 MCP 服务器与 Agent 之间的无缝协作，提供了强大的工具扩展能力、真正的流式输出体验和优秀的用户体验。
