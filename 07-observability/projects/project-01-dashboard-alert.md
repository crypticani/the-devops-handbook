# Project: Metrics Dashboard and Alert

## Problem Statement

Build a small monitoring setup that scrapes an application or service, visualizes key metrics, and fires one useful alert.

## Deliverables

- Prometheus scrape configuration
- Grafana dashboard or exported dashboard JSON
- Alert rule with threshold and explanation
- Short incident note explaining how the alert should be handled

## Validation

Capture evidence that:

- Prometheus can reach the target
- Metrics are being scraped
- Dashboard panels show live data
- Alert can move to firing state during a simulated problem

## Failure Scenario

Stop the monitored service or make the health metric fail. Document the alert behavior, dashboard signal, and recovery.

## Cleanup

Stop containers or services used for the monitoring stack.

## What to Commit

- Monitoring config
- Dashboard export or dashboard notes
- Alert rule
- Incident note

## Review Rubric

Use this rubric to self-assess your work or have a peer review it.

| Criteria | What to Look For | Score (1-5) |
|----------|-----------------|-------------|
| **Reproducibility** | Dashboard JSON and alert rules can be imported into a fresh Grafana instance | |
| **Correctness** | Metrics are accurate; alert fires on the documented threshold condition | |
| **Debugging quality** | Dashboard includes panels that help diagnose root cause, not just symptoms | |
| **Security basics** | No credentials in Prometheus configs; Grafana uses non-default password | |
| **Cleanup quality** | Docker Compose stack tears down cleanly with no orphan volumes | |
| **Explanation clarity** | Each dashboard panel has a title and description explaining its purpose | |

**Scoring**: 1 = Not attempted, 2 = Partial, 3 = Meets expectations, 4 = Exceeds expectations, 5 = Production quality
