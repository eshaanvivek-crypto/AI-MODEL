from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

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

    def pop_warnings(self) -> list[str]:
        return []


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
            href = _normalize_duckduckgo_href(title_tag.get("href", ""))
            title = title_tag.get_text(" ", strip=True)
            snippet = snippet_tag.get_text(" ", strip=True) if snippet_tag else ""
            if href and title and _is_valid_result_url(href):
                output.append(SearchResult(title=title, url=href, snippet=snippet))
            if len(output) >= limit:
                break

        return output


class WikipediaSearchProvider(SearchProvider):
    def __init__(self, timeout: int, user_agent: str) -> None:
        self.timeout = timeout
        self.user_agent = user_agent

    def search(self, query: str, limit: int) -> list[SearchResult]:
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srlimit": max(1, min(limit, 10)),
            "utf8": 1,
        }
        resp = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params=params,
            timeout=self.timeout,
            headers={"User-Agent": self.user_agent},
        )
        resp.raise_for_status()
        data = resp.json()

        output: list[SearchResult] = []
        for item in data.get("query", {}).get("search", [])[:limit]:
            title = item.get("title", "").strip()
            pageid = item.get("pageid")
            if not title or not isinstance(pageid, int):
                continue
            url = f"https://en.wikipedia.org/?curid={pageid}"
            if not _is_valid_result_url(url):
                continue
            snippet_html = item.get("snippet", "")
            snippet = BeautifulSoup(snippet_html, "html.parser").get_text(" ", strip=True)
            output.append(SearchResult(title=title, url=url, snippet=snippet))
        return output


@dataclass
class FallbackSearchProvider(SearchProvider):
    primary_name: str
    primary: SearchProvider
    fallback_name: str
    fallback: SearchProvider
    _warnings: list[str] = field(default_factory=list)

    def pop_warnings(self) -> list[str]:
        warnings = self._warnings
        self._warnings = []
        return warnings

    def search(self, query: str, limit: int) -> list[SearchResult]:
        self._warnings = []

        try:
            primary_results = self.primary.search(query, limit)
        except Exception as exc:
            self._warnings.append(
                f"Primary search provider '{self.primary_name}' failed ({exc.__class__.__name__}). "
                f"Tried fallback provider '{self.fallback_name}'."
            )
            return self._search_fallback(query, limit)

        if primary_results:
            return primary_results

        self._warnings.append(
            f"Primary search provider '{self.primary_name}' returned no results. "
            f"Tried fallback provider '{self.fallback_name}'."
        )
        return self._search_fallback(query, limit)

    def _search_fallback(self, query: str, limit: int) -> list[SearchResult]:
        try:
            return self.fallback.search(query, limit)
        except Exception as exc:
            self._warnings.append(
                f"Fallback search provider '{self.fallback_name}' failed ({exc.__class__.__name__})."
            )
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


def domain_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _is_valid_result_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_duckduckgo_href(href: str) -> str:
    if not href:
        return ""
    candidate = href
    if candidate.startswith("//"):
        candidate = f"https:{candidate}"
    elif candidate.startswith("/"):
        candidate = f"https://duckduckgo.com{candidate}"

    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower()
    if host in {"duckduckgo.com", "www.duckduckgo.com"} and parsed.path.startswith("/l"):
        redirect_target = parse_qs(parsed.query).get("uddg", [""])[0]
        if redirect_target:
            return unquote(redirect_target)
    return candidate
