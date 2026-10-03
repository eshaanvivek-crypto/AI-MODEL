from unittest.mock import Mock, patch

import requests

from app.services.search import (
    DuckDuckGoSearchProvider,
    FallbackSearchProvider,
    SearchResult,
    WikipediaSearchProvider,
)


class StaticProvider:
    def __init__(self, results):
        self.results = results

    def search(self, query: str, limit: int):
        return self.results[:limit]


class ErrorProvider:
    def __init__(self, error: Exception):
        self.error = error

    def search(self, query: str, limit: int):
        raise self.error


def test_duckduckgo_search_normalizes_redirect_urls():
    provider = DuckDuckGoSearchProvider(timeout=2, user_agent="test-agent")
    html = """
    <div class="result">
      <a class="result__a" href="/l/?uddg=https%3A%2F%2Fexample.com%2Fdogs">Dogs</a>
      <div class="result__snippet">Dog summary</div>
    </div>
    """
    response = Mock()
    response.text = html
    response.raise_for_status = Mock()

    with patch("app.services.search.requests.get", return_value=response) as get_mock:
        results = provider.search("dogs", limit=5)

    get_mock.assert_called_once()
    assert len(results) == 1
    assert results[0].url == "https://example.com/dogs"
    assert results[0].title == "Dogs"


def test_fallback_search_uses_primary_results():
    primary = StaticProvider([SearchResult(title="A", url="https://example.com/a", snippet="s")])
    fallback = StaticProvider([SearchResult(title="B", url="https://example.com/b", snippet="s")])
    provider = FallbackSearchProvider("duckduckgo", primary, "wikipedia", fallback)

    results = provider.search("dogs", limit=5)

    assert [result.title for result in results] == ["A"]
    assert provider.pop_warnings() == []


def test_fallback_search_on_primary_zero_results():
    primary = StaticProvider([])
    fallback = StaticProvider([SearchResult(title="Wiki", url="https://en.wikipedia.org/?curid=1", snippet="s")])
    provider = FallbackSearchProvider("duckduckgo", primary, "wikipedia", fallback)

    results = provider.search("dogs", limit=5)
    warnings = provider.pop_warnings()

    assert len(results) == 1
    assert any("returned no results" in warning for warning in warnings)


def test_fallback_search_on_primary_exception():
    primary = ErrorProvider(requests.RequestException("network down"))
    fallback = StaticProvider([SearchResult(title="Wiki", url="https://en.wikipedia.org/?curid=1", snippet="s")])
    provider = FallbackSearchProvider("duckduckgo", primary, "wikipedia", fallback)

    results = provider.search("dogs", limit=5)
    warnings = provider.pop_warnings()

    assert len(results) == 1
    assert any("failed (RequestException)" in warning for warning in warnings)
    assert any("Tried fallback provider" in warning for warning in warnings)


def test_fallback_search_empty_when_fallback_has_no_results():
    provider = FallbackSearchProvider("duckduckgo", StaticProvider([]), "wikipedia", StaticProvider([]))

    results = provider.search("dogs", limit=5)
    warnings = provider.pop_warnings()

    assert results == []
    assert any("returned no results" in warning for warning in warnings)


def test_fallback_search_empty_when_fallback_fails():
    provider = FallbackSearchProvider(
        "duckduckgo",
        ErrorProvider(ValueError("parse error")),
        "wikipedia",
        ErrorProvider(requests.HTTPError("bad gateway")),
    )

    results = provider.search("dogs", limit=5)
    warnings = provider.pop_warnings()

    assert results == []
    assert any("Primary search provider 'duckduckgo' failed (ValueError)." in warning for warning in warnings)
    assert any("Fallback search provider 'wikipedia' failed (HTTPError)." in warning for warning in warnings)


def test_wikipedia_search_parses_response_without_live_http():
    provider = WikipediaSearchProvider(timeout=2, user_agent="test-agent")
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {
        "query": {
            "search": [
                {"title": "Dog", "pageid": 123, "snippet": "Domesticated <b>dog</b>"},
                {"title": "", "pageid": 456, "snippet": "skip"},
            ]
        }
    }

    with patch("app.services.search.requests.get", return_value=response) as get_mock:
        results = provider.search("dog", limit=5)

    get_mock.assert_called_once()
    assert len(results) == 1
    assert results[0].url == "https://en.wikipedia.org/?curid=123"
    assert results[0].snippet == "Domesticated dog"
