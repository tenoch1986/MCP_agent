# 实时消息查询公共 API

## 📰 新闻和资讯类 API

### 1. NewsAPI
**功能**：全球新闻聚合，支持实时新闻流
**URL**：`https://newsapi.org/`
**特点**：
- 支持 70,000+ 新闻源
- 实时新闻推送
- 多语言支持
- 免费套餐：500 请求/天

**示例调用**：
```python
import requests

def get_latest_news(api_key, query="technology", language="zh"):
    url = f"https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": language,
        "sortBy": "publishedAt",
        "apiKey": api_key
    }
    response = requests.get(url, params=params)
    return response.json()
```

### 2. GNews API
**功能**：新闻搜索和实时新闻
**URL**：`https://gnews.io/`
**特点**：
- 中文新闻支持良好
- 实时新闻更新
- 免费套餐：100 请求/天

**示例调用**：
```python
def get_gnews(api_key, query="科技", lang="zh"):
    url = "https://gnews.io/api/v4/search"
    params = {
        "q": query,
        "lang": lang,
        "token": api_key
    }
    response = requests.get(url, params=params)
    return response.json()
```

## 📊 社交媒体和论坛 API

### 3. Reddit API
**功能**：Reddit 帖子实时监控
**URL**：`https://www.reddit.com/dev/api/`
**特点**：
- 实时帖子流
- 热门话题追踪
- 无需 API key（有限制）

**示例调用**：
```python
import praw

def get_reddit_hot_posts(subreddit="technology", limit=10):
    reddit = praw.Reddit(
        client_id="your_client_id",
        client_secret="your_client_secret",
        user_agent="your_user_agent"
    )
    
    subreddit = reddit.subreddit(subreddit)
    posts = []
    for post in subreddit.hot(limit=limit):
        posts.append({
            "title": post.title,
            "score": post.score,
            "url": post.url,
            "created_utc": post.created_utc
        })
    return posts
```

### 4. Twitter API v2
**功能**：Twitter 实时推文流
**URL**：`https://developer.twitter.com/en/docs/twitter-api`
**特点**：
- 实时推文流
- 话题标签追踪
- 需要开发者账号

**示例调用**：
```python
import tweepy

def get_twitter_trends(bearer_token):
    client = tweepy.Client(bearer_token=bearer_token)
    
    # 获取趋势话题
    trends = client.get_place_trends(id=1)  # 1 是全球趋势
    return trends
```

## 🌐 实时数据流 API

### 5. WebSocket 实时数据
**功能**：实时消息推送
**技术**：WebSocket 协议
**特点**：
- 真正的实时双向通信
- 低延迟
- 适合聊天、通知等场景

**示例实现**：
```python
import asyncio
import websockets
import json

async def websocket_client(uri):
    async with websockets.connect(uri) as websocket:
        # 订阅消息
        await websocket.send(json.dumps({"action": "subscribe", "channel": "news"}))
        
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"收到实时消息: {data}")
```

### 6. Server-Sent Events (SSE)
**功能**：服务器推送事件
**技术**：HTTP SSE
**特点**：
- 单向服务器推送
- 简单易用
- 适合新闻、通知推送

**示例实现**：
```python
import requests
import json

def sse_client(url):
    response = requests.get(url, stream=True)
    
    for line in response.iter_lines():
        if line:
            data = line.decode('utf-8')
            if data.startswith('data: '):
                message = json.loads(data[6:])
                print(f"收到 SSE 消息: {message}")
```

## 📈 金融数据 API

### 7. Alpha Vantage
**功能**：股票市场实时数据
**URL**：`https://www.alphavantage.co/`
**特点**：
- 实时股票价格
- 技术指标
- 免费套餐：5 请求/分钟

**示例调用**：
```python
def get_stock_quote(api_key, symbol="AAPL"):
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": api_key
    }
    response = requests.get(url, params=params)
    return response.json()
```

### 8. Finnhub
**功能**：实时金融市场数据
**URL**：`https://finnhub.io/`
**特点**：
- 实时股票报价
- 新闻情绪分析
- WebSocket 支持

## 🎮 游戏和娱乐 API

### 9. Twitch API
**功能**：直播流信息
**URL**：`https://dev.twitch.tv/`
**特点**：
- 实时直播数据
- 聊天消息
- 需要 OAuth 认证

### 10. Steam Web API
**功能**：游戏新闻和更新
**URL**：`https://steamcommunity.com/dev`
**特点**：
- 游戏新闻
- 玩家统计数据
- 免费使用

## 🔧 实用工具 API

### 11. Webhook.site
**功能**：测试 Webhook 和实时消息
**URL**：`https://webhook.site/`
**特点**：
- 临时 Webhook URL
- 实时消息查看
- 无需注册

### 12. Pusher Channels
**功能**：实时消息推送服务
**URL**：`https://pusher.com/`
**特点**：
- 专业的实时消息服务
- WebSocket 和 SSE 支持
- 免费套餐可用

## 🛠️ 集成到 MCP 服务器的示例

### 新闻查询 MCP 服务器
```python
from mcp.server import FastMCP
import requests

mcp = FastMCP("news_server")

@mcp.tool()
async def get_latest_news(topic: str = "technology") -> str:
    """获取指定话题的最新新闻"""
    # 使用 NewsAPI
    api_key = "your_newsapi_key"
    url = f"https://newsapi.org/v2/everything"
    params = {
        "q": topic,
        "language": "zh",
        "sortBy": "publishedAt",
        "apiKey": api_key
    }
    
    response = requests.get(url, params=params)
    articles = response.json().get("articles", [])[:5]
    
    result = f"关于 {topic} 的最新新闻：\n\n"
    for article in articles:
        result += f"📰 {article['title']}\n"
        result += f"   来源: {article['source']['name']}\n"
        result += f"   时间: {article['publishedAt']}\n"
        result += f"   链接: {article['url']}\n\n"
    
    return result

if __name__ == "__main__":
    mcp.run(transport="sse")
```

### 实时股票 MCP 服务器
```python
from mcp.server import FastMCP
import requests

mcp = FastMCP("stock_server")

@mcp.tool()
async def get_stock_price(symbol: str) -> str:
    """获取股票实时价格"""
    api_key = "your_alphavantage_key"
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": api_key
    }
    
    response = requests.get(url, params=params)
    quote = response.json().get("Global Quote", {})
    
    if quote:
        return f"{symbol} 股票信息：\n" \
               f"价格: ${quote.get('05. price', 'N/A')}\n" \
               f"涨跌: {quote.get('10. change percent', 'N/A')}\n" \
               f"成交量: {quote.get('06. volume', 'N/A')}"
    else:
        return f"无法获取 {symbol} 的股票信息"

if __name__ == "__main__":
    mcp.run(transport="sse")
```

## 🔑 API 密钥获取

1. **NewsAPI**：访问 https://newsapi.org/register
2. **Alpha Vantage**：访问 https://www.alphavantage.co/support/#api-key
3. **Twitter API**：申请开发者账号 https://developer.twitter.com/
4. **Reddit API**：创建应用 https://www.reddit.com/prefs/apps

## ⚠️ 使用注意事项

1. **频率限制**：注意免费套餐的请求限制
2. **认证要求**：大多数 API 需要 API key
3. **数据格式**：处理 JSON 响应和错误情况
4. **实时性**：WebSocket 和 SSE 提供真正的实时数据

这些 API 可以集成到你的 MCP 服务器中，提供丰富的实时消息查询功能！
