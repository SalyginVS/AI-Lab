import os

import httpx
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings


SEARXNG_URL = os.getenv("SEARXNG_URL", "http://127.0.0.1:8080")

mcp = MCPServer(
    "AI Lab Web Search",
    instructions=(
        "Read-only web search backed by the local AI Lab SearXNG instance. "
        "Use web_search when current or externally verified information is needed."
    ),
)


@mcp.tool()
async def web_search(query: str, max_results: int = 8) -> dict:
    """Search the public web and return normalized search results with URLs."""
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")

    limit = max(1, min(max_results, 10))

    async with httpx.AsyncClient(
        timeout=20.0,
        follow_redirects=True,
    ) as client:
        response = await client.get(
            f"{SEARXNG_URL}/search",
            params={
                "q": query,
                "format": "json",
            },
        )
        response.raise_for_status()
        payload = response.json()

    results = []

    for item in payload.get("results", []):
        url = item.get("url")
        title = item.get("title")

        if not url or not title:
            continue

        if not url.startswith(("https://", "http://")):
            continue

        results.append(
            {
                "title": title,
                "url": url,
                "snippet": item.get("content") or "",
                "engine": item.get("engine") or "",
                "published_date": (
                    item.get("publishedDate")
                    or item.get("published_date")
                ),
            }
        )

        if len(results) >= limit:
            break

    return {
        "query": query,
        "count": len(results),
        "results": results,
    }


security = TransportSecuritySettings(
    allowed_hosts=[
        "127.0.0.1:*",
        "localhost:*",
        "192.168.0.128:*",
    ],
    allowed_origins=[
        "http://127.0.0.1:*",
        "http://localhost:*",
        "http://192.168.0.128:*",
    ],
)


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8300,
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        transport_security=security,
    )
