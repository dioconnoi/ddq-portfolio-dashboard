# ADR 0009: Contract-first API types

- Status: Accepted
- Date: 2026-09-24

## Context

Hand-written frontend types that duplicate backend schemas drift silently.

## Decision

`apps/api/openapi.json` is committed and rendered deterministically by `ddq_api.export_openapi`. `openapi-typescript` generates `apps/web/src/api/schema.d.ts` from it. CI regenerates both and fails on any diff, and a pytest guards the JSON.

## Consequences

Frontend/backend mismatches surface in CI. Contributors run two commands after changing an endpoint: `uv run python -m ddq_api.export_openapi` and `pnpm --dir apps/web gen:api`.
