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
