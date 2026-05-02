# Project: Containerized App with Compose and Healthcheck

## Problem Statement

Containerize a small web application and run it locally with Docker Compose. The app should be easy to build, validate, inspect, and stop.

## Deliverables

- Dockerfile using a pinned base image
- Non-root runtime user where the application supports it
- Compose file with service name, ports, environment, and healthcheck
- README with build, run, logs, and cleanup commands

## Validation

Capture output for:

- `docker compose build`
- `docker compose up -d`
- `docker compose ps`
- `curl` against the health endpoint
- `docker compose logs`

## Failure Scenario

Break the app port, healthcheck path, or required environment variable. Document the symptoms, the Docker commands used to diagnose it, and the fix.

## Cleanup

Run `docker compose down --volumes` if volumes were created.

## What to Commit

- Application source
- `Dockerfile`
- `compose.yml`
- Validation and failure notes
