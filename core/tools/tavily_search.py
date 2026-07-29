from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import os
import json


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    score: float = 0.0


class TavilySearchTool:
    """Web search tool powered by Tavily API.

    Features:
    - Agent-optimized search results
    - Automatic answer extraction
    - Raw context for RAG
    - Time-range filtering
    """

    name = "tavily_search"
    description = "Search the web using Tavily. Returns titles, URLs, and snippets."

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")

    async def __call__(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic",
        include_answer: bool = False,
        include_raw_content: bool = False,
    ) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "TAVILY_API_KEY not configured"}

        import urllib.request
        import urllib.error

        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
        }

        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            return {"error": str(e)}

        results = []
        for item in data.get("results", [])[:max_results]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    score=item.get("score", 0.0),
                ).__dict__
            )

        return {
            "query": query,
            "answer": data.get("answer"),
            "results": results,
        }
