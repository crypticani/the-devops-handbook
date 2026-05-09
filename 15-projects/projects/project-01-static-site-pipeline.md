# Project 01: Static Site Pipeline (Beginner)

## Problem Statement

Build a containerized static website with an automated CI/CD pipeline that lints, builds, scans, and deploys on every push. This is the simplest end-to-end DevOps project, but it must be done with production-quality practices.

## Requirements

### Application
- A static website (HTML/CSS/JS) — can be a personal portfolio, landing page, or documentation site
- Served by Nginx in a Docker container
- Health check endpoint that returns 200

### Dockerfile
- Uses `nginx:alpine` (slim base image)
- Runs as non-root user
- Copies only static files (no source code, no build tools in final image)
- Pinned image version (not `:latest`)

### CI/CD Pipeline (GitHub Actions)
- **Lint**: Validate HTML (htmlhint or similar)
- **Build**: Build the Docker image with a unique tag (git SHA)
- **Scan**: Run Trivy on the built image, fail on CRITICAL CVEs
- **Test**: Start the container and verify the health endpoint responds
- **Push** (optional): Push to GitHub Container Registry or Docker Hub

### Documentation
- README with architecture diagram
- Setup instructions for running locally
- Cleanup instructions

## Deliverables

- Git repository with all source code, Dockerfile, and CI/CD workflow
- Screenshot or link to a passing CI/CD pipeline run
- Trivy scan output showing no critical vulnerabilities
- Evidence of the health check working (curl output)
- Architecture diagram showing the build → test → deploy flow

## Validation

- `docker compose up` brings the site up on localhost
- CI pipeline passes on a clean push
- Trivy scan runs and reports results
- Health endpoint returns 200
- Container runs as non-root (verify with `docker exec <id> whoami`)

## Failure Scenario

Introduce one of these failures and document how the pipeline catches it:
1. Add a `<script>alert('xss')</script>` tag and see if the linter flags it
2. Switch to an image with known CRITICAL CVEs and see Trivy fail the pipeline
3. Break the Nginx config so the container starts but returns 500 on the health check

## What to Commit

- All source files, Dockerfile, docker-compose.yml, and GitHub Actions workflow
- Screenshot of passing and failing pipeline runs
- Trivy scan summary
- Troubleshooting notes from at least one issue you encountered

## Review Rubric

Use this rubric to self-assess your work or have a peer review it.

| Criteria | What to Look For | Score (1-5) |
|----------|-----------------|-------------|
| **Reproducibility** | `git clone` + `docker compose up` works on a fresh machine | |
| **Correctness** | Pipeline stages run in the right order; site serves correctly | |
| **Debugging quality** | At least one failure is intentionally introduced and caught | |
| **Security basics** | Non-root container, image scanning, no secrets in code | |
| **Cleanup quality** | `docker compose down` removes everything; clear teardown docs | |
| **Explanation clarity** | README explains architecture and technology choices | |

**Scoring**: 1 = Not attempted, 2 = Partial, 3 = Meets expectations, 4 = Exceeds expectations, 5 = Production quality
