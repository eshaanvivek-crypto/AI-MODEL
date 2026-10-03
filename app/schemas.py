from datetime import datetime
from pydantic import BaseModel, Field


class StageStatus(BaseModel):
    stage: str
    status: str
    detail: str | None = None


class SourceMetadata(BaseModel):
    id: int
    title: str
    url: str
    publisher: str
    retrieved_at: datetime
    snippet: str = ""


class ResearchRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1000)
    max_queries: int = Field(default=3, ge=1, le=5)
    max_sources: int = Field(default=5, ge=1, le=8)


class ResearchResponse(BaseModel):
    question: str
    report: str
    sources: list[SourceMetadata]
    stages: list[StageStatus]
    warnings: list[str] = []
    uncertainty: str | None = None
    setup_error: str | None = None
