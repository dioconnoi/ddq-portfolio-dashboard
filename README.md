# DDQ Portfolio Dashboard

**DDQ = Data Driven Quant.** A portfolio risk analytics dashboard: VaR/CVaR, Monte Carlo, stress tests, optimization and factor exposure, built with defensible methodology and production-quality engineering.

[![ci](https://github.com/dioconnoi/ddq-portfolio-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/dioconnoi/ddq-portfolio-dashboard/actions/workflows/ci.yml)

## Status

**Phase 0 (walking skeleton):** a React app shows live API and database health from a FastAPI service backed by Postgres, with CI, migrations and a deploy pipeline. Market data arrives in Phase 1 and the risk analytics in Phase 2. See the [project plan](docs/PLAN.md).

**Live demo:** _added when Phase 0 is deployed._

## Architecture

See [docs/architecture.md](docs/architecture.md) and the [decision records](docs/adr/0000-template.md).

```
packages/analytics/   pure Python analytics core (no I/O)
apps/api/             FastAPI service, Alembic migrations
apps/web/             React + TypeScript SPA (Vite, Tailwind)
docs/                 plan, architecture, ADRs, ops guides
```

## Local development

Requirements: Python 3.12, [uv](https://docs.astral.sh/uv/), Node 22+, pnpm.

```bash
uv sync
cp .env.example .env   # then edit the values
uv run uvicorn ddq_api.main:create_app --factory --reload
```

In a second terminal:

```bash
pnpm --dir apps/web install
pnpm --dir apps/web dev
```

## Tests and checks

```bash
uv run pytest
pnpm --dir apps/web test
uv run ruff check .
uv run mypy packages/analytics/src apps/api/src
uv run lint-imports
```

Database integration tests run when `DDQ_TEST_DATABASE_URL` points at a **throwaway** Postgres; CI provides one.

## Regenerating the API contract

After changing an endpoint:

```bash
uv run python -m ddq_api.export_openapi
pnpm --dir apps/web gen:api
```

## Docs

- [Project plan](docs/PLAN.md)
- [Architecture](docs/architecture.md)
- [Free-tier verification](docs/ops/free-tier-verification.md)
- [Setup guide: accounts and deployment](docs/ops/setup-guide.md)

## Disclaimer

Educational project, not investment advice. Market data sources are attributed in later phases.

## License

MIT, see [LICENSE](LICENSE).
