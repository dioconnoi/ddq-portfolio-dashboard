# ADR 0010: Monorepo with a uv workspace and a standalone pnpm project

- Status: Accepted
- Date: 2026-09-24

## Context

One repository is easier to show and to gate with one CI, but the analytics core must stay reusable and free of web dependencies.

## Decision

A uv workspace holds `packages/analytics` and `apps/api`. `apps/web` is its own pnpm project (Vercel root directory `apps/web`). An import-linter contract forbids `ddq_analytics` from importing `ddq_api`, `fastapi`, `sqlalchemy`, `asyncpg` or `httpx`.

## Consequences

The analytics core can be used from a notebook and tested in isolation. Two toolchains (uv and pnpm) have to be run; CI runs both.
