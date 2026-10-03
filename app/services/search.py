from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote_plus, urlparse

import requests
from bs4 import BeautifulSoup


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchProvider:
    def search(self, query: str, limit: int) -> list[SearchResult]:
        raise NotImplementedError


class MockSearchProvider(SearchProvider):
    def search(self, query: str, limit: int) -> list[SearchResult]:
        return []


class WikipediaSearchProvider(SearchProvider):
    def __init__(self, timeout: int, user_agent: str) -> None:
        self.timeout = timeout
        self.user_agent = user_agent

    def search(self, query: str, limit: int) -> list[SearchResult]:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": "1",
            "srlimit": max(1, min(limit, 10)),
            "srprop": "snippet",
        }
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params=params,
            timeout=self.timeout,
            headers={"User-Agent": self.user_agent},
        )
        resp.raise_for_status()

        payload = resp.json()
        output: list[SearchResult] = []
        for item in payload.get("query", {}).get("search", [])[:limit]:
            title = (item.get("title") or "").strip()
            if not title:
                continue
            snippet = _strip_html(item.get("snippet") or "")
            safe_title = title.replace(" ", "_")
            url = f"https://en.wikipedia.org/wiki/{quote_plus(safe_title, safe='/') }"
            output.append(SearchResult(title=title, url=url, snippet=snippet))
        return output


class DuckDuckGoSearchProvider(SearchProvider):
    def __init__(self, timeout: int, user_agent: str) -> None:
        self.timeout = timeout
        self.user_agent = user_agent

    def search(self, query: str, limit: int) -> list[SearchResult]:
        url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
        resp = requests.get(url, timeout=self.timeout, headers={"User-Agent": self.user_agent})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        output: list[SearchResult] = []
        for result in soup.select("div.result"):
            title_tag = result.select_one("a.result__a")
            snippet_tag = result.select_one("a.result__snippet") or result.select_one("div.result__snippet")
            if not title_tag:
                continue
            href = title_tag.get("href", "")
            title = title_tag.get_text(" ", strip=True)
            snippet = snippet_tag.get_text(" ", strip=True) if snippet_tag else ""
            if href and title:
                output.append(SearchResult(title=title, url=href, snippet=snippet))
            if len(output) >= limit:
                break

        return output


class FallbackSearchProvider(SearchProvider):
    def __init__(self, primary: SearchProvider, fallback: SearchProvider) -> None:
        self.primary = primary
        self.fallback = fallback

    def search(self, query: str, limit: int) -> list[SearchResult]:
        try:
            hits = self.primary.search(query, limit)
            if hits:
                return hits
        except Exception:
            pass

        try:
            hits = self.fallback.search(query, limit)
            if hits:
                return hits
        except Exception:
            pass

        return []


class SerpAPISearchProvider(SearchProvider):
    def __init__(self, api_key: str, timeout: int, user_agent: str) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.user_agent = user_agent

    def search(self, query: str, limit: int) -> list[SearchResult]:
        params = {
            "q": query,
            "api_key": self.api_key,
            "engine": "google",
            "num": max(1, min(limit, 10)),
        }
        resp = requests.get(
            "https://serpapi.com/search.json",
            params=params,
            timeout=self.timeout,
            headers={"User-Agent": self.user_agent},
        )
        resp.raise_for_status()
        data = resp.json()

        output: list[SearchResult] = []
        for item in data.get("organic_results", [])[:limit]:
            link = item.get("link", "")
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            if link and title:
                output.append(SearchResult(title=title, url=link, snippet=snippet))
        return output


def _strip_html(raw: str) -> str:
    if not raw:
        return ""
    return re.sub(r"<[^>]+>", " ", raw)


def domain_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


__all__ = [
    "DuckDuckGoSearchProvider",
    "FallbackSearchProvider",
    "MockSearchProvider",
    "SearchProvider",
    "SearchResult",
    "SerpAPISearchProvider",
    "WikipediaSearchProvider",
    "domain_of",
]


# The original module used to define domain_of at the bottom; keep the function in the module namespace.
# No-op marker to preserve import compatibility.
