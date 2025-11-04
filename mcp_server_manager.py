#!/usr/bin/env python3
"""
MCP 服务器管理器 - 管理多个 MCP 服务器的配置和连接

行业标准做法：
1. 使用 JSON 配置文件记录所有 MCP 服务器的信息
2. 支持自动发现和手动配置
3. 提供统一的连接管理接口
4. 支持健康检查和故障转移
"""

import asyncio
import os
import sys
import json
import subprocess
import time
import signal
import psutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import requests
from pathlib import Path

class MCPTransportType(Enum):
    """MCP 传输类型"""
    SSE = "sse"
    STDIO = "stdio"

@dataclass
class MCPServerConfig:
    """MCP 服务器配置"""
    name: str
    description: str
    transport_type: MCPTransportType
    command: Optional[str] = None  # 用于 STDIO
    url: Optional[str] = None      # 用于 SSE
    port: Optional[int] = None     # 用于 SSE
    working_directory: Optional[str] = None
    env_vars: Dict[str, str] = field(default_factory=dict)
    auto_start: bool = True
    health_check_endpoint: Optional[str] = None
    pid: Optional[int] = None      # 进程ID
    status: str = "stopped"        # running, stopped, error

class MCPServerManager:
    """
    MCP 服务器管理器
    负责管理多个 MCP 服务器的生命周期和配置
    """
    
    def __init__(self, config_file: str = "mcp_servers.json"):
        self.config_file = config_file
        self.servers: Dict[str, MCPServerConfig] = {}
        self.processes: Dict[str, subprocess.Popen] = {}
        self.load_config()
        
    def load_config(self):
        """加载服务器配置（不加载状态，状态实时查询）"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for server_name, server_data in data.items():
                    config = MCPServerConfig(
                        name=server_name,
                        description=server_data.get('description', ''),
                        transport_type=MCPTransportType(server_data.get('transport_type', 'sse')),
                        command=server_data.get('command'),
                        url=server_data.get('url'),
                        port=server_data.get('port'),
                        working_directory=server_data.get('working_directory'),
                        env_vars=server_data.get('env_vars', {}),
                        auto_start=server_data.get('auto_start', True),
                        health_check_endpoint=server_data.get('health_check_endpoint'),
                        pid=server_data.get('pid'),
                        status="unknown"  # 状态实时查询，不存储
                    )
                    self.servers[server_name] = config
                    
                print(f"[INFO] 加载了 {len(self.servers)} 个 MCP 服务器配置")
                
            except Exception as e:
                print(f"[ERROR] 加载配置文件失败: {e}")
                self._create_default_config()
        else:
            self._create_default_config()
            
    def _create_default_config(self):
        """创建默认配置"""
        print("[INFO] 创建默认 MCP 服务器配置...")
        
        # 默认的天气服务器配置
        weather_server = MCPServerConfig(
            name="weather_server",
            description="天气查询 MCP 服务器",
            transport_type=MCPTransportType.SSE,
            command="python weather_server.py",
            port=8000,
            url="http://127.0.0.1:8000/sse",
            working_directory=os.getcwd(),
            auto_start=True,
            health_check_endpoint="/sse"
        )
        
        self.servers["weather_server"] = weather_server
        self.save_config()
        
    def save_config(self):
        """保存服务器配置到文件"""
        try:
            data = {}
            for name, config in self.servers.items():
                data[name] = {
                    'description': config.description,
                    'transport_type': config.transport_type.value,
                    'command': config.command,
                    'url': config.url,
                    'port': config.port,
                    'working_directory': config.working_directory,
                    'env_vars': config.env_vars,
                    'auto_start': config.auto_start,
                    'health_check_endpoint': config.health_check_endpoint,
                    'pid': config.pid,
                    'status': config.status
                }
                
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            print(f"[INFO] 配置已保存到 {self.config_file}")
            
        except Exception as e:
            print(f"[ERROR] 保存配置失败: {e}")
            
    def add_server(self, config: MCPServerConfig):
        """添加新的 MCP 服务器配置"""
        self.servers[config.name] = config
        self.save_config()
        print(f"[INFO] 添加服务器: {config.name}")
        
    def remove_server(self, name: str):
        """移除 MCP 服务器配置"""
        if name in self.servers:
            # 先停止服务器
            self.stop_server(name)
            del self.servers[name]
            self.save_config()
            print(f"[INFO] 移除服务器: {name}")
        else:
            print(f"[WARN] 服务器不存在: {name}")
            
    def start_server(self, name: str) -> bool:
        """启动指定的 MCP 服务器"""
        if name not in self.servers:
            print(f"[ERROR] 服务器不存在: {name}")
            return False
            
        config = self.servers[name]
        
        try:
            if config.transport_type == MCPTransportType.STDIO:
                # STDIO 模式 - 启动进程
                env = os.environ.copy()
                env.update(config.env_vars)
                
                working_dir = config.working_directory or os.getcwd()
                
                process = subprocess.Popen(
                    config.command.split(),
                    cwd=working_dir,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                self.processes[name] = process
                config.pid = process.pid
                config.status = "running"
                self.save_config()
                
                print(f"[INFO] 启动服务器 {name} (PID: {process.pid})")
                return True
                
            elif config.transport_type == MCPTransportType.SSE:
                # SSE 模式 - 检查是否已运行，如果没有则启动
                if self._check_server_health(config):
                    print(f"[INFO] 服务器 {name} 已在运行")
                    config.status = "running"
                    self.save_config()
                    return True
                else:
                    # 启动 SSE 服务器进程
                    env = os.environ.copy()
                    env.update(config.env_vars)
                    
                    working_dir = config.working_directory or os.getcwd()
                    
                    process = subprocess.Popen(
                        config.command.split(),
                        cwd=working_dir,
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    self.processes[name] = process
                    config.pid = process.pid
                    config.status = "running"
                    self.save_config()
                    
                    # 等待服务器启动
                    time.sleep(2)
                    
                    if self._check_server_health(config):
                        print(f"[INFO] 启动服务器 {name} (PID: {process.pid})")
                        return True
                    else:
                        print(f"[WARN] 服务器 {name} 启动但健康检查失败")
                        return False
                    
        except Exception as e:
            print(f"[ERROR] 启动服务器 {name} 失败: {e}")
            config.status = "error"
            self.save_config()
            return False
            
        return True
        
    def stop_server(self, name: str):
        """停止指定的 MCP 服务器"""
        if name in self.processes:
            process = self.processes[name]
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"[INFO] 停止服务器 {name}")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"[WARN] 强制停止服务器 {name}")
            except Exception as e:
                print(f"[ERROR] 停止服务器 {name} 失败: {e}")
                
            del self.processes[name]
            
        if name in self.servers:
            self.servers[name].status = "stopped"
            self.servers[name].pid = None
            self.save_config()
            
    def start_all_servers(self):
        """启动所有配置为自动启动的服务器"""
        print("[INFO] 启动所有 MCP 服务器...")
        
        for name, config in self.servers.items():
            if config.auto_start:
                self.start_server(name)
                
        print("[INFO] 所有服务器启动完成")
        
    def stop_all_servers(self):
        """停止所有服务器"""
        print("[INFO] 停止所有 MCP 服务器...")
        
        for name in list(self.processes.keys()):
            self.stop_server(name)
            
        print("[INFO] 所有服务器已停止")
        
    def _check_server_health(self, config: MCPServerConfig) -> bool:
        """检查服务器健康状态"""
        if config.transport_type == MCPTransportType.SSE and config.url:
            try:
                resp = requests.head(config.url, timeout=5)
                return resp.status_code == 200
            except:
                return False
        return False
        
    def get_server_status(self, name: str) -> Dict[str, Any]:
        """获取服务器状态信息"""
        if name not in self.servers:
            return {"error": f"服务器不存在: {name}"}
            
        config = self.servers[name]
        status = {
            "name": config.name,
            "description": config.description,
            "transport_type": config.transport_type.value,
            "status": config.status,
            "pid": config.pid,
            "url": config.url,
            "health": "unknown"
        }
        
        # 检查健康状态
        if config.status == "running":
            status["health"] = "healthy" if self._check_server_health(config) else "unhealthy"
            
        return status
        
    def list_servers(self) -> List[Dict[str, Any]]:
        """列出所有服务器状态"""
        return [self.get_server_status(name) for name in self.servers.keys()]
        
    def discover_running_servers(self):
        """发现正在运行的 MCP 服务器"""
        print("[INFO] 扫描正在运行的 MCP 服务器...")
        
        # 这里可以实现自动发现逻辑
        # 例如扫描特定端口范围，检查进程等
        
        # 临时实现：检查已知端口的服务器
        common_ports = range(8000,8999)
        
        for port in common_ports:
            url = f"http://127.0.0.1:{port}/sse"
            try:
                resp = requests.head(url, timeout=2)
                if resp.status_code == 200:
                    server_name = f"discovered_server_{port}"
                    if server_name not in self.servers:
                        config = MCPServerConfig(
                            name=server_name,
                            description=f"自动发现的 MCP 服务器 (端口 {port})",
                            transport_type=MCPTransportType.SSE,
                            port=port,
                            url=url,
                            auto_start=False,
                            status="running"
                        )
                        self.add_server(config)
                        print(f"[INFO] 发现服务器: {server_name}")
            except:
                continue

def main():
    """MCP 服务器管理器主程序"""
    manager = MCPServerManager()
    
    print("=" * 60)
    print("MCP 服务器管理器")
    print("=" * 60)
    
    while True:
        print("\n可用命令:")
        print("  1. 列出所有服务器")
        print("  2. 启动所有服务器")
        print("  3. 停止所有服务器")
        print("  4. 启动单个服务器")
        print("  5. 停止单个服务器")
        print("  6. 发现运行中的服务器")
        print("  7. 添加新服务器")
        print("  8. 退出")
        
        try:
            choice = input("\n请输入命令编号: ").strip()
            
            if choice == "1":
                servers = manager.list_servers()
                print("\n服务器状态:")
                for server in servers:
                    print(f"  - {server['name']}: {server['status']} ({server['health']})")
                    
            elif choice == "2":
                manager.start_all_servers()
                
            elif choice == "3":
                manager.stop_all_servers()
                
            elif choice == "4":
                name = input("请输入服务器名称: ").strip()
                manager.start_server(name)
                
            elif choice == "5":
                name = input("请输入服务器名称: ").strip()
                manager.stop_server(name)
                
            elif choice == "6":
                manager.discover_running_servers()
                
            elif choice == "7":
                print("\n添加新服务器:")
                name = input("服务器名称: ").strip()
                description = input("描述: ").strip()
                transport = input("传输类型 (sse/stdio): ").strip()
                
                config = MCPServerConfig(
                    name=name,
                    description=description,
                    transport_type=MCPTransportType(transport)
                )
                
                if transport == "sse":
                    config.url = input("SSE URL: ").strip()
                    config.port = int(input("端口: ").strip())
                else:
                    config.command = input("启动命令: ").strip()
                    config.working_directory = input("工作目录 (可选): ").strip() or None
                    
                manager.add_server(config)
                
            elif choice == "8":
                print("[INFO] 退出管理器")
                manager.stop_all_servers()
                break
                
            else:
                print("[ERROR] 无效命令")
                
        except KeyboardInterrupt:
            print("\n[INFO] 用户中断")
            manager.stop_all_servers()
            break
        except Exception as e:
            print(f"[ERROR] 执行命令失败: {e}")

if __name__ == "__main__":
    main()
