# ADR 0003: Postgres job queue ticked by GitHub Actions

- Status: Accepted
- Date: 2026-09-24

## Context

Render's free tier has no worker or cron service, yet risk-limit alerts need scheduled, retryable, idempotent work.

## Decision

A `jobs` table claimed with `FOR UPDATE SKIP LOCKED`. A GitHub Actions cron calls a secret-protected endpoint that runs a bounded batch of due jobs (built in Phase 7).

## Consequences

No extra infrastructure, and the queue design is visible SQL. Cron timing is best-effort, so jobs must tolerate delay and duplicates: dedupe keys on jobs and a unique window key per alert event make retries idempotent.
