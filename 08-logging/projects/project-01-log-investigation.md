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

## Review Rubric

Use this rubric to self-assess your work or have a peer review it.

| Criteria | What to Look For | Score (1-5) |
|----------|-----------------|-------------|
| **Reproducibility** | Log stack and sample data can be recreated from provided configs | |
| **Correctness** | Queries return expected results; investigation conclusions match the evidence | |
| **Debugging quality** | Investigation follows a logical trail from symptom to root cause | |
| **Security basics** | No sensitive data in sample logs; access controls mentioned | |
| **Cleanup quality** | ELK/Loki stack tears down cleanly; no leftover indices or volumes | |
| **Explanation clarity** | Investigation report is structured with timeline, evidence, and conclusions | |

**Scoring**: 1 = Not attempted, 2 = Partial, 3 = Meets expectations, 4 = Exceeds expectations, 5 = Production quality
