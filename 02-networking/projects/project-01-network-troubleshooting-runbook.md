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
