# Phase 0: Foundation and Walking Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a live, CI-gated walking skeleton: a Vercel-hosted React SPA that shows real API and database health from a Render-hosted FastAPI service backed by Supabase Postgres, with light/dark theme, migrations, secrets policy, contract-first types and ADRs.

**Architecture:** uv-workspace Python monorepo (`packages/analytics` pure core + `apps/api` FastAPI) and a standalone pnpm project (`apps/web`). The API is a factory (`create_app(settings, db_health=…)`) with fail-fast settings, envelope responses, hardened middleware and a DB readiness port. The SPA consumes TS types generated from the API's committed `openapi.json`; CI fails on drift.

**Tech Stack:** Python 3.12, uv, FastAPI, Pydantic v2 + pydantic-settings, SQLAlchemy 2 async + asyncpg, Alembic, `limits`, pytest, ruff, mypy, import-linter · Node 22+/pnpm, Vite, React 19, TypeScript strict, Tailwind v4, TanStack Query, openapi-fetch/openapi-typescript, Vitest + Testing Library · GitHub Actions, Render (native Python), Vercel, Supabase.

**Spec:** `docs/PLAN.md` (approved, v0.1). Phase 0 is defined in its §13.

## Global Constraints

(Copied from the approved spec; every task inherits these.)

- No time estimates or deadlines anywhere in code, docs or commits.
- Free tiers and free data only. No paid services.
- **Immutability:** never mutate inputs; use `@dataclass(frozen=True)` / frozen Pydantic models / `readonly` TS types; new objects, not in-place edits.
- **File size:** 200–400 lines typical, 800 max. Functions < 50 lines. Nesting ≤ 4 levels.
- **Coverage:** ≥ 80% (gate enforced in `pytest` and `vitest`).
- **No debug statements:** no `print`, no `console.log` (ruff `T20` and ESLint `no-console` enforce this).
- **No hardcoded secrets.** Environment variables only; `.env` git-ignored; `.env.example` has no real values; the app fails fast at startup if a required secret is missing.
- **Error handling:** explicit at every boundary; never silently swallow; never leak stack traces or secrets in responses.
- **Input validation** at every system boundary; fail fast with clear messages.
- **API response envelope:** `{ "data": …, "error": null | {code, message, details}, "meta": {…} }` plus correct HTTP status codes.
- **Commit format:** `<type>: <description>` with types `feat, fix, refactor, docs, test, chore, perf, ci`. Attribution trailers are disabled globally, so add none.
- `ddq_analytics` must not import `ddq_api`, `fastapi`, `sqlalchemy`, `asyncpg`, or `httpx` (import-linter contract).
- Every table in `public` must have row-level security enabled (deny-all). The API is the only DB client.
- Sign convention (later phases): VaR/CVaR are positive losses.
- Security/outward-facing actions (publishing the repo, creating accounts, entering secrets) are done or explicitly confirmed by the user, never silently by the agent.

## Review Focus

Failure modes the spec implies that no ordinary happy-path test would cover (each is pinned by a test in the owning task):

1. **Render cold start returns an HTML 502/503 page, not JSON.** The SPA must show "offline/retry", never crash or hang on a JSON parse (Task 10).
2. **Config validation errors must not echo the database URL/password** into startup logs (Task 4).
3. **`/health` must stay 200 when the database is down** (the host's health check must not depend on Postgres, or Render will restart-loop the service) (Task 5).
4. **`localStorage` throws or is unavailable** (private mode, blocked storage): the theme must still work and never crash (Task 9).
5. **A spoofed `X-Forwarded-For`** must not let a client dodge or hijack another client's rate-limit bucket (Task 6).

---

## File Structure

```
ddq-portfolio-dashboard/
├─ .github/workflows/{ci.yml, keepwarm.yml}
├─ .env.example  .gitignore  .editorconfig  .python-version  .pre-commit-config.yaml
├─ LICENSE  README.md  pyproject.toml (uv workspace root + tool config)  uv.lock  render.yaml
├─ docs/
│   PLAN.md  architecture.md
│   adr/0000-template.md … 0011-*.md
│   ops/{free-tier-verification.md, setup-guide.md}
│   superpowers/plans/2026-09-24-phase-0-foundation.md   (this file)
├─ packages/analytics/
│   pyproject.toml
│   src/ddq_analytics/{__init__.py, py.typed}
│   tests/test_package.py
├─ apps/api/
│   pyproject.toml  alembic.ini  openapi.json
│   migrations/{env.py, script.py.mako, versions/0001_baseline.py}
│   src/ddq_api/
│     __init__.py  main.py  export_openapi.py
│     core/{config.py, logging.py, envelope.py, errors.py, handlers.py, middleware.py, db.py}
│     routers/{__init__.py, health.py}
│     ops/{__init__.py, smoke.py}
│   tests/{conftest.py, test_config.py, test_logging.py, test_envelope.py, test_app.py,
│          test_middleware.py, test_cors.py, test_rate_limit.py, test_db.py,
│          test_openapi_contract.py, test_smoke.py, integration/{conftest.py, test_database.py}}
└─ apps/web/
    package.json  vite.config.ts  index.html  vercel.json  eslint.config.js  .prettierrc
    public/theme-init.js
    src/{main.tsx, App.tsx, config.ts}
    src/styles/{index.css, tokens.css}
    src/theme/{theme.ts, ThemeContext.ts, ThemeProvider.tsx, ThemeToggle.tsx}
    src/api/{client.ts, schema.d.ts (generated)}
    src/features/status/{deriveStatus.ts, useApiStatus.ts, StatusPage.tsx}
    src/test/{setup.ts, utils.tsx, fakeFetch.ts}
    (+ colocated *.test.ts(x) files)
```

Responsibilities: `core/*` = cross-cutting infrastructure (one concern per file); `routers/*` = HTTP surface only; `ops/smoke.py` = post-deploy verification tooling; `ddq_analytics` = empty pure-Python shell so the dependency rule exists from day one.

---

### Task 1: Verify the free-tier assumptions

The approved plan rests on free-tier facts written from memory (spec §12). Confirm them before building on them.

**Files:**
- Create: `docs/ops/free-tier-verification.md`
- Modify (only if a fact changed): `docs/PLAN.md`

**Interfaces:**
- Consumes: none.
- Produces: `docs/ops/free-tier-verification.md`, a table later tasks and the README cite.

- [ ] **Step 1: Research each claim from primary sources** (WebFetch/WebSearch; vendor docs, not blogs). Claims to verify, with starting URLs:

| # | Claim | Start at |
|---|-------|----------|
| 1 | Render free web service sleeps when idle, has 512 MB RAM, no cron/workers; supports `autoDeployTrigger: checksPass`; native Python runtime and `.venv` persist to runtime | `https://render.com/docs/free`, `https://render.com/docs/blueprint-spec` |
| 2 | Fly.io has no free tier for new accounts | `https://fly.io/docs/about/pricing/` |
| 3 | Supabase free tier: 500 MB DB, pauses after ~1 week inactivity; direct connection is IPv6-only; pooler transaction mode (6543) / session mode (5432) exist and are IPv4 | `https://supabase.com/pricing`, `https://supabase.com/docs/guides/database/connecting-to-postgres` |
| 4 | Brevo free tier: daily send cap, sender-address verification only; Resend free tier requires a verified domain to send to third parties | `https://www.brevo.com/pricing/`, `https://resend.com/docs/dashboard/domains/introduction` |
| 5 | GitHub disables `schedule` workflows in public repos after 60 days of no repo activity; cron is best-effort | GitHub Docs → "Events that trigger workflows" → schedule |
| 6 | Vercel Hobby is non-commercial only | `https://vercel.com/docs/plans/hobby` |
| 7 | yfinance is unofficial/Yahoo-ToS-bound; current release still works | `https://github.com/ranaroussi/yfinance` (README disclaimer, latest release) |

- [ ] **Step 2: Write `docs/ops/free-tier-verification.md`** with one row per claim: `claim | verdict (confirmed / changed / unclear) | what the source says | source URL | date checked | impact on plan`. Put today's date in the header.

- [ ] **Step 3: Decision gate.** If any verdict is *changed* for claims 1–4 (they underpin decisions D2, D3, D4), STOP, summarize the impact for the user and ask how to proceed. Otherwise continue. If a fact changed but no decision breaks, update the matching row in `docs/PLAN.md` §12 in the same commit.

- [ ] **Step 4: Verify completeness**

Run: `Select-String -Path docs/ops/free-tier-verification.md -Pattern 'https://' | Measure-Object` (PowerShell)
Expected: `Count` ≥ 7 (every claim has a source URL).

- [ ] **Step 5: Commit** (after Task 2 creates the repo; if committing now is impossible, leave the file and it will be included in Task 2's initial commit).

---

### Task 2: Repository bootstrap and workspace tooling

**Files:**
- Create: `.gitignore`, `.editorconfig`, `.python-version`, `.env.example`, `LICENSE`, `.pre-commit-config.yaml`, `pyproject.toml`
- Create: `packages/analytics/pyproject.toml`, `packages/analytics/src/ddq_analytics/__init__.py`, `packages/analytics/src/ddq_analytics/py.typed`, `packages/analytics/tests/test_package.py`
- Create: `apps/api/pyproject.toml`, `apps/api/src/ddq_api/__init__.py`, `apps/api/tests/conftest.py`
- Test: `packages/analytics/tests/test_package.py`

**Interfaces:**
- Consumes: none.
- Produces: an installable uv workspace (`uv sync`), `ddq_analytics.__version__: str`, `ddq_api.__version__: str`, pytest/ruff/mypy/import-linter configuration used by every later task.

- [ ] **Step 1: Initialise git and check identity**

```powershell
cd C:\Users\Emman\Documents\CLAUDE\ddq-portfolio-dashboard
git init -b main
git config user.name
git config user.email
```
Expected: both print a value. If either is empty, ask the user which name/email to use for commits and set them with `git config user.name "…"` / `git config user.email "…"` (repo-local).

- [ ] **Step 2: Write `.gitignore`**

```gitignore
__pycache__/
*.py[cod]
.venv/
.env
.env.*
!.env.example
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
coverage.xml
htmlcov/
node_modules/
dist/
.vercel/
*.log
.DS_Store
```

- [ ] **Step 3: Write `.editorconfig`, `.python-version`, `.env.example`**

`.editorconfig`:
```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.{ts,tsx,js,json,yml,yaml,css,html,md}]
indent_size = 2
```

`.python-version`:
```
3.12
```

`.env.example`:
```dotenv
# Copy to .env (never commit .env). All API variables use the DDQ_ prefix.
DDQ_ENVIRONMENT=local
DDQ_LOG_LEVEL=INFO
# Runtime connection: Supabase TRANSACTION pooler (port 6543). URL-encode special characters in the password.
DDQ_DATABASE_URL=postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres
# Migrations: Supabase SESSION pooler (port 5432, IPv4-reachable from GitHub Actions and Render).
DDQ_DATABASE_MIGRATION_URL=postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres
# Comma-separated exact origins (scheme + host [+ port], no trailing slash, no wildcard).
DDQ_ALLOWED_ORIGINS=http://localhost:5173
DDQ_RATE_LIMIT_DEFAULT=120/minute
# Number of trusted reverse proxies in front of the API (0 = none, ignore X-Forwarded-For).
DDQ_TRUSTED_PROXY_HOPS=0
DDQ_MAX_REQUEST_BYTES=1048576
```

- [ ] **Step 4: Write `LICENSE`** (MIT). Use the name from `git config user.name` as the copyright holder and the current year (2026).

- [ ] **Step 5: Write the root `pyproject.toml`**

```toml
[project]
name = "ddq-portfolio-dashboard"
version = "0.0.0"
description = "DDQ (Data Driven Quant) Portfolio Dashboard: workspace root"
requires-python = ">=3.12"
dependencies = ["ddq-analytics", "ddq-api"]

[tool.uv]
package = false

[tool.uv.workspace]
members = ["packages/analytics", "apps/api"]

[tool.uv.sources]
ddq-analytics = { workspace = true }
ddq-api = { workspace = true }

[dependency-groups]
dev = [
  "pytest>=8.3",
  "pytest-asyncio>=0.24",
  "pytest-cov>=5.0",
  "ruff>=0.8",
  "mypy>=1.13",
  "import-linter>=2.1",
  "pip-audit>=2.7",
  "pre-commit>=4.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"
src = ["packages/analytics/src", "apps/api/src"]
extend-exclude = ["apps/web"]

[tool.ruff.lint]
# T20 forbids print(); S is bandit; ASYNC catches blocking calls in async code.
select = ["E", "F", "W", "I", "B", "UP", "SIM", "C4", "RUF", "S", "T20", "ASYNC", "PT"]

[tool.ruff.lint.per-file-ignores]
"**/tests/**" = ["S101", "S105", "S106"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
explicit_package_bases = true
mypy_path = "packages/analytics/src:apps/api/src"

[tool.pytest.ini_options]
testpaths = ["packages/analytics/tests", "apps/api/tests"]
asyncio_mode = "auto"
addopts = "--import-mode=importlib --cov=ddq_analytics --cov=ddq_api --cov-report=term-missing --cov-fail-under=80"
markers = ["integration: needs a real Postgres (set DDQ_TEST_DATABASE_URL to a THROWAWAY database)"]

[tool.importlinter]
root_packages = ["ddq_analytics", "ddq_api", "fastapi", "sqlalchemy", "asyncpg", "httpx"]
include_external_packages = true

[[tool.importlinter.contracts]]
name = "analytics core stays pure (no web, DB or network imports)"
type = "forbidden"
source_modules = ["ddq_analytics"]
forbidden_modules = ["ddq_api", "fastapi", "sqlalchemy", "asyncpg", "httpx"]
```

- [ ] **Step 6: Write the two package skeletons**

`packages/analytics/pyproject.toml`:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ddq-analytics"
version = "0.1.0"
description = "DDQ portfolio risk analytics core: pure Python, no I/O."
requires-python = ">=3.12"
dependencies = []

[tool.hatch.build.targets.wheel]
packages = ["src/ddq_analytics"]
```

`packages/analytics/src/ddq_analytics/__init__.py`:
```python
"""DDQ portfolio risk analytics core. Pure functions over DataFrames; no I/O."""

__version__ = "0.1.0"
```
`packages/analytics/src/ddq_analytics/py.typed`: empty file.

`apps/api/pyproject.toml`:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "ddq-api"
version = "0.1.0"
description = "DDQ Portfolio Dashboard API (FastAPI)."
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
  "pydantic>=2.9",
  "pydantic-settings>=2.7",
  "sqlalchemy[asyncio]>=2.0.36",
  "asyncpg>=0.30",
  "alembic>=1.14",
  "limits>=3.13",
  "httpx>=0.27",
]

[tool.hatch.build.targets.wheel]
packages = ["src/ddq_api"]
```

`apps/api/src/ddq_api/__init__.py`:
```python
"""DDQ Portfolio Dashboard API."""

from importlib.metadata import version

__version__ = version("ddq-api")
```

`apps/api/tests/conftest.py`: create as an empty file for now (Task 5 fills it).

- [ ] **Step 7: Write the failing test** `packages/analytics/tests/test_package.py`

```python
from importlib.metadata import version

import ddq_analytics


def test_version_matches_installed_metadata() -> None:
    assert ddq_analytics.__version__ == version("ddq-analytics")


def test_package_is_typed() -> None:
    from importlib.resources import files

    assert files("ddq_analytics").joinpath("py.typed").is_file()
```

- [ ] **Step 8: Install and run the test.** Note that `--no-cov` is used when running a subset (the coverage gate applies to the full suite).

```powershell
uv sync
uv run pytest packages/analytics/tests/test_package.py --no-cov -v
```
Expected: `uv sync` creates `.venv` and `uv.lock`; both tests PASS. (If Step 7's test had been run before Step 6 it would fail with `ModuleNotFoundError`; the RED/GREEN here is compressed because the skeleton is the deliverable.)

- [ ] **Step 9: Verify the static tooling**

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy packages/analytics/src apps/api/src
uv run lint-imports
```
Expected: all pass (`lint-imports`: `analytics core stays pure … KEPT`). If `lint-imports` errors that a listed external package is missing, remove that name from both lists in the root `pyproject.toml`.

- [ ] **Step 10: Prove the purity contract actually bites.** Temporarily add `import sqlalchemy  # noqa` to `packages/analytics/src/ddq_analytics/__init__.py`, run `uv run lint-imports`.
Expected: the contract is BROKEN and the command exits non-zero. Then revert the line and re-run: KEPT.

- [ ] **Step 11: Write `.pre-commit-config.yaml`** then refresh pins

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2
    hooks:
      - id: gitleaks
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff
      - id: ruff-format
```
Run: `uv run pre-commit autoupdate` then `uv run pre-commit install`.
Expected: `.git/hooks/pre-commit` installed. (If the gitleaks hook cannot bootstrap Go on this machine, keep it in CI only and remove it from this file, noting so in the commit message.)

- [ ] **Step 12: Commit**

```powershell
git add -A
git commit -m "chore: bootstrap uv workspace, tooling and analytics purity contract"
```

---

### Task 3: API settings, logging and envelope

**Files:**
- Create: `apps/api/src/ddq_api/core/__init__.py` (empty), `core/config.py`, `core/logging.py`, `core/envelope.py`
- Test: `apps/api/tests/test_config.py`, `apps/api/tests/test_logging.py`, `apps/api/tests/test_envelope.py`

**Interfaces:**
- Consumes: nothing from earlier tasks except the workspace.
- Produces:
  - `Settings` (frozen `BaseSettings`, prefix `DDQ_`) with fields `environment: Literal["local","test","production"]`, `log_level`, `database_url: SecretStr`, `database_migration_url: SecretStr | None`, `allowed_origins: tuple[str, ...]`, `rate_limit_default: str`, `trusted_proxy_hops: int`, `max_request_bytes: int`; `get_settings() -> Settings` (cached); `normalize_database_url(url: str) -> str`.
  - `configure_logging(level: str = "INFO") -> None`, `JsonFormatter`, `request_id_var: ContextVar[str]`.
  - `ErrorBody`, `Envelope[T]`, `ok(data, meta=None)`, `fail(code, message, details=None)`.

- [ ] **Step 1: Write the failing config tests** `apps/api/tests/test_config.py`

```python
import pytest
from pydantic import ValidationError

from ddq_api.core.config import Settings, normalize_database_url

BASE = {
    "database_url": "postgresql://user:hunter2@db.example.com:6543/postgres",
    "allowed_origins": "http://localhost:5173",
}


def make(**overrides: object) -> Settings:
    return Settings(_env_file=None, **{**BASE, **overrides})  # type: ignore[arg-type]


def test_missing_database_url_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DDQ_DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, allowed_origins="http://localhost:5173")  # type: ignore[call-arg]


def test_reads_ddq_prefixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
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
    "bad", ["*", "http://a.example.com/", "http://a.example.com/path", "ftp://a.example.com", ""]
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest apps/api/tests/test_config.py --no-cov -q`
Expected: FAIL (`ModuleNotFoundError: ddq_api.core`).

- [ ] **Step 3: Implement** `apps/api/src/ddq_api/core/config.py` (and an empty `core/__init__.py`)

```python
"""Application settings, validated once at startup so bad config fails fast."""

import re
from functools import lru_cache
from typing import Annotated, Literal, Self

from limits import parse as parse_rate_limit
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_ORIGIN_RE = re.compile(r"^https?://[^/\s]+$")
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
        env_prefix="DDQ_", env_file=".env", extra="ignore", frozen=True
    )

    environment: Literal["local", "test", "production"] = "local"
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
            if not _ORIGIN_RE.match(origin):
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
    return Settings()  # type: ignore[call-arg]  # values come from the environment
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest apps/api/tests/test_config.py --no-cov -q`
Expected: all PASS. (If `test_validation_errors_never_echo_the_password` fails, the validator is seeing the raw string; keep the fields typed as `SecretStr` so pydantic masks the input.)

- [ ] **Step 5: Write the failing logging and envelope tests**

`apps/api/tests/test_logging.py`:
```python
import io
import json
import logging

from ddq_api.core.logging import (
    JsonFormatter,
    configure_logging,
    request_id_var,
)


def _logger(stream: io.StringIO) -> logging.Logger:
    logger = logging.getLogger("test.json")
    logger.handlers.clear()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def test_emits_one_json_object_with_request_id_and_context() -> None:
    stream = io.StringIO()
    token = request_id_var.set("req-12345678")
    try:
        _logger(stream).info("hello", extra={"ctx": {"path": "/x"}})
    finally:
        request_id_var.reset(token)
    payload = json.loads(stream.getvalue())
    assert payload["msg"] == "hello"
    assert payload["level"] == "INFO"
    assert payload["request_id"] == "req-12345678"
    assert payload["path"] == "/x"


def test_request_id_defaults_to_dash() -> None:
    stream = io.StringIO()
    _logger(stream).info("hello")
    assert json.loads(stream.getvalue())["request_id"] == "-"


def test_context_cannot_overwrite_core_fields() -> None:
    stream = io.StringIO()
    _logger(stream).info("real", extra={"ctx": {"msg": "forged", "level": "FATAL"}})
    payload = json.loads(stream.getvalue())
    assert payload["msg"] == "real"
    assert payload["level"] == "INFO"


def test_includes_exception_text() -> None:
    stream = io.StringIO()
    logger = _logger(stream)
    try:
        raise ValueError("boom")
    except ValueError:
        logger.exception("failed")
    assert "ValueError: boom" in json.loads(stream.getvalue())["exc"]


def test_configure_logging_is_idempotent() -> None:
    configure_logging()
    configure_logging()
    flagged = [
        h for h in logging.getLogger().handlers if getattr(h, "_ddq_json_handler", False)
    ]
    assert len(flagged) == 1
```

`apps/api/tests/test_envelope.py`:
```python
import pytest
from pydantic import ValidationError

from ddq_api.core.envelope import Envelope, ErrorBody, fail, ok


def test_ok_wraps_data_with_empty_error_and_meta() -> None:
    assert ok({"a": 1}).model_dump(mode="json") == {"data": {"a": 1}, "error": None, "meta": {}}


def test_ok_copies_meta() -> None:
    meta = {"page": 1}
    envelope = ok([1], meta=meta)
    meta["page"] = 99
    assert envelope.meta == {"page": 1}


def test_fail_builds_error_body() -> None:
    body = fail("not_found", "nope", {"id": 3}).model_dump(mode="json")
    assert body == {
        "data": None,
        "error": {"code": "not_found", "message": "nope", "details": {"id": 3}},
        "meta": {},
    }


def test_envelope_is_frozen() -> None:
    envelope = ok(1)
    with pytest.raises(ValidationError):
        envelope.data = 2  # type: ignore[misc]


def test_error_body_is_frozen() -> None:
    with pytest.raises(ValidationError):
        ErrorBody(code="x", message="y").code = "z"  # type: ignore[misc]


def test_envelope_generic_parametrisation() -> None:
    assert Envelope[int](data=1).data == 1
```

- [ ] **Step 6: Run to verify failure**

Run: `uv run pytest apps/api/tests/test_logging.py apps/api/tests/test_envelope.py --no-cov -q`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 7: Implement**

`apps/api/src/ddq_api/core/logging.py`:
```python
"""Structured JSON logging with a per-request correlation id."""

import contextvars
import json
import logging
import sys
from typing import Any

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

_HANDLER_FLAG = "_ddq_json_handler"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        context = getattr(record, "ctx", None)
        core: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if record.exc_info:
            core["exc"] = self.formatException(record.exc_info)
        extra = context if isinstance(context, dict) else {}
        # Core fields win so callers cannot forge them (log-injection hardening).
        return json.dumps({**extra, **core}, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Install a single stdout JSON handler; safe to call repeatedly."""
    root = logging.getLogger()
    for handler in [h for h in root.handlers if getattr(h, _HANDLER_FLAG, False)]:
        root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    setattr(handler, _HANDLER_FLAG, True)
    root.addHandler(handler)
    root.setLevel(level)
```

`apps/api/src/ddq_api/core/envelope.py`:
```python
"""The single response envelope used by every endpoint."""

from collections.abc import Mapping
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorBody(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    details: dict[str, Any] | None = None


class Envelope(BaseModel, Generic[T]):
    model_config = ConfigDict(frozen=True)

    data: T | None = None
    error: ErrorBody | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


def ok(data: T, meta: Mapping[str, Any] | None = None) -> Envelope[T]:
    return Envelope(data=data, meta=dict(meta or {}))


def fail(
    code: str, message: str, details: dict[str, Any] | None = None
) -> Envelope[None]:
    return Envelope(error=ErrorBody(code=code, message=message, details=details))
```

- [ ] **Step 8: Run to verify pass, then lint/type-check**

```powershell
uv run pytest apps/api/tests --no-cov -q
uv run ruff check . ; uv run ruff format . ; uv run mypy packages/analytics/src apps/api/src
```
Expected: all PASS, ruff/mypy clean.

- [ ] **Step 9: Commit**

```powershell
git add -A
git commit -m "feat: add fail-fast settings, JSON logging and response envelope"
```

---

### Task 4: App factory, error handling and health endpoints

**Files:**
- Create: `core/errors.py`, `core/handlers.py`, `core/db.py`, `routers/__init__.py`, `routers/health.py`, `main.py` (all under `apps/api/src/ddq_api/`)
- Modify: `apps/api/tests/conftest.py`
- Test: `apps/api/tests/test_app.py`, `apps/api/tests/test_db.py`

**Interfaces:**
- Consumes: `Settings`, `get_settings`, `configure_logging`, `request_id_var`, `Envelope`, `ok`, `fail`, `ErrorBody` (Task 3).
- Produces:
  - `DomainError(message, *, details=None)` with `status_code: int`, `code: str`; subclasses `NotFoundError` (404 `not_found`), `ServiceUnavailableError` (503 `service_unavailable`).
  - `register_exception_handlers(app: FastAPI) -> None`.
  - `DatabaseHealth` Protocol (`async def ping(self) -> None`), `SqlAlchemyHealth(engine)`, `build_engine(database_url: str) -> AsyncEngine`.
  - `create_app(settings: Settings | None = None, *, db_health: DatabaseHealth | None = None) -> FastAPI`. State: `app.state.settings`, `app.state.db_health`.
  - Routes: `GET /health` → `Envelope[HealthOut]`; `GET /ready` → `Envelope[ReadyOut]` (200) or 503 envelope with `error.code == "not_ready"`.
  - Test fixtures: `settings`, `make_client(*, db_error=None, db_delay=0.0, **settings_overrides) -> TestClient`.

- [ ] **Step 1: Write shared test fixtures** `apps/api/tests/conftest.py`

```python
import asyncio
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ddq_api.core.config import Settings
from ddq_api.main import create_app


class FakeDbHealth:
    def __init__(self, error: Exception | None = None, delay: float = 0.0) -> None:
        self._error = error
        self._delay = delay

    async def ping(self) -> None:
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._error is not None:
            raise self._error


@pytest.fixture
def settings() -> Settings:
    return Settings(  # type: ignore[call-arg]
        _env_file=None,
        environment="test",
        database_url="postgresql://u:p@localhost:5432/db",
        allowed_origins="http://localhost:5173",
    )


@pytest.fixture
def make_client(settings: Settings) -> Callable[..., TestClient]:
    def _make(
        *, db_error: Exception | None = None, db_delay: float = 0.0, **overrides: Any
    ) -> TestClient:
        effective = settings.model_copy(update=overrides) if overrides else settings
        app = create_app(effective, db_health=FakeDbHealth(db_error, db_delay))
        return TestClient(app, raise_server_exceptions=False)

    return _make
```

- [ ] **Step 2: Write the failing tests** `apps/api/tests/test_app.py`

```python
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ddq_api.core.errors import DomainError, NotFoundError
from ddq_api.routers import health as health_module


def test_health_returns_ok_envelope(make_client: Any) -> None:
    response = make_client().get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["data"]["status"] == "ok"
    assert body["data"]["environment"] == "test"
    assert body["data"]["version"]


def test_health_stays_200_when_database_is_down(make_client: Any) -> None:
    """Review focus 3: the host health check must not depend on Postgres."""
    client = make_client(db_error=ConnectionError("db down"))
    assert client.get("/health").status_code == 200


def test_ready_ok_when_database_pings(make_client: Any) -> None:
    response = make_client().get("/ready")
    assert response.status_code == 200
    assert response.json()["data"] == {"status": "ready", "checks": {"database": {"ok": True}}}


def test_ready_returns_503_without_leaking_error_text(make_client: Any) -> None:
    client = make_client(db_error=ConnectionError("password=hunter2 host=internal"))
    response = client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "not_ready"
    assert body["data"]["checks"]["database"]["ok"] is False
    assert "hunter2" not in response.text


def test_ready_times_out_slow_database(
    make_client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(health_module, "_DB_TIMEOUT_S", 0.05)
    response = make_client(db_delay=1.0).get("/ready")
    assert response.status_code == 503


def test_unknown_route_uses_envelope(make_client: Any) -> None:
    response = make_client().get("/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_wrong_method_uses_envelope(make_client: Any) -> None:
    response = make_client().delete("/health")
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


def _client_with_routes(make_client: Any) -> TestClient:
    client: TestClient = make_client()
    app: FastAPI = client.app  # type: ignore[assignment]

    @app.get("/_test/echo/{number}")
    async def echo(number: int) -> dict[str, int]:
        return {"number": number}

    @app.get("/_test/domain")
    async def domain() -> None:
        raise NotFoundError("portfolio not found", details={"id": 7})

    @app.get("/_test/custom")
    async def custom() -> None:
        raise DomainError("bad thing")

    @app.get("/_test/boom")
    async def boom() -> None:
        raise RuntimeError("secret internal detail")

    return client


def test_validation_error_is_422_envelope_without_echoing_input(make_client: Any) -> None:
    response = _client_with_routes(make_client).get("/_test/echo/not-a-number")
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"]["errors"][0]["loc"] == ["path", "number"]
    assert "not-a-number" not in response.text


def test_domain_errors_map_to_status_and_code(make_client: Any) -> None:
    client = _client_with_routes(make_client)
    missing = client.get("/_test/domain")
    assert missing.status_code == 404
    assert missing.json()["error"] == {
        "code": "not_found",
        "message": "portfolio not found",
        "details": {"id": 7},
    }
    assert client.get("/_test/custom").status_code == 400


def test_unhandled_exception_is_generic_500(make_client: Any) -> None:
    response = _client_with_routes(make_client).get("/_test/boom")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "secret internal detail" not in response.text
    assert "Traceback" not in response.text
```

`apps/api/tests/test_db.py`:
```python
import pytest
from sqlalchemy.exc import SQLAlchemyError

from ddq_api.core.db import SqlAlchemyHealth, build_engine

URL = "postgresql+asyncpg://u:p@127.0.0.1:1/db"


def test_engine_disables_prepared_statement_cache_for_the_pooler() -> None:
    engine = build_engine(URL)
    assert engine.url.query["prepared_statement_cache_size"] == "0"


async def test_ping_raises_when_database_unreachable() -> None:
    engine = build_engine(URL)
    try:
        with pytest.raises((OSError, SQLAlchemyError)):
            await SqlAlchemyHealth(engine).ping()
    finally:
        await engine.dispose()
```

- [ ] **Step 3: Run to verify failure**

Run: `uv run pytest apps/api/tests/test_app.py apps/api/tests/test_db.py --no-cov -q`
Expected: FAIL (`ModuleNotFoundError: ddq_api.main`).

- [ ] **Step 4: Implement errors, handlers and the DB port**

`core/errors.py`:
```python
"""Domain errors: raised by services, translated to the envelope by handlers."""

from typing import Any


class DomainError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ServiceUnavailableError(DomainError):
    status_code = 503
    code = "service_unavailable"
```

`core/handlers.py`:
```python
"""Exception handlers: every failure leaves the API as an envelope, never a stack trace."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ddq_api.core.envelope import Envelope, fail
from ddq_api.core.errors import DomainError
from ddq_api.core.logging import request_id_var

logger = logging.getLogger("ddq_api.errors")

_HTTP_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    413: "payload_too_large",
    429: "rate_limited",
}


def _json(
    status: int, envelope: Envelope[Any], headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(status_code=status, content=envelope.model_dump(mode="json"), headers=headers)


async def _domain_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)  # noqa: S101  (narrowing for mypy)
    return _json(exc.status_code, fail(exc.code, exc.message, exc.details))


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    errors = [
        {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()
    ]  # input values are deliberately omitted: they may contain secrets
    return _json(422, fail("validation_error", "Request validation failed", {"errors": errors}))


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101
    code = _HTTP_CODES.get(exc.status_code, "http_error")
    headers = dict(exc.headers) if exc.headers else None
    return _json(exc.status_code, fail(code, str(exc.detail)), headers)


async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "-")
    token = request_id_var.set(request_id)
    try:
        logger.error("unhandled exception", exc_info=exc, extra={"ctx": {"path": request.url.path}})
    finally:
        request_id_var.reset(token)
    return _json(
        500,
        fail("internal_error", "An unexpected error occurred"),
        {"X-Request-ID": request_id},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unhandled)
```

`core/db.py`:
```python
"""Database engine construction and the readiness port."""

from typing import Protocol
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class DatabaseHealth(Protocol):
    async def ping(self) -> None: ...


def build_engine(database_url: str) -> AsyncEngine:
    """Async engine that is safe behind Supabase's transaction pooler (no prepared statements)."""
    url = make_url(database_url).update_query_dict({"prepared_statement_cache_size": "0"})
    return create_async_engine(
        url,
        pool_size=3,
        max_overflow=2,
        pool_recycle=1800,
        pool_pre_ping=True,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
        },
    )


class SqlAlchemyHealth:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def ping(self) -> None:
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
```
Before moving on, confirm the asyncpg/pgbouncer arguments against current SQLAlchemy docs via Context7 (`resolve-library-id` "sqlalchemy" → query "asyncpg pgbouncer prepared_statement_cache_size prepared_statement_name_func"). If the docs differ, adjust this function and `test_engine_disables_prepared_statement_cache_for_the_pooler` together.

- [ ] **Step 5: Implement the health router and app factory**

`routers/__init__.py`: empty.

`routers/health.py`:
```python
"""Liveness (/health) and readiness (/ready). Liveness must never touch dependencies."""

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ddq_api import __version__
from ddq_api.core.config import Settings
from ddq_api.core.envelope import Envelope, ErrorBody, ok

logger = logging.getLogger("ddq_api.health")
router = APIRouter(tags=["health"])

_DB_TIMEOUT_S = 3.0


class HealthOut(BaseModel):
    status: Literal["ok"]
    version: str
    environment: str


class CheckOut(BaseModel):
    ok: bool


class ReadyOut(BaseModel):
    status: Literal["ready", "degraded"]
    checks: dict[str, CheckOut]


@router.get("/health", response_model=Envelope[HealthOut])
async def health(request: Request) -> Envelope[HealthOut]:
    settings: Settings = request.app.state.settings
    return ok(HealthOut(status="ok", version=__version__, environment=settings.environment))


@router.get(
    "/ready",
    response_model=Envelope[ReadyOut],
    responses={503: {"model": Envelope[ReadyOut]}},
)
async def ready(request: Request) -> Envelope[ReadyOut] | JSONResponse:
    db_health = getattr(request.app.state, "db_health", None)
    db_ok = False
    if db_health is not None:
        try:
            await asyncio.wait_for(db_health.ping(), timeout=_DB_TIMEOUT_S)
            db_ok = True
        except Exception:  # any failure means "not ready"; detail is logged, never returned
            logger.warning("database readiness check failed", exc_info=True)

    body = ReadyOut(
        status="ready" if db_ok else "degraded", checks={"database": CheckOut(ok=db_ok)}
    )
    if db_ok:
        return ok(body)
    envelope = Envelope[ReadyOut](
        data=body,
        error=ErrorBody(code="not_ready", message="One or more dependencies are unavailable"),
    )
    return JSONResponse(status_code=503, content=envelope.model_dump(mode="json"))
```

`main.py`:
```python
"""ASGI application factory. Run: uvicorn ddq_api.main:create_app --factory"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ddq_api import __version__
from ddq_api.core.config import Settings, get_settings
from ddq_api.core.db import DatabaseHealth, SqlAlchemyHealth, build_engine
from ddq_api.core.handlers import register_exception_handlers
from ddq_api.core.logging import configure_logging
from ddq_api.routers import health


def create_app(
    settings: Settings | None = None, *, db_health: DatabaseHealth | None = None
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = None
        if db_health is None:
            engine = build_engine(settings.database_url.get_secret_value())
            app.state.db_health = SqlAlchemyHealth(engine)
        yield
        if engine is not None:
            await engine.dispose()

    app = FastAPI(title="DDQ Portfolio Dashboard API", version=__version__, lifespan=lifespan)
    app.state.settings = settings
    if db_health is not None:
        app.state.db_health = db_health

    register_exception_handlers(app)
    app.include_router(health.router)
    return app
```

- [ ] **Step 6: Run to verify pass**

Run: `uv run pytest apps/api/tests --no-cov -q`
Expected: all PASS. If the 405 test returns code `http_error`, check that `_HTTP_CODES` contains 405; if `test_unhandled_exception_is_generic_500` raises instead of returning 500, confirm the `TestClient(..., raise_server_exceptions=False)` argument in conftest.

- [ ] **Step 7: Lint, type-check, commit**

```powershell
uv run ruff check . ; uv run ruff format . ; uv run mypy packages/analytics/src apps/api/src
git add -A
git commit -m "feat: add app factory, envelope error handling and health/ready endpoints"
```

---

### Task 5: Request context, security headers, CORS, body limit and rate limiting

**Files:**
- Create: `apps/api/src/ddq_api/core/middleware.py`
- Modify: `apps/api/src/ddq_api/main.py` (install middleware)
- Test: `apps/api/tests/test_middleware.py`, `apps/api/tests/test_cors.py`, `apps/api/tests/test_rate_limit.py`

**Interfaces:**
- Consumes: `Settings`, `request_id_var`, `fail`, `create_app`, `make_client` fixture (Task 4).
- Produces: `client_ip(request: Request, hops: int) -> str`; `RequestContextMiddleware`, `SecurityHeadersMiddleware(app, hsts: bool)`, `BodySizeLimitMiddleware(app, max_bytes: int)`, `RateLimitMiddleware(app, rate: str, hops: int)`; `install_middleware(app: FastAPI, settings: Settings) -> None`. Response header `X-Request-ID` on every response.

Middleware order (outermost → innermost): RequestContext → SecurityHeaders → CORS → RateLimit → BodySizeLimit → routes. CORS sits outside the limiter and body limit so 429/413 responses still carry CORS headers and the browser can read them.

- [ ] **Step 1: Write the failing tests**

`apps/api/tests/test_middleware.py`:
```python
import logging
import re
from typing import Any

import pytest
from starlette.requests import Request

from ddq_api.core.middleware import client_ip


def _request(headers: dict[str, str], client: tuple[str, int] | None = ("10.0.0.1", 1234)) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": client,
    }
    return Request(scope)


def test_client_ip_ignores_forwarded_header_when_no_trusted_proxy() -> None:
    assert client_ip(_request({"x-forwarded-for": "9.9.9.9"}), hops=0) == "10.0.0.1"


def test_client_ip_takes_entry_appended_by_the_trusted_proxy() -> None:
    """Review focus 5: leftmost entries are attacker-controlled; the rightmost is the proxy's."""
    request = _request({"x-forwarded-for": "6.6.6.6, 9.9.9.9, 1.1.1.1"})
    assert client_ip(request, hops=1) == "1.1.1.1"
    assert client_ip(request, hops=2) == "9.9.9.9"


def test_client_ip_falls_back_when_header_shorter_than_hops() -> None:
    assert client_ip(_request({"x-forwarded-for": "1.1.1.1"}), hops=2) == "10.0.0.1"


def test_client_ip_without_client_is_unknown() -> None:
    assert client_ip(_request({}, client=None), hops=0) == "unknown"


def test_every_response_has_a_request_id(make_client: Any) -> None:
    response = make_client().get("/health")
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-request-id"])


def test_valid_incoming_request_id_is_kept(make_client: Any) -> None:
    response = make_client().get("/health", headers={"X-Request-ID": "trace-abc_12345"})
    assert response.headers["x-request-id"] == "trace-abc_12345"


def test_invalid_incoming_request_id_is_replaced(make_client: Any) -> None:
    response = make_client().get("/health", headers={"X-Request-ID": "bad id with spaces"})
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-request-id"])


def test_security_headers_present(make_client: Any) -> None:
    headers = make_client().get("/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["cache-control"] == "no-store"
    assert "strict-transport-security" not in headers


def test_hsts_only_in_production(make_client: Any) -> None:
    client = make_client(environment="production", allowed_origins=("https://app.example.com",))
    assert "max-age=" in client.get("/health").headers["strict-transport-security"]


def test_oversized_body_is_rejected_with_413_envelope(make_client: Any) -> None:
    client = make_client(max_request_bytes=1024)
    response = client.post("/health", content=b"x" * 2048)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_chunked_body_without_length_is_rejected_with_411(make_client: Any) -> None:
    response = make_client().post("/health", content=(chunk for chunk in [b"abc"]))
    assert response.status_code == 411


def test_access_log_records_status_without_query_string(
    make_client: Any, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="ddq_api.access"):
        make_client().get("/health?token=secret")
    contexts = [getattr(r, "ctx", {}) for r in caplog.records if r.name == "ddq_api.access"]
    assert contexts
    assert contexts[-1]["status"] == 200
    assert contexts[-1]["path"] == "/health"
    assert "secret" not in str(contexts)
```

`apps/api/tests/test_cors.py`:
```python
from typing import Any

ORIGIN = "http://localhost:5173"


def test_allowed_origin_gets_cors_headers(make_client: Any) -> None:
    response = make_client().get("/health", headers={"Origin": ORIGIN})
    assert response.headers["access-control-allow-origin"] == ORIGIN
    assert "x-request-id" in response.headers["access-control-expose-headers"].lower()


def test_unknown_origin_gets_no_cors_headers(make_client: Any) -> None:
    response = make_client().get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_preflight_for_allowed_origin(make_client: Any) -> None:
    response = make_client().options(
        "/health",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN


def test_preflight_for_unknown_origin_is_rejected(make_client: Any) -> None:
    response = make_client().options(
        "/health",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 400


def test_credentials_are_never_allowed(make_client: Any) -> None:
    response = make_client().get("/health", headers={"Origin": ORIGIN})
    assert "access-control-allow-credentials" not in response.headers
```

`apps/api/tests/test_rate_limit.py`:
```python
from typing import Any


def test_requests_over_the_limit_get_429_envelope_with_retry_after(make_client: Any) -> None:
    client = make_client(rate_limit_default="2/minute")
    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 200
    limited = client.get("/health")
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    assert int(limited.headers["retry-after"]) >= 1


def test_429_still_carries_cors_headers(make_client: Any) -> None:
    client = make_client(rate_limit_default="1/minute")
    origin = {"Origin": "http://localhost:5173"}
    client.get("/health", headers=origin)
    limited = client.get("/health", headers=origin)
    assert limited.status_code == 429
    assert limited.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_buckets_are_per_client_behind_a_trusted_proxy(make_client: Any) -> None:
    client = make_client(rate_limit_default="1/minute", trusted_proxy_hops=1)
    a = {"X-Forwarded-For": "203.0.113.1"}
    b = {"X-Forwarded-For": "203.0.113.2"}
    assert client.get("/health", headers=a).status_code == 200
    assert client.get("/health", headers=a).status_code == 429
    assert client.get("/health", headers=b).status_code == 200


def test_spoofed_leftmost_forwarded_entries_do_not_evade_the_limit(make_client: Any) -> None:
    """Review focus 5."""
    client = make_client(rate_limit_default="1/minute", trusted_proxy_hops=1)
    assert client.get("/health", headers={"X-Forwarded-For": "1.1.1.1, 203.0.113.9"}).status_code == 200
    spoofed = client.get("/health", headers={"X-Forwarded-For": "2.2.2.2, 203.0.113.9"})
    assert spoofed.status_code == 429


def test_forwarded_header_is_ignored_when_no_proxy_is_trusted(make_client: Any) -> None:
    client = make_client(rate_limit_default="1/minute", trusted_proxy_hops=0)
    assert client.get("/health", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert client.get("/health", headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 429
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest apps/api/tests/test_middleware.py apps/api/tests/test_cors.py apps/api/tests/test_rate_limit.py --no-cov -q`
Expected: FAIL (`ImportError: cannot import name 'client_ip'`).

- [ ] **Step 3: Implement** `apps/api/src/ddq_api/core/middleware.py`

```python
"""HTTP middleware: request context, security headers, body limit and rate limiting."""

import logging
import math
import re
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from limits import parse as parse_rate_limit
from limits.storage import MemoryStorage
from limits.strategies import FixedWindowRateLimiter
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from ddq_api.core.config import Settings
from ddq_api.core.envelope import fail
from ddq_api.core.logging import request_id_var

_access_log = logging.getLogger("ddq_api.access")
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
_BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})


def client_ip(request: Request, hops: int) -> str:
    """Resolve the client address.

    Only the entry appended by our own trusted proxy is believed: with ``hops`` trusted
    proxies, that is the ``hops``-th entry from the RIGHT of X-Forwarded-For. Anything to
    its left was supplied by the client and can be forged.
    """
    if hops > 0:
        entries = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
        if len(entries) >= hops:
            return entries[-hops]
    return request.client.host if request.client else "unknown"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _REQUEST_ID_RE.fullmatch(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            _access_log.info(
                "request",
                extra={
                    "ctx": {
                        "method": request.method,
                        "path": request.url.path,  # never the query string (may hold tokens)
                        "status": response.status_code,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    }
                },
            )
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_var.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, hsts: bool) -> None:
        super().__init__(app)
        self._hsts = hsts

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        if self._hsts:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window limiter, in memory: per API instance, which is fine on a single free instance."""

    def __init__(self, app: ASGIApp, rate: str, hops: int) -> None:
        super().__init__(app)
        self._item = parse_rate_limit(rate)
        self._limiter = FixedWindowRateLimiter(MemoryStorage())
        self._hops = hops

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        key = client_ip(request, self._hops)
        if self._limiter.hit(self._item, key):
            return await call_next(request)
        stats = self._limiter.get_window_stats(self._item, key)
        retry_after = max(1, math.ceil(stats.reset_time - time.time()))
        envelope = fail("rate_limited", "Too many requests; please slow down")
        return JSONResponse(
            status_code=429,
            content=envelope.model_dump(mode="json"),
            headers={"Retry-After": str(retry_after)},
        )


class BodySizeLimitMiddleware:
    """Rejects oversized bodies by Content-Length, and unsized (chunked) bodies outright.

    Phase 3 (CSV upload) replaces this with streaming byte counting.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        length = headers.get("content-length")
        rejection: JSONResponse | None = None
        if length is not None:
            if not length.isdigit() or int(length) > self._max_bytes:
                rejection = JSONResponse(
                    413, fail("payload_too_large", "Request body is too large").model_dump(mode="json")
                )
        elif scope["method"] in _BODY_METHODS and "chunked" in headers.get(
            "transfer-encoding", ""
        ).lower():
            rejection = JSONResponse(
                411, fail("length_required", "Content-Length is required").model_dump(mode="json")
            )
        if rejection is not None:
            await rejection(scope, receive, send)
            return
        await self.app(scope, receive, send)


def install_middleware(app: FastAPI, settings: Settings) -> None:
    """Add innermost first: Starlette makes the LAST added the outermost layer."""
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_bytes)
    app.add_middleware(
        RateLimitMiddleware,
        rate=settings.rate_limit_default,
        hops=settings.trusted_proxy_hops,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=False,  # bearer tokens travel in the Authorization header, not cookies
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
        max_age=600,
    )
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.environment == "production")
    app.add_middleware(RequestContextMiddleware)
```

- [ ] **Step 4: Wire it in.** In `main.py` add `from ddq_api.core.middleware import install_middleware` and call `install_middleware(app, settings)` immediately after `register_exception_handlers(app)`.

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest apps/api/tests --no-cov -q`
Expected: all PASS. If the chunked-body test does not return 411 because the test client sets a `Content-Length`, send the chunked body with an explicit header: `content=(…), headers={"Transfer-Encoding": "chunked"}`. If the 500 handler test loses CORS headers, that is the known Starlette behaviour (ServerErrorMiddleware is outermost); it is acceptable and documented in the ADR set (Task 13).

- [ ] **Step 6: Lint, type-check, commit**

```powershell
uv run ruff check . ; uv run ruff format . ; uv run mypy packages/analytics/src apps/api/src
git add -A
git commit -m "feat: add request context, security headers, CORS, body limit and rate limiting"
```

---

### Task 6: Alembic baseline, database integration tests and the RLS guard

**Files:**
- Create: `apps/api/alembic.ini`, `apps/api/migrations/env.py`, `apps/api/migrations/script.py.mako`, `apps/api/migrations/versions/0001_baseline.py`
- Create: `apps/api/tests/integration/conftest.py`, `apps/api/tests/integration/test_database.py`
- Modify: root `pyproject.toml` (mypy exclude for migrations)

**Interfaces:**
- Consumes: `build_engine`, `SqlAlchemyHealth`, `normalize_database_url` (Tasks 3–4).
- Produces: a working `alembic upgrade head` (reads `DDQ_DATABASE_MIGRATION_URL`, falling back to `DDQ_DATABASE_URL`); baseline revision id `"0001"` that enables RLS on `alembic_version`; the **RLS guard test** every later migration must satisfy.

- [ ] **Step 1: Write the failing integration tests**

`apps/api/tests/integration/conftest.py`:
```python
import os

import pytest


@pytest.fixture
def database_url() -> str:
    url = os.environ.get("DDQ_TEST_DATABASE_URL")
    if not url:
        pytest.skip("DDQ_TEST_DATABASE_URL is not set")
    if "supabase" in url.lower():
        pytest.fail("refusing to run destructive migration tests against a Supabase database")
    return url
```

`apps/api/tests/integration/test_database.py`:
```python
import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

from ddq_api.core.config import normalize_database_url
from ddq_api.core.db import SqlAlchemyHealth, build_engine

pytestmark = pytest.mark.integration

API_DIR = Path(__file__).resolve().parents[2]

# Every table in `public` must have row-level security on: the Supabase REST API exposes
# `public`, and our authorization lives in the FastAPI service layer, not in Postgres roles.
UNPROTECTED_TABLES_SQL = """
SELECT c.relname
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p') AND NOT c.relrowsecurity
ORDER BY c.relname
"""


def _alembic(url: str, *args: str) -> None:
    subprocess.run(  # noqa: S603  (fixed argv, no shell)
        [sys.executable, "-m", "alembic", "-c", str(API_DIR / "alembic.ini"), *args],
        cwd=API_DIR,
        env={**os.environ, "DDQ_DATABASE_MIGRATION_URL": url},
        capture_output=True,
        text=True,
        check=True,
    )


async def test_ping_succeeds_against_real_postgres(database_url: str) -> None:
    engine = build_engine(normalize_database_url(database_url))
    try:
        await SqlAlchemyHealth(engine).ping()
    finally:
        await engine.dispose()


async def test_baseline_migration_applies_and_every_table_has_rls(database_url: str) -> None:
    await asyncio.to_thread(_alembic, database_url, "upgrade", "head")
    engine = build_engine(normalize_database_url(database_url))
    try:
        async with engine.connect() as connection:
            version = (await connection.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()
            unprotected = (await connection.execute(text(UNPROTECTED_TABLES_SQL))).scalars().all()
    finally:
        await engine.dispose()
        await asyncio.to_thread(_alembic, database_url, "downgrade", "base")
    assert version == "0001"
    assert unprotected == [], f"tables without row-level security: {unprotected}"
```

- [ ] **Step 2: Run to verify it fails or skips.** Locally (no throwaway database) the tests SKIP; that is expected. The authoritative RED/GREEN happens in CI (Task 11), which provides a Postgres service.

Run: `uv run pytest apps/api/tests/integration --no-cov -q -rs`
Expected: `2 skipped` ("DDQ_TEST_DATABASE_URL is not set").

- [ ] **Step 3: Write the Alembic files**

`apps/api/alembic.ini`:
```ini
[alembic]
script_location = %(here)s/migrations
file_template = %%(rev)s_%%(slug)s
```

`apps/api/migrations/env.py`:
```python
"""Alembic environment: async engine, URL from the environment (never from alembic.ini)."""

import asyncio
import os

from alembic import context
from sqlalchemy.engine import Connection

from ddq_api.core.config import normalize_database_url
from ddq_api.core.db import build_engine

target_metadata = None  # SQL-first migrations; no ORM metadata autogenerate


def _database_url() -> str:
    raw = os.environ.get("DDQ_DATABASE_MIGRATION_URL") or os.environ.get("DDQ_DATABASE_URL")
    if not raw:
        raise RuntimeError(
            "Set DDQ_DATABASE_MIGRATION_URL (preferred, session pooler) or DDQ_DATABASE_URL."
        )
    return normalize_database_url(raw)


def _run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_online() -> None:
    engine = build_engine(_database_url())
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_run_migrations)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline (--sql) migrations are not supported; run against a database.")

asyncio.run(_run_online())
```

`apps/api/migrations/script.py.mako`:
```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

Every new table MUST end with:
    op.execute("ALTER TABLE <name> ENABLE ROW LEVEL SECURITY")
The RLS guard test in tests/integration/test_database.py fails the build otherwise.
Migrations must be backward compatible with the previous app version (expand, then contract).
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

`apps/api/migrations/versions/0001_baseline.py`:
```python
"""baseline: no data tables yet; proves the migration pipeline and locks down alembic_version

Revision ID: 0001
Revises:
Create Date: 2026-09-24
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # alembic_version lives in `public`, which Supabase exposes over REST; deny-all it.
    op.execute("ALTER TABLE alembic_version ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("ALTER TABLE alembic_version DISABLE ROW LEVEL SECURITY")
```

- [ ] **Step 4: Exclude migrations from mypy.** In root `pyproject.toml` under `[tool.mypy]` add `exclude = ["apps/api/migrations"]`.

- [ ] **Step 5: Verify locally if a throwaway Postgres is available** (otherwise rely on CI): set `$env:DDQ_TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/ddq_test"` and run `uv run pytest apps/api/tests/integration --no-cov -q`.
Expected: 2 PASS. Without a local database, run `uv run alembic -c apps/api/alembic.ini heads` (with `DDQ_DATABASE_URL` unset it must not be needed for `heads`… if env.py raises for `heads`, that is acceptable; the migration graph is validated in CI).

- [ ] **Step 6: Lint, type-check, run full suite, commit**

```powershell
uv run ruff check . ; uv run ruff format . ; uv run mypy packages/analytics/src apps/api/src
uv run pytest -q
git add -A
git commit -m "feat: add Alembic baseline, database integration tests and RLS guard"
```
Expected: full suite passes with coverage ≥ 80% (integration tests skipped locally).

---

### Task 7: OpenAPI contract export

**Files:**
- Create: `apps/api/src/ddq_api/export_openapi.py`, `apps/api/openapi.json` (generated), `apps/api/tests/test_openapi_contract.py`

**Interfaces:**
- Consumes: `create_app`, `Settings` (Tasks 3–4).
- Produces: `render_openapi() -> str` (deterministic JSON, sorted keys, trailing newline); `main(argv: list[str]) -> int`; CLI `python -m ddq_api.export_openapi [output_path]`; committed `apps/api/openapi.json` consumed by Task 9 (`gen:api`) and CI (Task 11).

- [ ] **Step 1: Write the failing test** `apps/api/tests/test_openapi_contract.py`

```python
import json
from pathlib import Path

from ddq_api.export_openapi import OPENAPI_PATH, main, render_openapi


def test_schema_documents_health_and_ready() -> None:
    schema = json.loads(render_openapi())
    assert {"/health", "/ready"} <= set(schema["paths"])
    assert "503" in schema["paths"]["/ready"]["get"]["responses"]


def test_rendering_is_deterministic() -> None:
    assert render_openapi() == render_openapi()


def test_committed_contract_is_up_to_date() -> None:
    assert OPENAPI_PATH.read_text(encoding="utf-8") == render_openapi(), (
        "apps/api/openapi.json is stale: run `uv run python -m ddq_api.export_openapi` "
        "and `pnpm --dir apps/web gen:api`, then commit both."
    )


def test_main_writes_the_requested_file(tmp_path: Path) -> None:
    target = tmp_path / "out.json"
    assert main([str(target)]) == 0
    assert json.loads(target.read_text(encoding="utf-8"))["openapi"].startswith("3.")
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest apps/api/tests/test_openapi_contract.py --no-cov -q`
Expected: FAIL (`ModuleNotFoundError: ddq_api.export_openapi`).

- [ ] **Step 3: Implement** `apps/api/src/ddq_api/export_openapi.py`

```python
"""Write the OpenAPI schema to disk. CI regenerates it to detect contract drift."""

import json
import sys
from pathlib import Path

from ddq_api.core.config import Settings
from ddq_api.main import create_app

OPENAPI_PATH = Path(__file__).resolve().parents[2] / "openapi.json"  # apps/api/openapi.json


class _NoDatabase:
    async def ping(self) -> None:
        return None


def render_openapi() -> str:
    settings = Settings(  # type: ignore[call-arg]
        _env_file=None,
        environment="test",
        database_url="postgresql://x:x@localhost:5432/x",
        allowed_origins="http://localhost:5173",
    )
    schema = create_app(settings, db_health=_NoDatabase()).openapi()
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def main(argv: list[str]) -> int:
    target = Path(argv[0]) if argv else OPENAPI_PATH
    target.write_text(render_openapi(), encoding="utf-8", newline="\n")
    sys.stdout.write(f"wrote {target}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Generate the committed contract, then run tests**

```powershell
uv run python -m ddq_api.export_openapi
uv run pytest apps/api/tests/test_openapi_contract.py --no-cov -q
```
Expected: `apps/api/openapi.json` written; all 4 tests PASS.

- [ ] **Step 5: Lint, type-check, commit**

```powershell
uv run ruff check . ; uv run ruff format . ; uv run mypy packages/analytics/src apps/api/src
git add -A
git commit -m "feat: export deterministic OpenAPI contract with drift test"
```

---

### Task 8: Web scaffold, design tokens and theme

**Files:**
- Create: `apps/web/` via Vite template; then create/modify `vite.config.ts`, `index.html`, `eslint.config.js`, `.prettierrc`, `public/theme-init.js`, `src/styles/{index.css,tokens.css}`, `src/theme/{theme.ts,ThemeContext.ts,ThemeProvider.tsx,ThemeToggle.tsx}`, `src/App.tsx`, `src/main.tsx`, `src/test/{setup.ts,utils.tsx}`
- Test: `src/theme/theme.test.ts`, `src/theme/ThemeToggle.test.tsx`, `src/App.test.tsx`

**Interfaces:**
- Consumes: none.
- Produces:
  - `theme.ts`: `ThemePreference = 'light'|'dark'|'system'`, `ResolvedTheme`, `THEME_STORAGE_KEY = 'ddq-theme'`, `isThemePreference`, `resolveTheme(pref, systemPrefersDark)`, `nextPreference(pref)`, `readStoredPreference(storage)`, `storePreference(storage, pref)`.
  - `ThemeContext.ts`: `useTheme(): { preference: ThemePreference; resolved: ResolvedTheme; cycle(): void }`.
  - `ThemeProvider`, `ThemeToggle` components; `App` (`{ client?: ApiClient }` prop is added in Task 9).
  - Test helpers: `renderWithProviders` (Task 9 extends it with a query client).
  - CSS tokens (`--bg --surface --surface-2 --text --muted --border --accent --accent-contrast --good --warn --bad`) mapped to Tailwind colours (`bg-bg`, `text-muted`, …).

- [ ] **Step 1: Scaffold**

```powershell
cd C:\Users\Emman\Documents\CLAUDE\ddq-portfolio-dashboard
pnpm create vite@latest apps/web --template react-ts
```
If prompted (install/start now, experimental features), decline. Then:

```powershell
pnpm --dir apps/web install
pnpm --dir apps/web add @tanstack/react-query openapi-fetch
pnpm --dir apps/web add -D tailwindcss @tailwindcss/vite vitest jsdom @vitest/coverage-v8 @testing-library/react @testing-library/jest-dom @testing-library/user-event openapi-typescript prettier
pnpm --dir apps/web pkg set "packageManager=pnpm@$(pnpm --version)"
```
Delete the template demo files: `src/App.css`, `src/assets/`, `public/vite.svg`, and the demo content of `src/index.css` (it is replaced below by `src/styles/index.css`; delete `src/index.css`).

- [ ] **Step 2: Configure scripts, Vite/Vitest, Prettier, ESLint**

In `apps/web/package.json` set `"name": "ddq-web"` and scripts:
```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "preview": "vite preview",
  "lint": "eslint .",
  "format": "prettier --write .",
  "format:check": "prettier --check .",
  "test": "vitest run",
  "test:cov": "vitest run --coverage",
  "gen:api": "openapi-typescript ../api/openapi.json -o src/api/schema.d.ts"
}
```
`apps/web/vite.config.ts`:
```ts
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/**'],
      exclude: ['src/main.tsx', 'src/api/schema.d.ts', 'src/test/**', 'src/**/*.test.*'],
      thresholds: { lines: 80, functions: 80, statements: 80, branches: 70 },
    },
  },
})
```
`apps/web/.prettierrc`:
```json
{ "semi": false, "singleQuote": true, "printWidth": 100 }
```
Add `apps/web/.prettierignore`: `dist`, `pnpm-lock.yaml`, `src/api/schema.d.ts`.

In `apps/web/eslint.config.js` (created by the template) make two edits: add `'src/api/schema.d.ts'` and `'public'` to the global ignores next to `dist`, and add this object to the exported config array:
```js
{ rules: { 'no-console': 'error' } },
```
Ensure `apps/web/tsconfig.app.json` keeps `"strict": true` and add `"noUncheckedIndexedAccess": true`.

- [ ] **Step 3: Write the failing tests**

`src/test/setup.ts`:
```ts
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  }),
})

afterEach(() => {
  cleanup()
  localStorage.clear()
  delete document.documentElement.dataset.theme
})
```

`src/theme/theme.test.ts`:
```ts
import { describe, expect, it } from 'vitest'
import {
  THEME_STORAGE_KEY,
  isThemePreference,
  nextPreference,
  readStoredPreference,
  resolveTheme,
  storePreference,
} from './theme'

describe('theme', () => {
  it('resolves explicit preferences and follows the system for "system"', () => {
    expect(resolveTheme('light', true)).toBe('light')
    expect(resolveTheme('dark', false)).toBe('dark')
    expect(resolveTheme('system', true)).toBe('dark')
    expect(resolveTheme('system', false)).toBe('light')
  })

  it('cycles light -> dark -> system -> light', () => {
    expect(nextPreference('light')).toBe('dark')
    expect(nextPreference('dark')).toBe('system')
    expect(nextPreference('system')).toBe('light')
  })

  it('validates preferences', () => {
    expect(isThemePreference('dark')).toBe(true)
    expect(isThemePreference('purple')).toBe(false)
    expect(isThemePreference(null)).toBe(false)
  })

  it('reads a valid stored preference and defaults otherwise', () => {
    expect(readStoredPreference({ getItem: () => 'dark' })).toBe('dark')
    expect(readStoredPreference({ getItem: () => 'garbage' })).toBe('system')
    expect(readStoredPreference({ getItem: () => null })).toBe('system')
    expect(readStoredPreference(undefined)).toBe('system')
  })

  it('does not crash when storage throws (private mode / blocked storage)', () => {
    const throwing = {
      getItem: () => {
        throw new Error('denied')
      },
      setItem: () => {
        throw new Error('denied')
      },
    }
    expect(readStoredPreference(throwing)).toBe('system')
    expect(() => storePreference(throwing, 'dark')).not.toThrow()
  })

  it('persists under the documented key', () => {
    const calls: Array<[string, string]> = []
    storePreference({ setItem: (k, v) => calls.push([k, v]) }, 'dark')
    expect(calls).toEqual([[THEME_STORAGE_KEY, 'dark']])
  })
})
```

`src/test/utils.tsx`:
```tsx
import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { ThemeProvider } from '../theme/ThemeProvider'

export function renderWithProviders(ui: ReactElement) {
  return render(<ThemeProvider>{ui}</ThemeProvider>)
}
```

`src/theme/ThemeToggle.test.tsx`:
```tsx
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderWithProviders } from '../test/utils'
import { ThemeToggle } from './ThemeToggle'

describe('ThemeToggle', () => {
  it('applies the stored preference and cycles on click, persisting each choice', async () => {
    localStorage.setItem('ddq-theme', 'light')
    renderWithProviders(<ThemeToggle />)
    const button = screen.getByRole('button', { name: /theme/i })

    expect(document.documentElement.dataset.theme).toBe('light')
    await userEvent.click(button)
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem('ddq-theme')).toBe('dark')
    expect(button).toHaveAccessibleName(/dark/i)

    await userEvent.click(button) // -> system (matchMedia stub says light)
    expect(localStorage.getItem('ddq-theme')).toBe('system')
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('still renders and works when localStorage is unavailable', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('denied')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('denied')
    })
    renderWithProviders(<ThemeToggle />)
    await userEvent.click(screen.getByRole('button', { name: /theme/i }))
    expect(document.documentElement.dataset.theme).toBeDefined()
    vi.restoreAllMocks()
  })
})
```

`src/App.test.tsx`:
```tsx
import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'
import { renderWithProviders } from './test/utils'

describe('App', () => {
  it('shows the product name and the theme toggle', () => {
    renderWithProviders(<App />)
    expect(screen.getByRole('heading', { name: 'DDQ Portfolio Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /theme/i })).toBeInTheDocument()
  })
})
```
(`ThemeProvider` is rendered by both `renderWithProviders` and, in production, `main.tsx`; `App` itself does not render a second provider, so the shell stays testable.)

- [ ] **Step 4: Run to verify failure**

Run: `pnpm --dir apps/web test`
Expected: FAIL (modules not found: `./theme`, `../theme/ThemeProvider`, `./App`).

- [ ] **Step 5: Implement the theme**

`src/theme/theme.ts`:
```ts
export type ThemePreference = 'light' | 'dark' | 'system'
export type ResolvedTheme = 'light' | 'dark'

export const THEME_STORAGE_KEY = 'ddq-theme'
const PREFERENCES: readonly ThemePreference[] = ['light', 'dark', 'system']

export function isThemePreference(value: unknown): value is ThemePreference {
  return typeof value === 'string' && (PREFERENCES as readonly string[]).includes(value)
}

export function resolveTheme(preference: ThemePreference, systemPrefersDark: boolean): ResolvedTheme {
  if (preference === 'system') return systemPrefersDark ? 'dark' : 'light'
  return preference
}

export function nextPreference(current: ThemePreference): ThemePreference {
  const index = PREFERENCES.indexOf(current)
  return PREFERENCES[(index + 1) % PREFERENCES.length] ?? 'system'
}

export function readStoredPreference(
  storage: Pick<Storage, 'getItem'> | undefined,
): ThemePreference {
  try {
    const raw = storage?.getItem(THEME_STORAGE_KEY)
    return isThemePreference(raw) ? raw : 'system'
  } catch {
    return 'system' // storage blocked (private mode); fall back without failing
  }
}

export function storePreference(
  storage: Pick<Storage, 'setItem'> | undefined,
  preference: ThemePreference,
): void {
  try {
    storage?.setItem(THEME_STORAGE_KEY, preference)
  } catch {
    // Storage unavailable: the choice applies for this session but will not persist.
  }
}
```

`src/theme/ThemeContext.ts`:
```ts
import { createContext, useContext } from 'react'
import type { ResolvedTheme, ThemePreference } from './theme'

export interface ThemeState {
  readonly preference: ThemePreference
  readonly resolved: ResolvedTheme
  readonly cycle: () => void
}

export const ThemeContext = createContext<ThemeState | null>(null)

export function useTheme(): ThemeState {
  const value = useContext(ThemeContext)
  if (value === null) throw new Error('useTheme must be used inside <ThemeProvider>')
  return value
}
```

`src/theme/ThemeProvider.tsx`:
```tsx
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { ThemeContext } from './ThemeContext'
import {
  nextPreference,
  readStoredPreference,
  resolveTheme,
  storePreference,
  type ThemePreference,
} from './theme'

const DARK_QUERY = '(prefers-color-scheme: dark)'

function safeStorage(): Storage | undefined {
  try {
    return window.localStorage
  } catch {
    return undefined
  }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreference] = useState<ThemePreference>(() =>
    readStoredPreference(safeStorage()),
  )
  const [systemDark, setSystemDark] = useState(() => window.matchMedia(DARK_QUERY).matches)

  useEffect(() => {
    const query = window.matchMedia(DARK_QUERY)
    const onChange = (event: MediaQueryListEvent) => setSystemDark(event.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  const resolved = resolveTheme(preference, systemDark)

  useEffect(() => {
    document.documentElement.dataset.theme = resolved
  }, [resolved])

  const cycle = useCallback(() => {
    const next = nextPreference(preference)
    storePreference(safeStorage(), next)
    setPreference(next)
  }, [preference])

  const value = useMemo(() => ({ preference, resolved, cycle }), [preference, resolved, cycle])
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}
```

`src/theme/ThemeToggle.tsx`:
```tsx
import { useTheme } from './ThemeContext'

const LABELS = { light: 'Light', dark: 'Dark', system: 'System' } as const

export function ThemeToggle() {
  const { preference, cycle } = useTheme()
  return (
    <button
      type="button"
      onClick={cycle}
      aria-label={`Theme: ${LABELS[preference]}. Activate to change.`}
      className="rounded-md border border-border bg-surface-2 px-3 py-1.5 text-sm text-text hover:border-accent focus-visible:outline-2 focus-visible:outline-accent"
    >
      Theme: {LABELS[preference]}
    </button>
  )
}
```

- [ ] **Step 6: Implement the shell, tokens and entry points**

`src/styles/tokens.css`:
```css
:root,
[data-theme='light'] {
  color-scheme: light;
  --bg: #f7f8fa;
  --surface: #ffffff;
  --surface-2: #eef1f5;
  --text: #14181f;
  --muted: #5b6573;
  --border: #d9dee6;
  --accent: #1f5fd6;
  --accent-contrast: #ffffff;
  --good: #1a7f4b;
  --warn: #a15c00;
  --bad: #c0303a;
}

[data-theme='dark'] {
  color-scheme: dark;
  --bg: #0f1319;
  --surface: #171c24;
  --surface-2: #1f2630;
  --text: #e8ecf2;
  --muted: #9aa5b5;
  --border: #2d3644;
  --accent: #6ea2ff;
  --accent-contrast: #0b1220;
  --good: #4cc38a;
  --warn: #e0a13a;
  --bad: #ff7a85;
}
```

`src/styles/index.css`:
```css
@import 'tailwindcss';
@import './tokens.css';

@custom-variant dark (&:where([data-theme='dark'], [data-theme='dark'] *));

@theme inline {
  --color-bg: var(--bg);
  --color-surface: var(--surface);
  --color-surface-2: var(--surface-2);
  --color-text: var(--text);
  --color-muted: var(--muted);
  --color-border: var(--border);
  --color-accent: var(--accent);
  --color-accent-contrast: var(--accent-contrast);
  --color-good: var(--good);
  --color-warn: var(--warn);
  --color-bad: var(--bad);
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
}
```

`public/theme-init.js` (an external file so the production CSP needs no inline-script exception; it prevents a flash of the wrong theme):
```js
;(function () {
  var theme = 'light'
  try {
    var stored = window.localStorage.getItem('ddq-theme')
    var dark = window.matchMedia('(prefers-color-scheme: dark)').matches
    if (stored === 'dark' || (stored !== 'light' && dark)) theme = 'dark'
  } catch (error) {
    // storage or matchMedia unavailable: keep the light default
  }
  document.documentElement.dataset.theme = theme
})()
```

`index.html` (replace the template's; keep the Vite module script):
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="DDQ Portfolio Dashboard: portfolio risk analytics" />
    <title>DDQ Portfolio Dashboard</title>
    <script src="/theme-init.js"></script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`src/App.tsx`:
```tsx
import { ThemeToggle } from './theme/ThemeToggle'

export default function App() {
  return (
    <div className="min-h-screen bg-bg text-text">
      <header className="flex items-center justify-between border-b border-border bg-surface px-6 py-4">
        <h1 className="text-lg font-semibold">DDQ Portfolio Dashboard</h1>
        <ThemeToggle />
      </header>
      <main className="mx-auto max-w-3xl px-6 py-10">
        <p className="text-muted">Portfolio risk analytics: Data Driven Quant.</p>
      </main>
    </div>
  )
}
```

`src/main.tsx`:
```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles/index.css'
import { ThemeProvider } from './theme/ThemeProvider'

const root = document.getElementById('root')
if (root === null) throw new Error('Missing #root element')

createRoot(root).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>,
)
```

- [ ] **Step 7: Run to verify pass, then lint/format/typecheck/build**

```powershell
pnpm --dir apps/web test
pnpm --dir apps/web format
pnpm --dir apps/web lint
pnpm --dir apps/web build
```
Expected: all tests PASS; lint clean; build succeeds. (Task 9 adds `config.ts`, which `build` does not need yet.)

- [ ] **Step 8: Commit**

```powershell
git add -A
git commit -m "feat: scaffold web app with design tokens and light/dark/system theme"
```

---

### Task 9: API client and status page with cold-start UX

**Files:**
- Create: `apps/web/src/config.ts`, `src/config.test.ts`, `src/api/client.ts`, `src/api/schema.d.ts` (generated), `src/features/status/{deriveStatus.ts,deriveStatus.test.ts,useApiStatus.ts,StatusPage.tsx,StatusPage.test.tsx}`, `src/test/fakeFetch.ts`
- Modify: `src/App.tsx`, `src/main.tsx`, `src/test/utils.tsx`, `src/App.test.tsx`

**Interfaces:**
- Consumes: `apps/api/openapi.json` (Task 7), theme components (Task 8).
- Produces:
  - `resolveApiUrl(raw: string | undefined, isProd: boolean): string`, `API_URL`.
  - `createApiClient(baseUrl, fetchImpl?): ApiClient`, `apiClient`, `type ApiClient`.
  - `deriveStatus(inputs: StatusInputs): ApiStatus` with `ApiStatus = 'checking'|'waking'|'online'|'degraded'|'offline'`, `WAKE_THRESHOLD_MS = 3000`.
  - `useApiStatus(client): { status, snapshot, elapsedMs, refetch }`; `StatusPage({ client })`; `fakeFetch(routes)` and `renderWithProviders` now wrapping a `QueryClientProvider` (`retry: false`).

- [ ] **Step 1: Generate API types**

```powershell
pnpm --dir apps/web gen:api
```
Expected: `apps/web/src/api/schema.d.ts` created and containing `"/health"` and `"/ready"`.

- [ ] **Step 2: Write the failing tests**

`src/config.test.ts`:
```ts
import { describe, expect, it } from 'vitest'
import { resolveApiUrl } from './config'

describe('resolveApiUrl', () => {
  it('defaults to localhost in development', () => {
    expect(resolveApiUrl(undefined, false)).toBe('http://localhost:8000')
  })

  it('requires the variable in production builds', () => {
    expect(() => resolveApiUrl(undefined, true)).toThrow(/VITE_API_URL/)
  })

  it('requires https in production', () => {
    expect(() => resolveApiUrl('http://api.example.com', true)).toThrow(/https/)
    expect(resolveApiUrl('https://api.example.com', true)).toBe('https://api.example.com')
  })

  it('reduces the value to a clean origin', () => {
    expect(resolveApiUrl('https://api.example.com/some/path/', true)).toBe('https://api.example.com')
  })

  it('rejects values that are not URLs', () => {
    expect(() => resolveApiUrl('not a url', false)).toThrow()
  })
})
```

`src/test/fakeFetch.ts`:
```ts
export interface FakeRoute {
  readonly status: number
  readonly body: unknown
  readonly contentType?: string
}

/** A fetch stand-in that answers by URL path; `null` means "never resolves" (cold start). */
export function fakeFetch(routes: Record<string, FakeRoute | null>) {
  return async (input: Request): Promise<Response> => {
    const route = routes[new URL(input.url).pathname]
    if (route === undefined) return new Response('not found', { status: 404 })
    if (route === null) return new Promise<Response>(() => undefined)
    const contentType = route.contentType ?? 'application/json'
    const payload = typeof route.body === 'string' ? route.body : JSON.stringify(route.body)
    return new Response(payload, { status: route.status, headers: { 'content-type': contentType } })
  }
}
```

`src/features/status/deriveStatus.test.ts`:
```ts
import { describe, expect, it } from 'vitest'
import { WAKE_THRESHOLD_MS, deriveStatus } from './deriveStatus'

const base = { isLoading: false, elapsedMs: 0, hasSnapshot: true, failed: false, dbOk: true }

describe('deriveStatus', () => {
  it.each([
    [{ isLoading: true, elapsedMs: 0 }, 'checking'],
    [{ isLoading: true, elapsedMs: WAKE_THRESHOLD_MS - 1 }, 'checking'],
    [{ isLoading: true, elapsedMs: WAKE_THRESHOLD_MS }, 'waking'],
    [{ failed: true }, 'offline'],
    [{ hasSnapshot: false }, 'offline'],
    [{ dbOk: false }, 'degraded'],
    [{}, 'online'],
  ] as const)('%j -> %s', (overrides, expected) => {
    expect(deriveStatus({ ...base, ...overrides })).toBe(expected)
  })
})
```

`src/features/status/StatusPage.test.tsx`:
```tsx
import { act, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApiClient } from '../../api/client'
import { fakeFetch } from '../../test/fakeFetch'
import { renderWithProviders } from '../../test/utils'
import { StatusPage } from './StatusPage'

const HEALTH = {
  status: 200,
  body: { data: { status: 'ok', version: '0.1.0', environment: 'production' }, error: null, meta: {} },
}
const READY_OK = {
  status: 200,
  body: { data: { status: 'ready', checks: { database: { ok: true } } }, error: null, meta: {} },
}
const READY_DOWN = {
  status: 503,
  body: {
    data: { status: 'degraded', checks: { database: { ok: false } } },
    error: { code: 'not_ready', message: 'x', details: null },
    meta: {},
  },
}

const clientFor = (routes: Parameters<typeof fakeFetch>[0]) =>
  createApiClient('http://api.test', fakeFetch(routes))

afterEach(() => vi.useRealTimers())

describe('StatusPage', () => {
  it('shows online with version and a connected database', async () => {
    renderWithProviders(<StatusPage client={clientFor({ '/health': HEALTH, '/ready': READY_OK })} />)
    expect(await screen.findByText('Online')).toBeInTheDocument()
    expect(screen.getByText('0.1.0')).toBeInTheDocument()
    expect(screen.getByText('Connected')).toBeInTheDocument()
  })

  it('shows degraded when the database check fails', async () => {
    renderWithProviders(<StatusPage client={clientFor({ '/health': HEALTH, '/ready': READY_DOWN })} />)
    expect(await screen.findByText('Degraded')).toBeInTheDocument()
    expect(screen.getByText('Unavailable')).toBeInTheDocument()
  })

  it('treats a non-JSON 502 page (Render cold start) as offline without crashing', async () => {
    const html = { status: 502, body: '<html>Bad Gateway</html>', contentType: 'text/html' }
    renderWithProviders(<StatusPage client={clientFor({ '/health': html, '/ready': html })} />)
    expect(await screen.findByText('Offline')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })

  it('explains the cold start once the API has been silent for a few seconds', async () => {
    vi.useFakeTimers()
    renderWithProviders(<StatusPage client={clientFor({ '/health': null, '/ready': null })} />)
    expect(screen.getByText('Checking')).toBeInTheDocument()
    await act(async () => {
      vi.advanceTimersByTime(3500)
    })
    expect(screen.getByText(/waking the api/i)).toBeInTheDocument()
  })

  it('retries when the user asks', async () => {
    const html = { status: 502, body: 'bad', contentType: 'text/plain' }
    const routes: Parameters<typeof fakeFetch>[0] = { '/health': html, '/ready': html }
    const client = createApiClient('http://api.test', (req) => fakeFetch(routes)(req))
    renderWithProviders(<StatusPage client={client} />)
    await screen.findByText('Offline')
    routes['/health'] = HEALTH
    routes['/ready'] = READY_OK
    await userEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(await screen.findByText('Online')).toBeInTheDocument()
  })
})
```

Update `src/App.test.tsx` (App now needs a client) to:
```tsx
import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'
import { createApiClient } from './api/client'
import { fakeFetch } from './test/fakeFetch'
import { renderWithProviders } from './test/utils'

describe('App', () => {
  it('shows the product name, the theme toggle and the status page', async () => {
    const client = createApiClient('http://api.test', fakeFetch({ '/health': null, '/ready': null }))
    renderWithProviders(<App client={client} />)
    expect(screen.getByRole('heading', { name: 'DDQ Portfolio Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /theme/i })).toBeInTheDocument()
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})
```

- [ ] **Step 3: Run to verify failure**

Run: `pnpm --dir apps/web test`
Expected: FAIL (missing `./config`, `../../api/client`, `./StatusPage`, …).

- [ ] **Step 4: Implement config, client and status logic**

`src/config.ts`:
```ts
const DEFAULT_DEV_API_URL = 'http://localhost:8000'

export function resolveApiUrl(raw: string | undefined, isProd: boolean): string {
  if (!raw) {
    if (isProd) throw new Error('VITE_API_URL is required for production builds')
    return DEFAULT_DEV_API_URL
  }
  const url = new URL(raw) // throws on an invalid URL
  if (isProd && url.protocol !== 'https:') throw new Error('VITE_API_URL must use https in production')
  return url.origin
}

export const API_URL = resolveApiUrl(import.meta.env.VITE_API_URL, import.meta.env.PROD)
```

`src/api/client.ts`:
```ts
import createClient from 'openapi-fetch'
import { API_URL } from '../config'
import type { paths } from './schema'

type FetchImpl = (input: Request) => Promise<Response>

export function createApiClient(baseUrl: string, fetchImpl: FetchImpl = (input) => fetch(input)) {
  return createClient<paths>({ baseUrl, fetch: fetchImpl })
}

export type ApiClient = ReturnType<typeof createApiClient>

export const apiClient: ApiClient = createApiClient(API_URL)
```

`src/features/status/deriveStatus.ts`:
```ts
export type ApiStatus = 'checking' | 'waking' | 'online' | 'degraded' | 'offline'

/** After this long without a response we assume the free-tier API is waking from sleep. */
export const WAKE_THRESHOLD_MS = 3000

export interface StatusInputs {
  readonly isLoading: boolean
  readonly elapsedMs: number
  readonly hasSnapshot: boolean
  readonly failed: boolean
  readonly dbOk: boolean
}

export function deriveStatus(inputs: StatusInputs): ApiStatus {
  if (inputs.isLoading) return inputs.elapsedMs >= WAKE_THRESHOLD_MS ? 'waking' : 'checking'
  if (inputs.failed || !inputs.hasSnapshot) return 'offline'
  return inputs.dbOk ? 'online' : 'degraded'
}
```

`src/features/status/useApiStatus.ts`:
```ts
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import type { ApiClient } from '../../api/client'
import { deriveStatus, type ApiStatus } from './deriveStatus'

const REQUEST_TIMEOUT_MS = 90_000
const TICK_MS = 500

export interface ApiSnapshot {
  readonly version: string
  readonly environment: string
  readonly dbOk: boolean
}

function readDbOk(body: unknown): boolean {
  if (typeof body !== 'object' || body === null) return false
  const data = (body as { data?: { checks?: { database?: { ok?: unknown } } } }).data
  return data?.checks?.database?.ok === true
}

async function fetchSnapshot(client: ApiClient): Promise<ApiSnapshot> {
  const signal = AbortSignal.timeout(REQUEST_TIMEOUT_MS)
  const [health, ready] = await Promise.all([
    client.GET('/health', { signal }),
    client.GET('/ready', { signal }),
  ])
  const info = health.data?.data
  if (!info) throw new Error('API returned an unexpected response')
  return {
    version: info.version,
    environment: info.environment,
    dbOk: readDbOk(ready.data ?? ready.error),
  }
}

function useElapsedMs(active: boolean): number {
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    if (!active) return
    const start = Date.now()
    const id = setInterval(() => setElapsed(Date.now() - start), TICK_MS)
    return () => {
      clearInterval(id)
      setElapsed(0)
    }
  }, [active])
  return elapsed
}

export function useApiStatus(client: ApiClient) {
  const query = useQuery({
    queryKey: ['api-status'],
    queryFn: () => fetchSnapshot(client),
    refetchOnWindowFocus: false,
  })
  const elapsedMs = useElapsedMs(query.isFetching)
  const status: ApiStatus = deriveStatus({
    isLoading: query.isFetching,
    elapsedMs,
    hasSnapshot: query.data !== undefined,
    failed: query.isError,
    dbOk: query.data?.dbOk ?? false,
  })
  return { status, snapshot: query.data, elapsedMs, refetch: () => void query.refetch() }
}
```

`src/features/status/StatusPage.tsx`:
```tsx
import type { ApiClient } from '../../api/client'
import type { ApiStatus } from './deriveStatus'
import { useApiStatus } from './useApiStatus'

const LABEL: Record<ApiStatus, string> = {
  checking: 'Checking',
  waking: 'Waking',
  online: 'Online',
  degraded: 'Degraded',
  offline: 'Offline',
}
const ICON: Record<ApiStatus, string> = {
  checking: '…',
  waking: '⏳',
  online: '✓',
  degraded: '!',
  offline: '✕',
}
const TONE: Record<ApiStatus, string> = {
  checking: 'text-muted',
  waking: 'text-warn',
  online: 'text-good',
  degraded: 'text-warn',
  offline: 'text-bad',
}

export function StatusPage({ client }: { client: ApiClient }) {
  const { status, snapshot, refetch } = useApiStatus(client)
  return (
    <section aria-labelledby="status-heading" className="space-y-4">
      <h2 id="status-heading" className="text-xl font-semibold">
        System status
      </h2>
      <div
        role="status"
        aria-live="polite"
        className="rounded-lg border border-border bg-surface p-5"
      >
        <p className={`text-lg font-medium ${TONE[status]}`}>
          <span aria-hidden="true">{ICON[status]} </span>
          {status === 'waking' ? 'Waking the API…' : LABEL[status]}
        </p>
        {status === 'waking' && (
          <p className="mt-2 text-sm text-muted">
            The free-tier API sleeps when idle. Waking it takes about 30–60 seconds.
          </p>
        )}
        {(status === 'offline' || status === 'degraded') && (
          <button
            type="button"
            onClick={refetch}
            className="mt-3 rounded-md bg-accent px-3 py-1.5 text-sm text-accent-contrast"
          >
            Retry
          </button>
        )}
      </div>
      {snapshot && (
        <dl className="grid grid-cols-3 gap-3 text-sm">
          <Fact label="API version" value={snapshot.version} />
          <Fact label="Environment" value={snapshot.environment} />
          <Fact label="Database" value={snapshot.dbOk ? 'Connected' : 'Unavailable'} />
        </dl>
      )}
    </section>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <dt className="text-muted">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  )
}
```
Note: when `status === 'waking'` the visible text is "Waking the API…", and "Waking" (the LABEL) is never rendered alone; the test looks for `/waking the api/i`. In the `checking` state the test looks for the exact text `Checking`; the icon lives in an `aria-hidden` span, so `getByText('Checking')` matches the paragraph text after normalisation. If it does not, use `getByText(/^…?\s*Checking$/)`.

- [ ] **Step 5: Wire the app.** Update `src/test/utils.tsx`:
```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { ThemeProvider } from '../theme/ThemeProvider'

export function renderWithProviders(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>{ui}</ThemeProvider>
    </QueryClientProvider>,
  )
}
```
Update `src/App.tsx` to accept `{ client?: ApiClient }` (default `apiClient` imported from `./api/client`) and render `<StatusPage client={client} />` inside `<main>` in place of the placeholder paragraph. Update `src/main.tsx` to wrap `<App />` in a `QueryClientProvider` with `new QueryClient({ defaultOptions: { queries: { retry: 2, retryDelay: 1500 } } })`.

- [ ] **Step 6: Run to verify pass, then the full frontend gate**

```powershell
pnpm --dir apps/web test:cov
pnpm --dir apps/web format
pnpm --dir apps/web lint
$env:VITE_API_URL = "https://api.example.com"; pnpm --dir apps/web build; Remove-Item Env:VITE_API_URL
```
Expected: all tests PASS with coverage thresholds met; lint clean; build succeeds. If `AbortSignal.timeout` is undefined in the jsdom test environment, replace it with a small helper that builds an `AbortController` and a `setTimeout` abort.

- [ ] **Step 7: Commit**

```powershell
git add -A
git commit -m "feat: add typed API client and status page with cold-start handling"
```

---

### Task 10: Post-deploy smoke tool

**Files:**
- Create: `apps/api/src/ddq_api/ops/__init__.py` (empty), `ops/smoke.py`, `apps/api/tests/test_smoke.py`

**Interfaces:**
- Consumes: the live/served shapes of `/health`, `/ready` (Task 4), CORS and security headers (Task 5).
- Produces: `CheckResult(name, ok, detail)`; check functions; `run_smoke(api_url, web_url, client: httpx.Client) -> list[CheckResult]`; CLI `python -m ddq_api.ops.smoke --api URL --web URL` (exit code 1 if any check fails).

- [ ] **Step 1: Write the failing tests** `apps/api/tests/test_smoke.py`

```python
import httpx

from ddq_api.ops.smoke import run_smoke

API = "https://api.example.com"
WEB = "https://app.example.com"

API_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "x-request-id": "abc12345",
}
WEB_HEADERS = {
    "content-security-policy": "default-src 'self'",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "strict-transport-security": "max-age=63072000",
}


def _handler(*, db_ok: bool = True, cors_for_evil: bool = False, web_root: bool = True):
    def handle(request: httpx.Request) -> httpx.Response:
        origin = request.headers.get("origin")
        if request.url.host == "app.example.com":
            body = '<div id="root"></div>' if web_root else "<html></html>"
            return httpx.Response(200, text=body, headers=WEB_HEADERS)
        headers = dict(API_HEADERS)
        if origin == WEB or (origin == "https://evil.example" and cors_for_evil):
            headers["access-control-allow-origin"] = origin
        if request.url.path == "/health":
            data = {"status": "ok", "version": "0.1.0", "environment": "production"}
            return httpx.Response(200, json={"data": data, "error": None, "meta": {}}, headers=headers)
        data = {"status": "ready" if db_ok else "degraded", "checks": {"database": {"ok": db_ok}}}
        return httpx.Response(200 if db_ok else 503, json={"data": data, "error": None, "meta": {}}, headers=headers)

    return handle


def _run(**kwargs: bool) -> list:
    client = httpx.Client(transport=httpx.MockTransport(_handler(**kwargs)))
    return run_smoke(API, WEB, client)


def test_all_checks_pass_on_a_healthy_deployment() -> None:
    results = _run()
    assert results
    assert all(r.ok for r in results), [r for r in results if not r.ok]


def test_fails_when_database_is_down() -> None:
    failed = {r.name for r in _run(db_ok=False) if not r.ok}
    assert "api /ready database" in failed


def test_fails_when_cors_allows_an_unknown_origin() -> None:
    failed = {r.name for r in _run(cors_for_evil=True) if not r.ok}
    assert "api CORS rejects unknown origin" in failed


def test_fails_when_web_shell_is_missing() -> None:
    failed = {r.name for r in _run(web_root=False) if not r.ok}
    assert "web serves the app shell" in failed


def test_trailing_slashes_are_tolerated() -> None:
    client = httpx.Client(transport=httpx.MockTransport(_handler()))
    assert all(r.ok for r in run_smoke(API + "/", WEB + "/", client))
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest apps/api/tests/test_smoke.py --no-cov -q`
Expected: FAIL (`ModuleNotFoundError: ddq_api.ops.smoke`).

- [ ] **Step 3: Implement** `apps/api/src/ddq_api/ops/smoke.py`

```python
"""Post-deploy smoke checks: python -m ddq_api.ops.smoke --api URL --web URL"""

import argparse
import sys
from dataclasses import dataclass
from typing import Any

import httpx

_REQUEST_TIMEOUT_S = 120.0  # the free-tier API may be asleep
_EVIL_ORIGIN = "https://evil.example"
_API_HEADERS = ("x-content-type-options", "x-frame-options", "referrer-policy", "x-request-id")
_WEB_HEADERS = (
    "content-security-policy",
    "x-content-type-options",
    "x-frame-options",
    "strict-transport-security",
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


def _json(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _missing(response: httpx.Response, required: tuple[str, ...]) -> list[str]:
    return [h for h in required if h not in response.headers]


def run_smoke(api_url: str, web_url: str, client: httpx.Client) -> list[CheckResult]:
    api, web = api_url.rstrip("/"), web_url.rstrip("/")
    health = client.get(f"{api}/health", timeout=_REQUEST_TIMEOUT_S)
    ready = client.get(f"{api}/ready", timeout=_REQUEST_TIMEOUT_S)
    cors_ok = client.get(f"{api}/health", headers={"Origin": web}, timeout=_REQUEST_TIMEOUT_S)
    cors_bad = client.get(f"{api}/health", headers={"Origin": _EVIL_ORIGIN}, timeout=_REQUEST_TIMEOUT_S)
    shell = client.get(web, timeout=_REQUEST_TIMEOUT_S)

    health_data = _json(health).get("data") or {}
    ready_data = _json(ready).get("data") or {}
    db_ok = ((ready_data.get("checks") or {}).get("database") or {}).get("ok") is True
    api_missing = _missing(health, _API_HEADERS)
    web_missing = _missing(shell, _WEB_HEADERS)

    return [
        CheckResult("api /health", health.status_code == 200 and health_data.get("status") == "ok",
                    f"status={health.status_code}"),
        CheckResult("api /ready database", ready.status_code == 200 and db_ok,
                    f"status={ready.status_code}"),
        CheckResult("api CORS allows the web origin",
                    cors_ok.headers.get("access-control-allow-origin") == web),
        CheckResult("api CORS rejects unknown origin",
                    "access-control-allow-origin" not in cors_bad.headers),
        CheckResult("api security headers", not api_missing, f"missing={api_missing}"),
        CheckResult("web serves the app shell", shell.status_code == 200 and 'id="root"' in shell.text,
                    f"status={shell.status_code}"),
        CheckResult("web security headers", not web_missing, f"missing={web_missing}"),
    ]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Post-deploy smoke checks")
    parser.add_argument("--api", required=True, help="API base URL")
    parser.add_argument("--web", required=True, help="Web app base URL")
    args = parser.parse_args(argv)
    with httpx.Client(follow_redirects=True) as client:
        results = run_smoke(args.api, args.web, client)
    for result in results:
        sys.stdout.write(f"{'PASS' if result.ok else 'FAIL'}  {result.name}  {result.detail}\n")
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run to verify pass, then the full backend gate**

```powershell
uv run pytest -q
uv run ruff check . ; uv run ruff format . ; uv run mypy packages/analytics/src apps/api/src
```
Expected: all PASS, coverage ≥ 80%, tools clean.

- [ ] **Step 5: Commit**

```powershell
git add -A
git commit -m "feat: add post-deploy smoke checks"
```

---

### Task 11: CI workflows

**Files:**
- Create: `.github/workflows/ci.yml`, `.github/workflows/keepwarm.yml`

**Interfaces:**
- Consumes: all commands from Tasks 2–10 (`uv sync --frozen`, `ruff`, `mypy`, `lint-imports`, `pytest`, `pnpm lint|format:check|test:cov|build|gen:api`, `python -m ddq_api.export_openapi`).
- Produces: required checks on every PR/push; a `migrate` job for `main`; a keep-warm ping.

- [ ] **Step 1: Write `.github/workflows/ci.yml`**

```yaml
name: ci

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: ddq_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U postgres"
          --health-interval 5s --health-timeout 5s --health-retries 10
    env:
      DDQ_TEST_DATABASE_URL: postgresql://postgres:postgres@localhost:5432/ddq_test
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy packages/analytics/src apps/api/src
      - run: uv run lint-imports
      - run: uv run pytest

  web:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/web
    env:
      VITE_API_URL: https://api.example.invalid
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          package_json_file: apps/web/package.json
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: pnpm
          cache-dependency-path: apps/web/pnpm-lock.yaml
      - run: pnpm install --frozen-lockfile
      - run: pnpm lint
      - run: pnpm format:check
      - run: pnpm test:cov
      - run: pnpm build

  contract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - uses: pnpm/action-setup@v4
        with:
          package_json_file: apps/web/package.json
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: pnpm
          cache-dependency-path: apps/web/pnpm-lock.yaml
      - run: uv sync --frozen
      - run: pnpm --dir apps/web install --frozen-lockfile
      - run: uv run python -m ddq_api.export_openapi
      - run: pnpm --dir apps/web gen:api
      - name: Fail on API contract drift
        run: git diff --exit-code -- apps/api/openapi.json apps/web/src/api/schema.d.ts

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      - uses: astral-sh/setup-uv@v6
      - run: uv sync --frozen
      - run: uv run pip-audit --skip-editable
      - uses: pnpm/action-setup@v4
        with:
          package_json_file: apps/web/package.json
      - run: pnpm --dir apps/web audit --prod --audit-level high

  migrate:
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: [backend, web, contract, security]
    runs-on: ubuntu-latest
    environment: production
    env:
      DDQ_DATABASE_MIGRATION_URL: ${{ secrets.DDQ_DATABASE_MIGRATION_URL }}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv sync --frozen
      - name: Apply migrations (skipped until the secret exists)
        if: env.DDQ_DATABASE_MIGRATION_URL != ''
        run: uv run alembic -c apps/api/alembic.ini upgrade head
```

- [ ] **Step 2: Write `.github/workflows/keepwarm.yml`**

```yaml
name: keepwarm

# Pings the API so the free-tier instance stays awake for visitors and the Supabase
# project sees database activity (free projects pause after ~1 week idle).
# Trade-off: best-effort cron; GitHub disables schedules after 60 days without repo activity.
on:
  schedule:
    - cron: "*/10 * * * *"
  workflow_dispatch:

permissions: {}

jobs:
  ping:
    runs-on: ubuntu-latest
    env:
      API_URL: ${{ vars.API_URL }}
    steps:
      - name: Ping /ready (skipped until API_URL is configured)
        if: env.API_URL != ''
        run: curl --fail --silent --show-error --max-time 120 --retry 3 --retry-delay 10 "$API_URL/ready"
```

- [ ] **Step 3: Lint the workflows locally.** Run: `uvx actionlint` is not available on PyPI, so use `pnpm dlx @action-validator/cli .github/workflows/ci.yml .github/workflows/keepwarm.yml`.
Expected: no errors. (If the tool is unavailable, rely on the first GitHub run in Task 14 and fix any syntax error then.)

- [ ] **Step 4: Run every CI command locally once, in CI order,** to catch drift before pushing:

```powershell
uv sync --frozen
uv run ruff check . ; uv run ruff format --check . ; uv run mypy packages/analytics/src apps/api/src ; uv run lint-imports ; uv run pytest
uv run python -m ddq_api.export_openapi ; pnpm --dir apps/web gen:api ; git diff --exit-code -- apps/api/openapi.json apps/web/src/api/schema.d.ts
uv run pip-audit --skip-editable
pnpm --dir apps/web audit --prod --audit-level high
```
Expected: everything exits 0. Fix any vulnerability report by upgrading the dependency (do not silence the audit).

- [ ] **Step 5: Commit**

```powershell
git add -A
git commit -m "ci: add lint, type, test, contract, security, migration and keep-warm workflows"
```

---

### Task 12: Deployment configuration

**Files:**
- Create: `render.yaml`, `apps/web/vercel.json`

**Interfaces:**
- Consumes: `create_app` factory (Task 4), env var names (`DDQ_*`), `VITE_API_URL` (Task 9).
- Produces: a Render Blueprint (`ddq-api`) and Vercel config (SPA fallback + security headers/CSP).

- [ ] **Step 1: Write `render.yaml`**

```yaml
services:
  - type: web
    name: ddq-api
    runtime: python
    plan: free
    region: oregon # pick the region closest to your Supabase project, then keep them aligned
    buildCommand: pip install uv && uv sync --frozen --no-dev --package ddq-api
    startCommand: uv run --no-sync uvicorn ddq_api.main:create_app --factory --host 0.0.0.0 --port $PORT --no-access-log
    healthCheckPath: /health
    autoDeployTrigger: checksPass
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.10
      - key: DDQ_ENVIRONMENT
        value: production
      - key: DDQ_TRUSTED_PROXY_HOPS
        value: "1"
      - key: DDQ_DATABASE_URL
        sync: false
      - key: DDQ_ALLOWED_ORIGINS
        sync: false
```
`healthCheckPath` is `/health` on purpose (Review Focus 3). `sync: false` means Render asks for the value in the dashboard; no secret is ever committed.

- [ ] **Step 2: Write `apps/web/vercel.json`**

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        { "key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=()" },
        { "key": "Strict-Transport-Security", "value": "max-age=63072000; includeSubDomains" },
        {
          "key": "Content-Security-Policy",
          "value": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' https://*.onrender.com https://*.supabase.co; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        }
      ]
    }
  ]
}
```
Task 15 tightens `connect-src` to the exact API URL once it is known.

- [ ] **Step 3: Validate the files parse**

```powershell
python -c "import json; json.load(open('apps/web/vercel.json'))"
uv run python -c "import yaml" 2>$null; python -c "import sys,tomllib; print('ok')"
```
Then check the Blueprint: `pnpm dlx @render-oss/render-yaml-validator render.yaml` if it exists; otherwise the Blueprint is validated by Render when connected (Task 15). Expected: `vercel.json` parses.

- [ ] **Step 4: Prove the exact start command works locally** (with dummy env, no DB needed for `/health`):

```powershell
$env:DDQ_DATABASE_URL = "postgresql://u:p@localhost:5432/db"; $env:DDQ_ALLOWED_ORIGINS = "http://localhost:5173"
uv run --no-sync uvicorn ddq_api.main:create_app --factory --port 8000
```
In a second terminal: `curl http://localhost:8000/health` → `{"data":{"status":"ok",…}}`, and `curl -i http://localhost:8000/ready` → 503 `not_ready` (no database). Stop the server and clear the env vars (`Remove-Item Env:DDQ_DATABASE_URL, Env:DDQ_ALLOWED_ORIGINS`).

- [ ] **Step 5: Commit**

```powershell
git add -A
git commit -m "ci: add Render blueprint and Vercel configuration"
```

---

### Task 13: Architecture decision records, architecture doc and README

**Files:**
- Create: `docs/adr/0000-template.md`, `docs/adr/0001-supabase-auth.md` … `docs/adr/0011-in-process-rate-limiting.md`, `docs/architecture.md`, `docs/ops/setup-guide.md`, `README.md`

**Interfaces:**
- Consumes: decisions D1–D10 from `docs/PLAN.md` §2, plus choices made during Phase 0.
- Produces: the documentation set the Phase 0 deliverable requires ("ADRs for D1–D10").

- [ ] **Step 1: Write the template** `docs/adr/0000-template.md`

```markdown
# ADR NNNN: Title

- Status: Accepted | Superseded by ADR-NNNN
- Date: YYYY-MM-DD

## Context
What forces are at play?

## Decision
What did we choose?

## Consequences
What becomes easier, what becomes harder, and what did we reject?
```

- [ ] **Step 2: Write the eleven ADRs.** Each file uses the template, status "Accepted", date 2026-09-24, and this content (Context / Decision / Consequences):

| File | Title | Context → Decision → Consequences (write each as 2–4 sentences) |
|------|-------|------|
| `0001-supabase-auth.md` | Supabase Auth for sign-in | Need email/password + Google + GitHub sign-in without storing passwords or hand-rolling OAuth. → The SPA signs in with `supabase-js`; FastAPI only verifies the JWT (JWKS signature, `aud`, `exp`, `iss`). → No password handling in our code and a smaller attack surface; we depend on Supabase's free-tier limits, and authorization stays our job (owner checks in the service layer). Rejected: Authlib + argon2 (more to defend, no upside). |
| `0002-render-for-the-api.md` | Render for the API host | Free API hosting is needed; Fly.io no longer offers a free tier for new accounts (confirmed in `docs/ops/free-tier-verification.md`). → Render free web service with the native Python runtime (no Docker on the dev machine). → Cold starts (~30–60 s) are handled in the SPA and softened by a keep-warm workflow (best-effort cron; GitHub disables idle-repo schedules after 60 days); 512 MB RAM bounds compute (limits on Monte Carlo size later). |
| `0003-postgres-job-queue.md` | Postgres job queue ticked by GitHub Actions | Render free has no worker or cron, yet alerts need scheduled, retryable, idempotent work. → A `jobs` table claimed with `FOR UPDATE SKIP LOCKED`, run by a bounded batch at each tick from a GitHub Actions cron calling a secret-protected endpoint (built in Phase 7). → No extra infrastructure and a visible SQL-based queue design; cron timing is best-effort, so jobs must tolerate delay and duplicates (dedupe keys, unique alert-event windows). |
| `0004-brevo-email-behind-a-port.md` | Brevo email behind an `EmailSender` port | Alert emails need a free provider; Resend's free tier needs a verified domain to email third parties. → Brevo (sender-address verification only) behind an `EmailSender` port. → Swapping to Resend is one adapter; deliverability without a custom domain is modest, acceptable for alert emails to the owner. |
| `0005-echarts.md` | Apache ECharts for charts | Need heatmaps, zoomable time series, fan charts and a dark theme. → ECharts, tree-shaken. → Rich chart types out of the box; larger dependency than Recharts but far less than full Plotly. Rejected: Plotly (bundle size), Recharts (weak heatmap/fan charts). |
| `0006-api-is-the-only-db-client.md` | API is the only database client; RLS deny-all | Supabase exposes `public` over REST; authorization scattered across policies is hard to test. → SQLAlchemy 2 async + Alembic; only FastAPI connects; every table has row-level security enabled with no policies, and a CI test (`test_database.py`) fails if any table lacks it. → One authorization surface testable in Python; migrations run over the session pooler, runtime uses the transaction pooler with prepared-statement caching disabled. |
| `0007-reportlab-for-pdf.md` | ReportLab for PDF reports | Need PDF export within a 512 MB free instance and without system libraries. → ReportLab + matplotlib (pure pip). → Reports are laid out in code rather than HTML/CSS; no Pango/Cairo install on Render. Rejected: WeasyPrint. |
| `0008-lean-runtime-dependencies.md` | numpy/scipy only in production; heavy libraries as test oracles | 512 MB RAM, and self-implemented math is stronger interview material. → OLS with Newey-West errors, Ledoit-Wolf shrinkage and the optimizer are implemented in numpy/scipy; statsmodels and scikit-learn are dev-only reference implementations the tests compare against. → Slimmer deploys; more code to own, mitigated by oracle tests. |
| `0009-contract-first-types.md` | Contract-first API types | Hand-written duplicate types drift. → `apps/api/openapi.json` is committed; `openapi-typescript` generates `apps/web/src/api/schema.d.ts`; CI regenerates both and fails on any diff (and a pytest guards the JSON). → Frontend/backend mismatches surface in CI; contributors must run two commands after changing an endpoint. |
| `0010-monorepo-uv-and-pnpm.md` | Monorepo with a uv workspace and a standalone pnpm project | One repo to show and one CI, with a hard dependency direction. → uv workspace for `packages/analytics` + `apps/api`; `apps/web` is its own pnpm project (Vercel root directory `apps/web`); import-linter forbids `ddq_analytics` from importing web/DB/network libraries. → Analytics stays pure and reusable in a notebook; two toolchains to run. |
| `0011-in-process-rate-limiting.md` | In-process rate limiting with `limits` | Need per-client limits on a single free instance; slowapi is a thin wrapper that couples limits to decorators and its own exception handler. → A small ASGI middleware using the `limits` library directly (fixed window, in-memory), keyed by the client IP resolved from the `hops`-th right-most `X-Forwarded-For` entry (`DDQ_TRUSTED_PROXY_HOPS`). → Fully controlled envelope, headers and CORS interplay; limits are per instance and reset on restart (documented limitation). Also recorded here: unhandled-500 responses come from Starlette's outermost layer and therefore lack CORS headers. |

- [ ] **Step 3: Write `docs/architecture.md`.** Contents: a one-paragraph purpose; the mermaid architecture diagram copied verbatim from `docs/PLAN.md` §3; the dependency rule (`routers → services → {analytics, providers, repositories}`; `ddq_analytics` imports nothing from `apps/`); the middleware order table from Task 5; the request flow paragraph from `docs/PLAN.md` §3; links to the ADR index (a bulleted list of the eleven ADR files).

- [ ] **Step 4: Write `docs/ops/setup-guide.md`.** Sections, each with numbered steps the user performs themselves (the agent never enters credentials or creates accounts):
  1. **GitHub**: `gh repo create ddq-portfolio-dashboard --public --source . --remote origin --push` (after confirming with the user, Task 14).
  2. **Supabase**: New project `ddq-portfolio-dashboard`, choose a region, save the database password in a password manager; Project Settings → Database → Connection string → copy the **transaction pooler** string (port 6543) and the **session pooler** string (port 5432); URL-encode special characters in the password.
  3. **Local `.env`**: copy `.env.example` to `.env`, fill both database URLs, keep `.env` uncommitted.
  4. **GitHub secrets/variables**: `gh secret set DDQ_DATABASE_MIGRATION_URL` (paste when prompted); repo variable `API_URL` after Render is live; create the `production` environment.
  5. **Render**: New → Blueprint → select the repo; when asked, set `DDQ_DATABASE_URL` (transaction pooler) and `DDQ_ALLOWED_ORIGINS` (the Vercel production URL, `https`, no trailing slash).
  6. **Vercel**: Import the repo, Root Directory `apps/web`, env var `VITE_API_URL` = the Render URL.
  7. **Order of operations** and where each URL is needed (API URL → Vercel; Vercel URL → Render CORS).

- [ ] **Step 5: Write `README.md`** (v0). Sections: title and one-line pitch; badges (CI status via `https://github.com/<owner>/ddq-portfolio-dashboard/actions/workflows/ci.yml/badge.svg`, owner filled in Task 14); **Status** ("Phase 0: walking skeleton complete; risk analytics arrive in Phase 2"); **Live demo** (URL added in Task 15); **Architecture** (link to `docs/architecture.md`); **Repo layout**; **Local development**:

```bash
uv sync
cp .env.example .env   # then edit
uv run uvicorn ddq_api.main:create_app --factory --reload
pnpm --dir apps/web install
pnpm --dir apps/web dev
```
**Tests and checks** (`uv run pytest`, `pnpm --dir apps/web test`, `uv run ruff check .`, `uv run mypy packages/analytics/src apps/api/src`, `uv run lint-imports`); **Regenerating the API contract** (`uv run python -m ddq_api.export_openapi` then `pnpm --dir apps/web gen:api`); **Docs** (PLAN, ADRs, ops guides); **Disclaimer** ("Educational project, not investment advice; market data sources are attributed in later phases"); **License** (MIT).

- [ ] **Step 6: Verify links and formatting**

```powershell
Get-ChildItem docs/adr | Measure-Object            # expect 12 files (template + 11 ADRs)
pnpm --dir apps/web format:check
```
Expected: 12 files; formatting passes. Open `README.md` and confirm every relative link resolves to an existing file.

- [ ] **Step 7: Commit**

```powershell
git add -A
git commit -m "docs: add ADRs, architecture overview, setup guide and README"
```

---

### Task 14: Review pass before going live

**Files:**
- Modify: whichever files the reviews flag.

**Interfaces:**
- Consumes: the whole branch.
- Produces: a branch with no unresolved CRITICAL/HIGH findings.

- [ ] **Step 1: Run the reviews in parallel** (independent, per the agent-orchestration rule) on `git diff` of the whole repo: `code-reviewer`, `python-reviewer` (backend), `typescript-reviewer` (web), and `security-reviewer` (settings, middleware, CORS, CSP, workflows: this is security-sensitive code).

- [ ] **Step 2: Triage.** Fix every CRITICAL and HIGH finding test-first (add a failing test, then fix). Fix MEDIUM findings when cheap; record any deliberately skipped finding with a one-line reason in the commit message. Re-run the full local gate from Task 11 Step 4.

- [ ] **Step 3: Confirm the Review Focus tests all exist and pass.**

Run: `uv run pytest -q -k "database_is_down or leak or hunter2 or spoofed" --no-cov ; pnpm --dir apps/web test -- --run`
Expected: PASS (items 2, 3, 5 backend; items 1, 4 web).

- [ ] **Step 4: Commit fixes**

```powershell
git add -A
git commit -m "fix: address review findings"
```
(Skip if there were none.)

---

### Task 15: Go live and verify the Phase 0 exit criteria

This task publishes code and touches accounts, so it is **interactive**: the agent confirms each outward-facing step with the user, and the user enters every credential themselves.

**Files:**
- Modify: `apps/web/vercel.json` (tighten CSP), `README.md` (URLs, badge), `docs/ops/free-tier-verification.md` (findings), possibly `docs/PLAN.md`.

**Interfaces:**
- Consumes: everything above; the user's accounts (GitHub `dioconnoi` is the logged-in `gh` account, Supabase, Render, Vercel).
- Produces: live URLs, a green CI run, a passing smoke run, and a completed exit checklist.

- [ ] **Step 1: Ask, then publish the repo.** Ask the user to confirm: "Create the PUBLIC repo `dioconnoi/ddq-portfolio-dashboard` from this folder and push?" Only after an explicit yes:

```powershell
gh repo create ddq-portfolio-dashboard --public --source . --remote origin --push --description "DDQ (Data Driven Quant) Portfolio Risk Analytics Dashboard"
```
Expected: repo created and `main` pushed. Watch the first CI run: `gh run watch` (or `gh run list --limit 1`). Fix anything red (workflow syntax, lockfile drift, `pip-audit` findings) before continuing. The `migrate` job will skip its step (no secret yet).

- [ ] **Step 2: Walk the user through the accounts** using `docs/ops/setup-guide.md` (Supabase → GitHub secret → Render → Vercel). The user performs each dashboard action and enters all credentials; the agent never sees passwords. Note the resulting URLs: `API_URL` (Render) and `WEB_URL` (Vercel).

- [ ] **Step 3: Tighten the CSP.** In `apps/web/vercel.json` replace `https://*.onrender.com https://*.supabase.co` in `connect-src` with the exact API origin (Supabase stays only if Phase 3 needs it; remove it now and re-add in Phase 3). Set the repo variable `API_URL` (`gh variable set API_URL --body "<render url>"`). Commit `fix: restrict CSP connect-src to the API origin` and push.

- [ ] **Step 4: Apply migrations to Supabase via CI.** Trigger the `ci` workflow on `main` (the push in Step 3 does this). Expected: the `migrate` job runs `alembic upgrade head` successfully. Verify in Supabase (Table Editor) that `alembic_version` exists with `RLS enabled` and version `0001`.

- [ ] **Step 5: Run the smoke test against production**

```powershell
uv run python -m ddq_api.ops.smoke --api <API_URL> --web <WEB_URL>
```
Expected: every line `PASS`. The first request may take up to ~60 s (cold start), which is itself the behaviour the SPA's "waking" state covers.

- [ ] **Step 6: Verify the trusted-proxy assumption.** The rate limiter trusts the `DDQ_TRUSTED_PROXY_HOPS=1`-th right-most `X-Forwarded-For` entry. Confirm that this is Render's real edge behaviour, from two different networks (laptop and phone tethering): exceed `120/minute` from the laptop (`1..130 | % { curl.exe -s -o NUL -w "%{http_code}`n" <API_URL>/health } | Select-Object -Last 3` → `429`), then request `/health` from the phone. Expected: the phone is NOT limited. If it is, Render has an extra proxy: set `DDQ_TRUSTED_PROXY_HOPS=2` in the Render dashboard and repeat. Record the finding in `docs/ops/free-tier-verification.md`.

- [ ] **Step 7: Verify the SPA by eye.** Open `WEB_URL` in the browser pane (`mcp__Claude_Browser__preview_start` with the URL) and take a screenshot. Check: header, status card shows Online with the API version and "Connected"; toggle Light → Dark → System and confirm the colours change and persist across reload; open DevTools console and confirm there are no CSP violations or errors (`read_console_messages`). To see the cold-start state, wait for the Render instance to sleep, reload, and confirm "Waking the API…" appears (or simulate in DevTools by blocking the API host).

- [ ] **Step 7b: Free-tier findings.** Update `docs/ops/free-tier-verification.md` with what was actually observed (cold-start time, memory headroom in Render's metrics, whether `.venv` persisted between build and start). If a finding invalidates an ADR or the PLAN, amend the document in the same commit and tell the user.

- [ ] **Step 8: Update the README** with the live demo URL and the CI badge (replace `<owner>` with `dioconnoi`). Commit and push: `docs: add live demo URL and CI badge`.

- [ ] **Step 9: Phase 0 exit checklist.** Confirm each item against evidence (command output or screenshot) before declaring the phase done, and report any gap plainly:
  - [ ] Live SPA on Vercel shows live API and DB health from Render/Supabase.
  - [ ] Light, dark and system themes work.
  - [ ] CI is green on `main` (backend, web, contract, security, migrate).
  - [ ] Smoke test passes against production.
  - [ ] `alembic_version` in Supabase has RLS enabled; the RLS guard test is green in CI.
  - [ ] ADRs 0001–0011 exist and `docs/ops/free-tier-verification.md` is complete.
  - [ ] No secrets in the repository (`gitleaks` job green).
  - [ ] Backend coverage ≥ 80% and web coverage thresholds met.

- [ ] **Step 10: Save project memory.** Write a `project` memory (with an entry in `MEMORY.md`) recording: the repo location and slug, live URLs, that Phase 0 is complete, and that Phase 1 (market data layer) is next. Then report to the user and ask whether to proceed to the Phase 1 plan.

---

## Self-review

**Spec coverage (`docs/PLAN.md` §13 Phase 0):**
- Repo, monorepo layout, tooling → Task 2. CI → Task 11. Secrets policy → Tasks 2, 3 (fail-fast settings, `.env.example`, gitleaks), 11.
- Supabase project + Alembic baseline (no data tables) → Tasks 6, 15. Deploy pipelines → Tasks 11, 12, 15.
- Verification of free-tier assumptions → Task 1 (+ Task 15 Steps 6–7b for observed behaviour).
- Deliverable "live SPA showing live API + DB health" → Tasks 9, 15. "Light/dark theme" → Task 8. "CI green" → Tasks 11, 15. "ADRs for D1–D10" → Task 13 (eleven ADRs; D1–D10 plus rate limiting).
- Cross-cutting requirements applied in Phase 0: input validation (settings, origins, request ids, body size), rate limiting, explicit error handling (handlers), no debug statements (ruff T20, ESLint), immutability (frozen settings/envelope), contract-first types, ≥80% coverage gates.
- Gap noted and accepted: the PLAN's Playwright E2E arrives in Phase 3; Phase 0 has the smoke script instead. The PLAN says the base path is `/api/v1`; health endpoints intentionally live at the root (infrastructure routes) and versioned business routes start in Phase 1; ADR 0011 and this note record it.

**Placeholder scan:** no TBD/TODO; every code step contains code; ADR rows specify the content to write; the only deferred values are runtime facts (URLs, dates verified in Task 1) that cannot exist before the work is done.

**Type consistency:** `Settings` fields (`database_url`, `database_migration_url`, `allowed_origins`, `rate_limit_default`, `trusted_proxy_hops`, `max_request_bytes`, `log_level`) are used with identical names in Tasks 3–7, in `.env.example` and in `render.yaml`. `create_app(settings, *, db_health=…)`, `make_client(*, db_error, db_delay, **overrides)`, `client_ip(request, hops)`, `HealthOut/ReadyOut/CheckOut`, `ApiClient`, `StatusInputs`/`deriveStatus`, `useApiStatus` and `fakeFetch` match across the tasks that define and use them. Env var `DDQ_DATABASE_MIGRATION_URL` is consistent in `.env.example`, `env.py`, the integration test and CI.
