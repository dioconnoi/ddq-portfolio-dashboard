# ADR 0002: Render for the API host

- Status: Accepted
- Date: 2026-09-24

## Context

The API needs free hosting. Fly.io no longer offers a free tier for new accounts (a 7-day / 2-hour trial only; see `docs/ops/free-tier-verification.md`).

## Decision

Render's free web service with the native Python runtime (no Docker on the development machine). The Python version is pinned explicitly (`PYTHON_VERSION=3.12.10`) because Render's default for new services is 3.14.

## Consequences

Free instances sleep after 15 minutes idle and take about a minute to wake, which the SPA handles with an explicit "waking the API" state. A keep-warm workflow softens this; its cron is best-effort and GitHub disables scheduled workflows in public repositories after 60 days without repository activity. The roughly 500 MB RAM ceiling bounds compute (Monte Carlo and optimizer sizes are limited in later phases).
