# weather_server.py
from mcp.server import FastMCP

mcp = FastMCP("weather")

@mcp.tool()
async def get_weather(city: str) -> str:
    """获取城市天气"""
    return f"{city} 今天晴，25°C，微风。"

# 关键：不要加多余的 print，否则破坏 JSON-RPC 协议！
if __name__ == "__main__":
    mcp.run(transport="sse")