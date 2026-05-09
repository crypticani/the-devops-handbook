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

## Review Rubric

Use this rubric to self-assess your work or have a peer review it.

| Criteria | What to Look For | Score (1-5) |
|----------|-----------------|-------------|
| **Reproducibility** | Scan commands and tool versions are documented for reproducibility | |
| **Correctness** | Triage accurately assesses severity, exploitability, and impact | |
| **Debugging quality** | At least one finding is fixed with before/after evidence | |
| **Security basics** | Scan covers code, dependencies, images, and infrastructure configs | |
| **Cleanup quality** | Test repos and dummy secrets are removed after the exercise | |
| **Explanation clarity** | Triage report clearly explains each finding, decision, and rationale | |

**Scoring**: 1 = Not attempted, 2 = Partial, 3 = Meets expectations, 4 = Exceeds expectations, 5 = Production quality
