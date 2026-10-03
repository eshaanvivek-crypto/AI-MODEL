from __future__ import annotations

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


def domain_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()
