# ADR 0008: numpy/scipy only in production; heavy libraries as test oracles

- Status: Accepted
- Date: 2026-09-24

## Context

The API must fit in about 500 MB of RAM, and self-implemented quantitative methods are stronger evidence of understanding than library calls.

## Decision

OLS with Newey-West errors, Ledoit-Wolf shrinkage and the portfolio optimizer are implemented on numpy/scipy. statsmodels and scikit-learn are development-only dependencies used as reference implementations that the tests compare against.

## Consequences

Deploys stay small. There is more code to own, which the oracle tests (and synthetic data with known answers) keep honest.
