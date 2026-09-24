"""Application settings, validated once at startup so bad config fails fast."""

import re
from functools import lru_cache
from typing import Annotated, Literal, Self

from limits import parse as parse_rate_limit
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_ORIGIN_RE = re.compile(r"https?://[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?(?::\d{1,5})?")
_ASYNC_DRIVER = "postgresql+asyncpg://"


def normalize_database_url(url: str) -> str:
    """Return the SQLAlchemy asyncpg form of a Postgres URL (Supabase hands out plain postgresql://)."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return _ASYNC_DRIVER + url[len(prefix) :]
    if url.startswith(_ASYNC_DRIVER):
        return url
    raise ValueError(
        "database URL must start with postgresql://, postgres:// or postgresql+asyncpg://"
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DDQ_",
        env_file=".env",
        extra="ignore",
        frozen=True,
        # Validation errors otherwise echo the raw input (a DB URL with its password).
        hide_input_in_errors=True,
    )

    # No default on purpose: a production host that loses this variable must fail to start
    # rather than quietly run with local (HSTS-off, http-origin) behaviour.
    environment: Literal["local", "test", "production"]
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: SecretStr
    database_migration_url: SecretStr | None = None
    allowed_origins: Annotated[tuple[str, ...], NoDecode]
    rate_limit_default: str = "120/minute"
    trusted_proxy_hops: int = Field(default=0, ge=0, le=5)
    max_request_bytes: int = Field(default=1_048_576, ge=1024)

    @field_validator("database_url", "database_migration_url")
    @classmethod
    def _normalise_database_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        return SecretStr(normalize_database_url(value.get_secret_value()))

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(part.strip() for part in value.split(",") if part.strip())
        return value

    @field_validator("allowed_origins")
    @classmethod
    def _check_origins(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("at least one allowed origin is required")
        for origin in value:
            if not _ORIGIN_RE.fullmatch(origin):
                raise ValueError(
                    f"invalid origin {origin!r}: use scheme://host[:port] with no path, "
                    "trailing slash or wildcard"
                )
        return value

    @field_validator("rate_limit_default")
    @classmethod
    def _check_rate_limit(cls, value: str) -> str:
        parse_rate_limit(value)  # raises ValueError on an invalid expression
        return value

    @model_validator(mode="after")
    def _production_requires_https(self) -> Self:
        if self.environment == "production" and any(
            not origin.startswith("https://") for origin in self.allowed_origins
        ):
            raise ValueError("production allowed_origins must all use https")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment
