#!/usr/bin/env python3
"""
GNews API MCP 服务器 - 通过 GNews API 查询新闻

功能：
- 提供新闻搜索工具
- 支持多种搜索参数
- 支持 SSE 传输模式
"""

import json
import urllib.request
from urllib.parse import quote
from typing import Optional
from mcp.server import FastMCP

# 创建 MCP 服务器实例
mcp = FastMCP("gnews_server", port=8002)

# GNews API 配置
GNEWS_API_KEY = "52a1e33ade91f472baca36ff22e115be"
BASE_URL = "https://gnews.io/api/v4/search"

def build_gnews_url(
    query: str,
    lang: str = "zh",
    country: str = "cn",
    max_results: int = 10,
    sort_by: str = "publishedAt"
) -> str:
    """构建 GNews API URL"""
    # URL 编码查询参数
    encoded_query = quote(query)
    
    url = f"{BASE_URL}?q={encoded_query}&lang={lang}&country={country}&max={max_results}&sortby={sort_by}&apikey={GNEWS_API_KEY}"
    return url

def fetch_news_from_gnews(url: str) -> dict:
    """从 GNews API 获取新闻数据"""
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data
    except Exception as e:
        return {"error": f"获取新闻失败: {str(e)}"}

@mcp.tool()
async def search_news(
    query: str,
    lang: str = "zh",
    country: str = "cn",
    max_results: int = 10,
    sort_by: str = "publishedAt"
) -> str:
    """搜索新闻文章
    
    Args:
        query: 搜索关键词（支持逻辑运算符 AND, OR, NOT）
        lang: 语言代码 (zh=中文, en=英文等)
        country: 国家代码 (cn=中国, us=美国等)
        max_results: 返回结果数量 (1-100)
        sort_by: 排序方式 (publishedAt=发布时间, relevance=相关性)
    """
    if not query:
        return "错误：请提供搜索关键词"
    
    # 验证参数
    if max_results < 1 or max_results > 100:
        return "错误：max_results 必须在 1-100 之间"
    
    if sort_by not in ["publishedAt", "relevance"]:
        return "错误：sort_by 必须是 'publishedAt' 或 'relevance'"
    
    # 构建 API URL
    url = build_gnews_url(query, lang, country, max_results, sort_by)
    
    # 获取新闻数据
    data = fetch_news_from_gnews(url)
    
    if "error" in data:
        return data["error"]
    
    articles = data.get("articles", [])
    total_articles = data.get("totalArticles", 0)
    
    if not articles:
        return f"没有找到关于 '{query}' 的新闻"
    
    # 格式化结果
    result = f"📰 关于 '{query}' 的新闻搜索结果 ({total_articles} 条结果)\n\n"
    
    for i, article in enumerate(articles[:max_results], 1):
        result += f"**{i}. {article.get('title', '无标题')}**\n"
        result += f"   描述: {article.get('description', '无描述')}\n"
        result += f"   来源: {article.get('source', {}).get('name', '未知')}\n"
        result += f"   发布时间: {article.get('publishedAt', '未知')}\n"
        result += f"   链接: {article.get('url', '无链接')}\n\n"
    
    return result

@mcp.tool()
async def get_top_headlines(
    category: str = "general",
    country: str = "cn",
    max_results: int = 10
) -> str:
    """获取头条新闻
    
    Args:
        category: 新闻类别 (general, world, nation, business, technology, entertainment, sports, science, health)
        country: 国家代码
        max_results: 返回结果数量
    """
    # 使用 GNews 的搜索功能模拟头条新闻
    query = "最新 新闻"
    
    url = build_gnews_url(query, "zh", country, max_results, "publishedAt")
    data = fetch_news_from_gnews(url)
    
    if "error" in data:
        return data["error"]
    
    articles = data.get("articles", [])
    
    if not articles:
        return f"没有找到 {category} 类别的头条新闻"
    
    result = f"📢 {category.capitalize()} 类别头条新闻\n\n"
    
    for i, article in enumerate(articles[:max_results], 1):
        result += f"**{i}. {article.get('title', '无标题')}**\n"
        result += f"   描述: {article.get('description', '无描述')}\n"
        result += f"   来源: {article.get('source', {}).get('name', '未知')}\n"
        result += f"   发布时间: {article.get('publishedAt', '未知')}\n\n"
    
    return result

@mcp.tool()
async def search_news_by_topic(
    topic: str,
    lang: str = "zh",
    max_results: int = 10
) -> str:
    """按主题搜索新闻
    
    Args:
        topic: 新闻主题 (如: 科技, 体育, 财经, 娱乐等)
        lang: 语言代码
        max_results: 返回结果数量
    """
    # 中文主题映射到英文关键词
    topic_mapping = {
        "科技": "technology",
        "体育": "sports", 
        "财经": "finance",
        "娱乐": "entertainment",
        "健康": "health",
        "科学": "science",
        "政治": "politics",
        "教育": "education"
    }
    
    # 如果主题在映射中，使用英文关键词，否则使用中文
    if topic in topic_mapping:
        query = topic_mapping[topic]
    else:
        query = topic
    
    url = build_gnews_url(query, lang, "cn", max_results, "publishedAt")
    data = fetch_news_from_gnews(url)
    
    if "error" in data:
        return data["error"]
    
    articles = data.get("articles", [])
    total_articles = data.get("totalArticles", 0)
    
    if not articles:
        return f"没有找到关于 '{topic}' 主题的新闻"
    
    result = f"📰 {topic} 主题新闻 ({total_articles} 条结果)\n\n"
    
    for i, article in enumerate(articles[:max_results], 1):
        result += f"**{i}. {article.get('title', '无标题')}**\n"
        result += f"   描述: {article.get('description', '无描述')}\n"
        result += f"   来源: {article.get('source', {}).get('name', '未知')}\n"
        result += f"   发布时间: {article.get('publishedAt', '未知')}\n\n"
    
    return result

# 关键：不要加多余的 print，否则破坏 JSON-RPC 协议！
if __name__ == "__main__":
    mcp.run(transport="sse")
