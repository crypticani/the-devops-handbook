# Project: DNS and HTTP Troubleshooting Runbook

## Problem Statement

Create a practical runbook for diagnosing why a user cannot reach a web service. The runbook should move from DNS to TCP connectivity to HTTP behavior and service logs.

## Deliverables

- Step-by-step troubleshooting flow
- Example commands using `dig`, `curl`, `ss`, `ip`, and Nginx logs
- Expected healthy output for each check
- Decision table for DNS failure, closed port, firewall block, proxy issue, and application error

## Validation

Run the checks against a working local or public test endpoint and capture the important output. Then intentionally break one layer, such as using a bad hostname or stopping Nginx, and show how the runbook identifies the fault.

## Failure Scenario

Document a case where DNS resolves correctly but HTTP still fails. Explain how you prove whether the issue is the port, reverse proxy, upstream app, or firewall.

## Cleanup

Stop any local services you started and remove temporary test configs.

## What to Commit

- `network-runbook.md`
- `healthy-output.md`
- `failure-investigation.md`

## Review Rubric

Use this rubric to self-assess your work or have a peer review it.

| Criteria | What to Look For | Score (1-5) |
|----------|-----------------|-------------|
| **Reproducibility** | Runbook commands work on standard Linux systems without custom tooling | |
| **Correctness** | Diagnostic steps follow a logical order (DNS → connectivity → application) | |
| **Debugging quality** | Each step includes expected vs failure output and next actions | |
| **Security basics** | Runbook notes firewall and ACL checks; no credentials in examples | |
| **Cleanup quality** | Any test services or temporary firewall rules are cleaned up | |
| **Explanation clarity** | A junior engineer could follow the runbook without prior context | |

**Scoring**: 1 = Not attempted, 2 = Partial, 3 = Meets expectations, 4 = Exceeds expectations, 5 = Production quality
