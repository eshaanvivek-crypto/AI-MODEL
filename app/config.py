from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    llm_provider: str = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    search_provider: str = "duckduckgo"
    serpapi_api_key: str | None = None

    http_timeout_seconds: int = Field(default=8, ge=2, le=20)
    max_search_results: int = Field(default=5, ge=1, le=10)
    max_page_chars: int = Field(default=8000, ge=1000, le=20000)
    user_agent: str = "AI-MODEL-ResearchAssistant/1.0"
