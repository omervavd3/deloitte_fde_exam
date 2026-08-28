from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/airport"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "airport-investment-agent"

    cors_origins: str = "http://localhost:5173"

    live_cache_ttl_seconds: int = 90
    http_timeout_seconds: float = 10.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
