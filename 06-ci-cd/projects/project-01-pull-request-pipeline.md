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
