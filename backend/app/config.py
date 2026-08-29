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

    # Agent behaviour. Tuning knobs, not methodology: none of these change what
    # a score means, so two deployments still rank an airport identically. The
    # assumptions that DO move scores - passenger weight, runway ceilings, the
    # tie band - stay in code and are published in `provenance`.
    history_messages: int = 6
    default_result_limit: int = 10
    max_clarify_rounds: int = 3
    max_fact_airports: int = 5
    max_live_lookups: int = 5
    max_attributed_rows: int = 10

    # Startup data acquisition.
    warm_attempts: int = 3
    warm_backoff_seconds: float = 2.0
    t100_page_size: int = 1000

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
