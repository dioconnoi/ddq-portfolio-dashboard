# ADR 0006: The API is the only database client; RLS deny-all

- Status: Accepted
- Date: 2026-09-24

## Context

Supabase exposes the `public` schema over REST. Authorization scattered across database policies is hard to test and easy to get wrong.

## Decision

SQLAlchemy 2 (async) with Alembic. Only FastAPI connects to Postgres. Every table has row-level security enabled with no policies, and an integration test (`apps/api/tests/integration/test_database.py`) fails the build if any table in `public` lacks it. Runtime uses Supabase's transaction pooler with prepared-statement caching disabled; migrations use the session pooler (IPv4, so GitHub Actions can reach it).

## Consequences

There is one authorization surface, testable in Python. Migrations must include `ENABLE ROW LEVEL SECURITY` for every new table. Migrations must be backward compatible with the previous app version (expand, then contract) because CI applies them before the new app deploys.
