from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """All runtime configuration. Values come from environment variables or carbon_backend/.env."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Carbon Tracker API"
    app_version: str = "1.0.0"
    log_level: str = "INFO"

    database_url: str
    firebase_project_id: str = "carbon-tracker-622b1"
    access_token_ttl_days: int = Field(default=7, ge=1)

    # Exact origins, e.g. CORS_ORIGINS='["https://carbon.example.com"]'.
    cors_origins: list[str] = []
    # Any localhost port by default, so Vite and `flutter run -d chrome` work without extra config.
    cors_origin_regex: str | None = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"

    @field_validator("cors_origin_regex")
    @classmethod
    def empty_regex_disables(cls, value: str | None) -> str | None:
        return value or None

    @field_validator("database_url")
    @classmethod
    def use_psycopg3_driver(cls, value: str) -> str:
        # requirements.txt ships psycopg 3; a bare postgresql:// URL would make SQLAlchemy load psycopg2.
        for prefix in ("postgresql://", "postgres://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value.removeprefix(prefix)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
