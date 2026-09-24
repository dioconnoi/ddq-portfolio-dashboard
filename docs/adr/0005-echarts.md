# ADR 0005: Apache ECharts for charts

- Status: Accepted
- Date: 2026-09-24

## Context

The dashboard needs heatmaps (correlation), zoomable time series, fan charts (Monte Carlo) and a dark theme.

## Decision

Apache ECharts, imported as tree-shaken modules.

## Consequences

All required chart types work out of the box. The dependency is larger than Recharts but far smaller than a full Plotly bundle. Rejected: Plotly (bundle size) and Recharts (weak heatmap and fan-chart support).
