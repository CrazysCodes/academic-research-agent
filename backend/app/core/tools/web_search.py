"""
Tavily Web Search Tool（可选）。
仅在 TAVILY_API_KEY 配置时生效。
"""
from app.config import settings


async def search_web(query: str, max_results: int = 3) -> str:
    """使用 Tavily 搜索补充外部资料，返回格式化文本。"""
    if not settings.tavily_api_key:
        return ""
    try:
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=settings.tavily_api_key)
        response = await client.search(query, max_results=max_results)
        results = response.get("results", [])
        formatted = [
            f"**{r['title']}** ({r['url']})\n{r.get('content', '')}"
            for r in results
        ]
        return "\n\n".join(formatted)
    except Exception:
        return ""
