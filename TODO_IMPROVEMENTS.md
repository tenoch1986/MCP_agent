# MCP 系统改进计划

## 当前已完成的功能
- ✅ 多 MCP 服务器同时使用
- ✅ 真正的流式输出功能
- ✅ 基本的调试日志系统
- ✅ 智能工具路由和调用

## 待改进的问题

### 1. MCP 服务器管理架构重构

**当前问题**：
- 手动添加和自动发现的服务器重复
- 服务器管理逻辑混乱
- 缺乏清晰的服务器分类

**新架构设计**：

| 服务器类型 | 配置文件 | 启动方式 | 管理方式 |
|-----------|----------|----------|----------|
| **Python 内部服务器** | `mcp_server_python.json` | Python 脚本 | 本地启动，支持自定义参数 |
| **NPM 外部服务器** | `mcp_server_npm.json` | npx 命令 | 临时安装，支持 token 等配置 |

### 2. 具体实现计划

#### 2.1 配置文件结构设计

**mcp_server_python.json**
```json
{
  "weather_server": {
    "type": "python",
    "description": "天气查询 MCP 服务器",
    "transport_type": "sse",
    "command": "python weather_server.py",
    "url": "http://127.0.0.1:8000/sse",
    "port": 8000,
    "working_directory": "/Users/liuluyao/Documents/coding/AI/MCP_agent",
    "env_vars": {},
    "auto_start": true,
    "health_check_endpoint": "/sse",
    "custom_params": {}
  }
}
```

**mcp_server_npm.json**
```json
{
  "github_server": {
    "type": "npm",
    "description": "GitHub MCP 服务器",
    "transport_type": "stdio",
    "command": "npx @modelcontextprotocol/server-github",
    "env_vars": {
      "GITHUB_TOKEN": "your_token_here"
    },
    "auto_start": true
  }
}
```

#### 2.2 MCP 客户端启动流程
1. 读取 `mcp_server_python.json`
   - 检查 Python 服务器是否运行
   - 未运行的通过 manager 启动
2. 读取 `mcp_server_npm.json`
   - 检查 NPM 服务器是否运行
   - 未运行的通过 npx 命令启动
3. 合并所有可用服务器
4. 提供统一的工具调用接口

#### 2.3 MCP 服务器管理器改进
- 支持两种服务器类型的独立管理
- 自动去重逻辑（基于端口和功能）
- 健康检查和自动重启
- 配置验证和错误处理

### 3. 优先级排序

| 优先级 | 任务 | 描述 | 预计时间 |
|--------|------|------|----------|
| 高 | 重构配置文件结构 | 创建两个独立的 JSON 配置文件 | 1-2 天 |
| 高 | 更新服务器管理器 | 支持两种服务器类型的管理 | 2-3 天 |
| 中 | 客户端启动流程优化 | 自动读取和启动两种服务器 | 1-2 天 |
| 中 | 去重和冲突解决 | 避免服务器重复和端口冲突 | 1 天 |
| 低 | 高级功能 | 健康检查、自动重启等 | 2-3 天 |

### 4. 技术考虑

#### 4.1 服务器识别
- **Python 服务器**：通过端口和进程名识别
- **NPM 服务器**：通过进程命令和端口识别

#### 4.2 冲突解决策略
1. 端口冲突检测
2. 功能重复检测（相同工具名）
3. 优先级设置（手动配置 > 自动发现）

#### 4.3 错误处理
- 服务器启动失败处理
- 连接超时处理
- 配置验证和错误提示

### 5. 测试计划
- [ ] 单服务器启动测试
- [ ] 多服务器并发测试
- [ ] 配置文件格式验证
- [ ] 错误场景处理测试
- [ ] 性能基准测试

### 6. 文档更新
- [ ] 新架构说明文档
- [ ] 配置指南
- [ ] 故障排除指南
- [ ] API 文档更新

## 预期收益
1. **清晰的架构**：明确的服务器分类和管理方式
2. **避免重复**：自动检测和去重机制
3. **易于扩展**：支持更多服务器类型
4. **更好的维护性**：分离关注点，简化配置管理
5. **用户体验提升**：更稳定的服务器管理和工具调用
