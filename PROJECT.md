# MCP Multi-Server Framework

一个功能完整的 MCP (Model Context Protocol) 多服务器框架，支持动态工具发现、智能路由和真正的流式输出。

## 项目特性

### 🚀 核心功能
- **多服务器管理**: 自动从配置文件加载和管理多个 MCP 服务器
- **动态工具发现**: 运行时自动发现所有可用工具
- **智能工具路由**: LLM 自动选择最合适的工具
- **真正流式输出**: 提供流畅的用户体验
- **详细调试日志**: 完整的处理流程记录

### 📡 内置服务器
1. **天气服务器** (`weather_server.py`)
   - 工具: `get_weather` - 获取城市天气信息

2. **员工查询服务器** (`employee_server.py`)
   - 工具: `query_employee` - 通过工号查询员工姓名
   - 工具: `list_employees` - 列出员工信息
   - 工具: `get_employee_location` - 获取员工位置（测试工具）

3. **新闻服务器** (`gnews_server.py`)
   - 工具: `search_news` - 搜索新闻文章
   - 工具: `get_top_headlines` - 获取头条新闻
   - 工具: `search_news_by_topic` - 按主题搜索新闻

### 🛠️ 客户端
- **mcp_multi_client.py**: 标准多服务器客户端
- **mcp_true_stream_client.py**: 真正流式输出客户端
- **mcp_server_manager.py**: 服务器管理器

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置环境变量
```bash
# 复制 .env.example 为 .env 并填入你的 API 密钥
cp .env.example .env
```

### 3. 启动服务器
```bash
# 启动服务器管理器
python mcp_server_manager.py

# 或者手动启动单个服务器
python weather_server.py
python employee_server.py  
python gnews_server.py
```

### 4. 运行客户端
```bash
# 标准客户端
python mcp_multi_client.py

# 流式输出客户端
python mcp_true_stream_client.py
```

## 项目结构
```
MCP_agent/
├── weather_server.py      # 天气查询服务器
├── employee_server.py     # 员工查询服务器  
├── gnews_server.py        # 新闻查询服务器
├── mcp_server_manager.py  # 服务器管理器
├── mcp_multi_client.py    # 多服务器客户端
├── mcp_true_stream_client.py # 流式输出客户端
├── requirements.txt       # Python 依赖
├── README.md             # 项目说明
├── PROJECT.md            # 项目文档
└── .gitignore           # Git 忽略文件
```

## 技术栈
- **Python 3.8+**
- **MCP (Model Context Protocol)**
- **FastMCP** - 高性能 MCP 服务器框架
- **LangChain** - LLM 集成
- **DeepSeek API** - AI 模型服务

## 许可证
MIT License
