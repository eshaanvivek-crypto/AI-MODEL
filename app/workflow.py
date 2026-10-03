from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.citations import deterministic_report, validate_citations
from app.config import Settings
from app.guardrails import is_safe_url, normalize_url
from app.schemas import ResearchRequest, ResearchResponse, SourceMetadata, StageStatus
from app.services.extract import extract_evidence_snippet, extract_page_text
from app.services.fetch import PageFetcher
from app.services.llm import HeuristicLLMProvider, LLMProvider, LLMSetupState, OpenAILLMProvider
from app.services.search import (
    DuckDuckGoSearchProvider,
    MockSearchProvider,
    SearchProvider,
    SerpAPISearchProvider,
    domain_of,
)


@dataclass
class AssistantServices:
    llm_state: LLMSetupState
    search_provider: SearchProvider
    fetcher: PageFetcher
    settings: Settings


class SetupError(Exception):
    pass


def build_services(settings: Settings) -> AssistantServices:
    llm_state = _build_llm(settings)
    search_provider = _build_search_provider(settings)
    fetcher = PageFetcher(timeout=settings.http_timeout_seconds, user_agent=settings.user_agent)
    return AssistantServices(llm_state=llm_state, search_provider=search_provider, fetcher=fetcher, settings=settings)


def _build_llm(settings: Settings) -> LLMSetupState:
    provider = settings.llm_provider.lower()
    if provider == "openai":
        if not settings.openai_api_key:
            return LLMSetupState(
                provider=HeuristicLLMProvider(),
                setup_error="OPENAI_API_KEY is missing. Running in limited heuristic mode.",
            )
        return LLMSetupState(provider=OpenAILLMProvider(settings.openai_api_key, settings.openai_model))
    if provider == "mock":
        return LLMSetupState(provider=HeuristicLLMProvider())
    return LLMSetupState(
        provider=HeuristicLLMProvider(),
        setup_error=f"Unsupported LLM_PROVIDER '{settings.llm_provider}'. Using limited heuristic mode.",
    )


def _build_search_provider(settings: Settings) -> SearchProvider:
    provider = settings.search_provider.lower()
    if provider == "duckduckgo":
        return DuckDuckGoSearchProvider(timeout=settings.http_timeout_seconds, user_agent=settings.user_agent)
    if provider == "serpapi":
        if not settings.serpapi_api_key:
            raise SetupError("SEARCH_PROVIDER is serpapi but SERPAPI_API_KEY is missing.")
        return SerpAPISearchProvider(
            api_key=settings.serpapi_api_key,
            timeout=settings.http_timeout_seconds,
            user_agent=settings.user_agent,
        )
    if provider == "mock":
        return MockSearchProvider()
    raise SetupError(f"Unsupported SEARCH_PROVIDER '{settings.search_provider}'.")


def _dedupe_sources(sources: list[SourceMetadata]) -> list[SourceMetadata]:
    seen: set[str] = set()
    deduped: list[SourceMetadata] = []
    for source in sources:
        key = normalize_url(source.url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(source)
    return deduped


def run_research(request: ResearchRequest, services: AssistantServices) -> ResearchResponse:
    stages: list[StageStatus] = []
    warnings: list[str] = []
    setup_error = services.llm_state.setup_error

    stages.append(StageStatus(stage="question_intake", status="ok"))

    llm: LLMProvider = services.llm_state.provider
    queries = llm.plan_queries(request.question, request.max_queries)
    stages.append(StageStatus(stage="query_planning", status="ok", detail=f"Generated {len(queries)} queries"))

    raw_hits = []
    for query in queries:
        try:
            hits = services.search_provider.search(query, limit=services.settings.max_search_results)
            raw_hits.extend(hits)
        except Exception as exc:
            warnings.append(f"Search failure for query '{query}': {exc}")

    stages.append(StageStatus(stage="search", status="ok", detail=f"Collected {len(raw_hits)} raw results"))

    sources: list[SourceMetadata] = []
    evidence_lines: list[str] = []
    for hit in raw_hits:
        if len(sources) >= request.max_sources:
            break
        if not is_safe_url(hit.url):
            warnings.append(f"Skipped unsafe URL: {hit.url}")
            continue
        try:
            html = services.fetcher.fetch(hit.url)
            text = extract_page_text(html, services.settings.max_page_chars)
            snippet = extract_evidence_snippet(text)
            if not snippet:
                continue
            source = SourceMetadata(
                id=len(sources) + 1,
                title=hit.title,
                url=hit.url,
                publisher=domain_of(hit.url) or "unknown",
                retrieved_at=datetime.now(timezone.utc),
                snippet=hit.snippet or snippet[:180],
            )
            sources.append(source)
            evidence_lines.append(f"{snippet} [{source.id}]")
        except Exception as exc:
            warnings.append(f"Retrieval failed for {hit.url}: {exc}")

    stages.append(StageStatus(stage="source_retrieval", status="ok", detail=f"Retrieved {len(sources)} sources"))

    sources = _dedupe_sources(sources)
    for idx, src in enumerate(sources, start=1):
        src.id = idx

    remapped_lines: list[str] = []
    for idx, src in enumerate(sources, start=1):
        remapped_lines.append(f"{src.title}: {src.snippet} [{idx}]")

    stages.append(StageStatus(stage="text_extraction", status="ok", detail=f"Extracted evidence from {len(sources)} sources"))
    stages.append(StageStatus(stage="evidence_claim_extraction", status="ok", detail=f"Extracted {len(remapped_lines)} evidence lines"))

    if not sources:
        uncertainty = "No reliable sources were retrieved. Response quality is limited."
    else:
        uncertainty = None

    report = llm.draft_report(request.question, remapped_lines, len(sources))
    valid, citation_error = validate_citations(report, sources)
    if not valid:
        warnings.append(f"Citation validation fallback applied: {citation_error}")
        report = deterministic_report(request.question, remapped_lines, uncertainty=uncertainty)

    stages.append(StageStatus(stage="report_generation", status="ok"))
    stages.append(StageStatus(stage="citation_validation", status="ok" if valid else "fallback", detail=citation_error))

    return ResearchResponse(
        question=request.question,
        report=report,
        sources=sources,
        stages=stages,
        warnings=warnings,
        uncertainty=uncertainty,
        setup_error=setup_error,
    )


class ResearchAssistant:
    def __init__(self, services: AssistantServices):
        self.services = services

    def research(self, request: ResearchRequest) -> ResearchResponse:
        return run_research(request, self.services)
