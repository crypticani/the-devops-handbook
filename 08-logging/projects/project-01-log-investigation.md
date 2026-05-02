# Project: Centralized Logging Investigation

## Problem Statement

Collect application or container logs into a logging stack and use queries to investigate a realistic failure.

## Deliverables

- Logging stack configuration
- Application or sample logs
- Queries that find errors, slow requests, or suspicious events
- Investigation report with timeline, impact, root cause, and fix

## Validation

Capture evidence that logs are flowing into the stack and that your queries return the expected events.

## Failure Scenario

Generate repeated 500 errors, failed logins, or bad requests. Use log queries to identify when the issue started and which component produced it.

## Cleanup

Stop the logging stack and remove temporary volumes if they are not needed.

## What to Commit

- Logging config
- Query examples
- Investigation report
- Cleanup notes
