# ADR 0007: ReportLab for PDF reports

- Status: Accepted
- Date: 2026-09-24

## Context

PDF export must fit a roughly 500 MB free instance and must not require system libraries.

## Decision

ReportLab with matplotlib-rendered charts, both pure pip installs (built in Phase 8).

## Consequences

Reports are laid out in code rather than HTML/CSS, and there is no Pango/Cairo install on Render. Rejected: WeasyPrint (needs system libraries).
