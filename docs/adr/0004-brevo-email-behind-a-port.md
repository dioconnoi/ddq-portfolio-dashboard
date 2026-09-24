# ADR 0004: Brevo email behind an `EmailSender` port

- Status: Accepted
- Date: 2026-09-24

## Context

Alert emails need a free provider. Resend's free tier only delivers to the account owner until a domain is verified, and the project owner may not have a domain.

## Decision

Brevo (300 emails per day on the free plan) behind an `EmailSender` port. The exact sender-verification flow is re-checked at the start of Phase 7.

## Consequences

Switching to Resend is one adapter if a domain becomes available. Deliverability without a custom domain is modest, which is acceptable for alert emails sent to the portfolio owner.
