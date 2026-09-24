# ADR 0011: In-process rate limiting with `limits`

- Status: Accepted
- Date: 2026-09-24

## Context

Per-client rate limits are needed on a single free instance. slowapi is a thin wrapper that couples limits to route decorators and its own exception handler, which complicates the response envelope and CORS behaviour.

## Decision

A small ASGI middleware uses the `limits` library directly (fixed window, in-memory, async storage). The client key is derived defensively:

- With `DDQ_TRUSTED_PROXY_HOPS=0` the `X-Forwarded-For` header is ignored.
- Otherwise the key is the `hops`-th entry from the right of the header, with all header lines joined (a client can send several). Entries to the left of the trusted proxy's are client-controlled and can be forged.
- The chosen entry must be a valid IP address, otherwise the socket peer is used. IPv6 addresses collapse to their /64 so one subscriber cannot mint unlimited keys.

## Consequences

The 429 response is a normal envelope, carries CORS headers and a `Retry-After` header, and is fully unit-tested. Limits are per API instance and reset on restart, which is acceptable for a single free instance. The number of tracked keys is bounded only by the number of distinct client addresses; a global fallback limiter is deferred until endpoints that are expensive to call exist. The correct hop count for Render is verified at go-live.

Unhandled exceptions are turned into the 500 envelope by an innermost middleware rather than by Starlette's outermost error handler, so error responses still carry CORS and security headers, keep their request id, and appear in the access log. The outermost handler stays as a last resort for failures inside the outer layers.
