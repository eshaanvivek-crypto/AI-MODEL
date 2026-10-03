from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.schemas import ResearchRequest, ResearchResponse
from app.workflow import ResearchAssistant, SetupError, build_services

app = FastAPI(title="AI-MODEL Research Assistant", version="0.1.0")

UI_DIR = Path(__file__).resolve().parent / "ui"
app.mount("/static", StaticFiles(directory=UI_DIR), name="static")


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_assistant() -> ResearchAssistant:
    settings = get_settings()
    services = build_services(settings)
    return ResearchAssistant(services)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (UI_DIR / "index.html").read_text(encoding="utf-8")


@app.post("/api/research", response_model=ResearchResponse)
def research(
    payload: ResearchRequest,
    assistant: ResearchAssistant = Depends(get_assistant),
) -> ResearchResponse:
    try:
        return assistant.research(payload)
    except SetupError as exc:
        return ResearchResponse(
            question=payload.question,
            report="Configuration error prevents full research workflow.",
            sources=[],
            stages=[],
            warnings=[],
            uncertainty="Unable to run due to configuration error.",
            setup_error=str(exc),
        )
