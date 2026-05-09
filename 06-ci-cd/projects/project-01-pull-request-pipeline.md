# Project: Pull Request CI Pipeline

## Problem Statement

Create a CI pipeline that gives fast feedback on every pull request and blocks changes that fail linting, tests, or build checks.

## Deliverables

- GitHub Actions workflow or Jenkins pipeline
- At least one lint step
- At least one automated test step
- Build or packaging step
- Artifact upload or clear build output

## Validation

Capture evidence for one passing run and one failing run. The failing run should make the reason obvious from the pipeline logs.

## Failure Scenario

Intentionally break a test or lint rule. Document how the pipeline reports the failure and what command reproduces it locally.

## What to Commit

- Pipeline definition
- Minimal app or script under test
- Passing and failing run notes
- Local reproduction command

## Review Rubric

Use this rubric to self-assess your work or have a peer review it.

| Criteria | What to Look For | Score (1-5) |
|----------|-----------------|-------------|
| **Reproducibility** | Pipeline runs on a fresh fork without manual secret setup | |
| **Correctness** | Lint, test, and build stages pass on good code and fail on bad code | |
| **Debugging quality** | At least one intentional failure with clear diagnosis in the workflow log | |
| **Security basics** | Secrets use GitHub Secrets; workflow uses minimal permissions | |
| **Cleanup quality** | No leftover artifacts, containers, or cloud resources after pipeline runs | |
| **Explanation clarity** | Pipeline stages are documented with purpose and expected outcomes | |

**Scoring**: 1 = Not attempted, 2 = Partial, 3 = Meets expectations, 4 = Exceeds expectations, 5 = Production quality
