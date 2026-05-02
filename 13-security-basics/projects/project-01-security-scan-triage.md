# Project: Security Scan and Triage Report

## Problem Statement

Run security scans against a small application, container image, or infrastructure config. Triage the findings and document what you fixed, what remains, and why.

## Deliverables

- Scan command and tool version
- Raw or summarized scan output
- Triage table with severity, impact, fix, and owner
- Evidence for at least one fixed issue
- Residual-risk note for accepted findings

## Validation

Run the scan before and after a fix. Capture enough output to prove the finding changed or was intentionally accepted.

## Failure Scenario

Include one leaked dummy secret, vulnerable dependency, or insecure config in a safe test repo. Document how the scan detects it and how prevention should be added to CI.

## What to Commit

- Scan notes
- Triage report
- Fix evidence
- CI/prevention recommendation
