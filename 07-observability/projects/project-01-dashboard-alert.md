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
