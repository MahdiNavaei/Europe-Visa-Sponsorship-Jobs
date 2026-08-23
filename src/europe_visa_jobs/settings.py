from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./europe_visa_jobs.db"
    log_level: str = "INFO"
    request_timeout_seconds: float = 20.0
    web_origin: str = "http://localhost:3000"
    discovery_timeout_seconds: float = 30.0
    discovery_retry_attempts: int = 3
    discovery_concurrency: int = 8
    discovery_index_concurrency: int = 2
    discovery_common_crawl_max_pages: int = 20
    discovery_urlscan_max_pages: int = 10
    discovery_checkpoint_size: int = 100
    discovery_batch_size: int = 250
    discovery_verified_stale_hours: int = 24 * 7
    discovery_invalid_retry_days: int = 30
    discovery_blocked_retry_hours: int = 24 * 14
    discovery_transient_retry_minutes: int = 60
    discovery_user_agent: str = "CareerRadar/1.0 (+https://github.com/MahdiNavaei/Europe-Visa-Sponsorship-Jobs)"
    discovery_contact: str | None = None
    ingestion_concurrency: int = 4

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
