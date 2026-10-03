from __future__ import annotations

from unittest.mock import Mock, patch

from app.services.search import FallbackSearchProvider, SearchResult, WikipediaSearchProvider


def test_wikipedia_search_parser_parses_api_payload() -> None:
    provider = WikipediaSearchProvider(timeout=5, user_agent="test-agent")
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "query": {
            "search": [
                {"title": "Dog", "snippet": "<span>Domestic dog</span> is a domesticated mammal."},
                {"title": "Dog breed", "snippet": "<i>Dog breeds</i> vary widely."},
            ]
        }
    }

    with patch("app.services.search.requests.get", return_value=response):
        hits = provider.search("dogs", limit=2)

    assert len(hits) == 2
    assert hits[0].title == "Dog"
    assert "Domestic dog" in hits[0].snippet
    assert hits[0].url.startswith("https://en.wikipedia.org/wiki/")


def test_fallback_search_uses_backup_when_primary_returns_empty() -> None:
    primary = Mock()
    primary.search.return_value = []
    fallback = Mock()
    fallback.search.return_value = [SearchResult(title="Dog", url="https://example.com/dog", snippet="Canine")]

    provider = FallbackSearchProvider(primary=primary, fallback=fallback)
    hits = provider.search("dogs", limit=3)

    assert len(hits) == 1
    assert hits[0].title == "Dog"


def test_fallback_search_raises_after_all_failures() -> None:
    primary = Mock()
    primary.search.side_effect = RuntimeError("primary down")
    fallback = Mock()
    fallback.search.side_effect = RuntimeError("fallback down")

    provider = FallbackSearchProvider(primary=primary, fallback=fallback)

    try:
        provider.search("dogs", limit=3)
        raise AssertionError("Expected RuntimeError")
    except RuntimeError:
        pass


def test_workflow_warns_when_search_returns_no_results() -> None:
    from app.schemas import ResearchRequest
    from app.workflow import AssistantServices, ResearchAssistant, run_research
    from app.config import Settings
    from app.services.llm import HeuristicLLMProvider, LLMSetupState
    from app.services.fetch import PageFetcher

    class EmptySearchProvider:
        def search(self, query: str, limit: int):
            return []

    services = AssistantServices(
        llm_state=LLMSetupState(provider=HeuristicLLMProvider()),
        search_provider=EmptySearchProvider(),
        fetcher=PageFetcher(timeout=5, user_agent="test-agent"),
        settings=Settings(llm_provider="mock", openai_api_key=None, search_provider="mock"),
    )

    response = run_research(ResearchRequest(question="research about dogs", max_queries=3, max_sources=2), services)

    assert response.sources == []
    assert response.uncertainty is not None
    assert any("No search results" in warning or "No results" in warning for warning in response.warnings)
    search_stage = next(stage for stage in response.stages if stage.stage == "search")
    assert search_stage.status == "warning"
