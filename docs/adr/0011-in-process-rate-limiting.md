# ADR 0011: In-process rate limiting with `limits`

- Status: Accepted
- Date: 2026-09-24

## Context

Per-client rate limits are needed on a single free instance. slowapi is a thin wrapper that couples limits to route decorators and its own exception handler, which complicates the response envelope and CORS behaviour.

## Decision

A small ASGI middleware uses the `limits` library directly (fixed window, in-memory). The client address is the `DDQ_TRUSTED_PROXY_HOPS`-th entry from the right of `X-Forwarded-For`; with zero trusted proxies the header is ignored, because entries to the left of the trusted proxy's are client-controlled and can be forged.

## Consequences

The 429 response is a normal envelope, carries CORS headers and a `Retry-After` header, and is fully unit-tested. Limits are per API instance and reset on restart, which is acceptable for a single free instance. The correct hop count for Render is verified at go-live.

Also recorded here: responses to unhandled exceptions (HTTP 500) are produced by Starlette's outermost layer, so they do not carry CORS headers. The browser shows a network error instead of the envelope in that case; the failure is logged with its request id.
