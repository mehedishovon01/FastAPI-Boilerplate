"""Application configuration loaded from environment variables.

Uses Pydantic Settings v2. All settings are validated on import; if a required
value is missing or malformed the app will fail fast at startup.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import EmailStr, Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---------- Application ----------
    PROJECT_NAME: str = "FastAPI Boilerplate"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "A clean, production-ready FastAPI boilerplate."
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # ---------- Server ----------
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ---------- Security ----------
    SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60

    # ---------- CORS ----------
    # ``NoDecode`` tells pydantic-settings *not* to JSON-decode this value,
    # so we can accept a plain comma-separated string from .env and convert
    # it to a list in the validator below.
    BACKEND_CORS_ORIGINS: Annotated[list[str], NoDecode] = []

    # ---------- Database ----------
    DATABASE_URL: str = "sqlite:///./app.db"

    # ---------- First superuser ----------
    FIRST_SUPERUSER_EMAIL: EmailStr | None = None
    FIRST_SUPERUSER_USERNAME: str | None = None
    FIRST_SUPERUSER_PASSWORD: str | None = None

    # ---------- Email ----------
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_TLS: bool = True
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    # Accept comma-separated string from .env and turn it into a list
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so Settings() is only instantiated once per process."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
