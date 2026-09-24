import pytest
from pydantic import ValidationError

from ddq_api.core.config import Settings, normalize_database_url

BASE = {
    "environment": "local",
    "database_url": "postgresql://user:hunter2@db.example.com:6543/postgres",
    "allowed_origins": "http://localhost:5173",
}


def make(**overrides: object) -> Settings:
    return Settings(_env_file=None, **{**BASE, **overrides})  # type: ignore[arg-type]


def test_missing_database_url_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DDQ_DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(  # type: ignore[call-arg]
            _env_file=None, environment="local", allowed_origins="http://localhost:5173"
        )


def test_reads_ddq_prefixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DDQ_ENVIRONMENT", "local")
    monkeypatch.setenv("DDQ_DATABASE_URL", "postgresql://u:p@h:6543/db")
    monkeypatch.setenv("DDQ_ALLOWED_ORIGINS", "http://localhost:5173,https://app.example.com")
    monkeypatch.setenv("DDQ_TRUSTED_PROXY_HOPS", "1")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.allowed_origins == ("http://localhost:5173", "https://app.example.com")
    assert settings.trusted_proxy_hops == 1


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgresql://u:p@h/db", "postgresql+asyncpg://u:p@h/db"),
        ("postgres://u:p@h/db", "postgresql+asyncpg://u:p@h/db"),
        ("postgresql+asyncpg://u:p@h/db", "postgresql+asyncpg://u:p@h/db"),
    ],
)
def test_normalize_database_url(raw: str, expected: str) -> None:
    assert normalize_database_url(raw) == expected


def test_normalize_rejects_other_schemes() -> None:
    with pytest.raises(ValueError, match="must start with"):
        normalize_database_url("mysql://u:p@h/db")


def test_settings_normalise_both_urls() -> None:
    s = make(database_migration_url="postgres://u:p@h:5432/db")
    assert s.database_url.get_secret_value().startswith("postgresql+asyncpg://")
    assert s.database_migration_url is not None
    assert s.database_migration_url.get_secret_value().startswith("postgresql+asyncpg://")


def test_origins_are_split_and_trimmed() -> None:
    s = make(allowed_origins=" http://a.example.com , https://b.example.com ")
    assert s.allowed_origins == ("http://a.example.com", "https://b.example.com")


@pytest.mark.parametrize(
    "bad",
    [
        "*",
        "http://a.example.com/",
        "http://a.example.com/path",
        "ftp://a.example.com",
        "",
        "https://*.vercel.app",
        "https://user@a.example.com",
        "https://a.example.com?x=1",
    ],
)
def test_rejects_wildcard_slash_path_and_empty_origins(bad: str) -> None:
    with pytest.raises(ValidationError):
        make(allowed_origins=bad)


def test_production_requires_https_origins() -> None:
    with pytest.raises(ValidationError, match="https"):
        make(environment="production", allowed_origins="http://app.example.com")
    assert make(environment="production", allowed_origins="https://app.example.com")


def test_rejects_invalid_rate_limit_expression() -> None:
    with pytest.raises(ValidationError):
        make(rate_limit_default="banana")
    assert make(rate_limit_default="5/second").rate_limit_default == "5/second"


def test_settings_are_immutable() -> None:
    s = make()
    with pytest.raises(ValidationError):
        s.environment = "production"  # type: ignore[misc]


def test_secrets_are_masked_in_repr() -> None:
    assert "hunter2" not in repr(make())


def test_validation_errors_never_echo_the_password() -> None:
    """Review focus 2: a bad URL must not leak credentials into startup logs."""
    with pytest.raises(ValidationError) as excinfo:
        make(database_url="mysql://user:hunter2@db.example.com/postgres")
    assert "hunter2" not in str(excinfo.value)


def test_environment_must_be_stated_explicitly(monkeypatch: pytest.MonkeyPatch) -> None:
    """A production box that loses DDQ_ENVIRONMENT must fail to start, not silently run as local."""
    monkeypatch.delenv("DDQ_ENVIRONMENT", raising=False)
    without_environment = {k: v for k, v in BASE.items() if k != "environment"}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **without_environment)  # type: ignore[arg-type]


@pytest.mark.parametrize("good", ["http://localhost:5173", "https://app.example.com:8443"])
def test_accepts_well_formed_origins(good: str) -> None:
    assert make(allowed_origins=good).allowed_origins == (good,)


def test_origin_validator_itself_rejects_a_trailing_newline() -> None:
    """Tuple input skips the comma splitter (which trims), so the regex must not rely on `$`."""
    with pytest.raises(ValidationError):
        make(allowed_origins=("http://a.example.com\n",))
