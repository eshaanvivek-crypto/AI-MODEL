from app.config import Settings
from app.schemas import ResearchRequest
from app.services.llm import HeuristicLLMProvider, LLMSetupState
from app.workflow import AssistantServices, run_research


class FakeSearchProvider:
    def search(self, query: str, limit: int):
        return [type("Hit", (), {"title": "A", "url": "https://example.com/a", "snippet": "A snippet"})()]


class FakeFetcher:
    def fetch(self, url: str) -> str:
        return "<html><body><h1>Title</h1><p>Evidence sentence one.</p><p>Sentence two.</p></body></html>"


class EmptySearchProvider:
    def search(self, query: str, limit: int):
        return []


class FailingSearchProvider:
    def search(self, query: str, limit: int):
        raise RuntimeError("boom")


class WarningSearchProvider:
    def search(self, query: str, limit: int):
        return []

    def pop_warnings(self):
        return ["Primary search provider 'duckduckgo' failed (RequestException). Tried fallback provider 'wikipedia'."]


def test_workflow_runs_and_returns_sources():
    settings = Settings(search_provider="mock", llm_provider="mock")
    services = AssistantServices(
        llm_state=LLMSetupState(provider=HeuristicLLMProvider()),
        search_provider=FakeSearchProvider(),
        fetcher=FakeFetcher(),
        settings=settings,
    )
    response = run_research(ResearchRequest(question="What is tested?"), services)

    assert response.question == "What is tested?"
    assert len(response.stages) >= 7
    assert len(response.sources) == 1
    assert "Findings" in response.report


def test_workflow_marks_search_empty_when_no_results():
    settings = Settings(search_provider="mock", llm_provider="mock")
    services = AssistantServices(
        llm_state=LLMSetupState(provider=HeuristicLLMProvider()),
        search_provider=EmptySearchProvider(),
        fetcher=FakeFetcher(),
        settings=settings,
    )

    response = run_research(ResearchRequest(question="What is tested?", max_queries=1), services)
    search_stage = next(stage for stage in response.stages if stage.stage == "search")
    assert search_stage.status == "empty"
    assert "Collected 0 raw results" in (search_stage.detail or "")
    assert "No results were found from the configured search providers." in response.warnings


def test_workflow_marks_search_failed_when_search_raises():
    settings = Settings(search_provider="mock", llm_provider="mock")
    services = AssistantServices(
        llm_state=LLMSetupState(provider=HeuristicLLMProvider()),
        search_provider=FailingSearchProvider(),
        fetcher=FakeFetcher(),
        settings=settings,
    )

    response = run_research(ResearchRequest(question="What is tested?", max_queries=1), services)
    search_stage = next(stage for stage in response.stages if stage.stage == "search")
    assert search_stage.status == "failed"
    assert "query failures" in (search_stage.detail or "")
    assert any("Search failure for query" in warning for warning in response.warnings)
    assert "No results were found because all search attempts failed." in response.warnings


def test_workflow_includes_provider_fallback_warning():
    settings = Settings(search_provider="mock", llm_provider="mock")
    services = AssistantServices(
        llm_state=LLMSetupState(provider=HeuristicLLMProvider()),
        search_provider=WarningSearchProvider(),
        fetcher=FakeFetcher(),
        settings=settings,
    )

    response = run_research(ResearchRequest(question="What is tested?", max_queries=1), services)
    assert any("Tried fallback provider 'wikipedia'" in warning for warning in response.warnings)
