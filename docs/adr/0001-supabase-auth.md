# ADR 0001: Supabase Auth for sign-in

- Status: Accepted
- Date: 2026-09-24

## Context

The product needs email/password, Google and GitHub sign-in without storing passwords or hand-rolling OAuth flows.

## Decision

The SPA signs in with `supabase-js`. FastAPI only verifies the resulting JWT (JWKS signature, `aud`, `exp`, `iss`). Authentication is built in Phase 3.

## Consequences

Our code never handles passwords, which shrinks the attack surface. We depend on Supabase's free-tier limits, and authorization stays our responsibility (owner checks in the service layer, covered by tests that try to read another user's portfolio). Rejected: Authlib + argon2 (more to defend, no upside).
