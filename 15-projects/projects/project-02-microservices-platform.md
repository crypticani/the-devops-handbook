# Project 02: Microservices Platform (Intermediate)

## Problem Statement

Deploy a multi-service application with a reverse proxy, centralized monitoring, and centralized logging. Demonstrate that you can operate, observe, and debug a distributed system.

## Requirements

### Application Stack
- **Frontend**: Static site or simple web UI served by Nginx
- **API**: A small REST API (Python Flask, Node Express, or Go) with at least 3 endpoints
- **Database**: PostgreSQL or MySQL for persistent data
- **Cache**: Redis for session or response caching
- **Reverse Proxy**: Nginx load balancing traffic to the API

### Observability Stack
- **Metrics**: Prometheus scraping application and infrastructure metrics
- **Dashboards**: Grafana with at least one custom dashboard (4+ panels)
- **Logging**: Loki + Promtail (or ELK) collecting logs from all services
- **Alerting**: At least one alert rule (e.g., API error rate > 5%)

### Infrastructure
- All services run via Docker Compose
- Health checks defined for every service
- Environment variables for configuration (no hardcoded values)
- `.env.example` file documenting required variables

### Documentation
- Architecture diagram showing all services and connections
- Setup instructions that work from `docker compose up`
- Troubleshooting guide with at least 3 real issues you encountered

## Deliverables

- Git repository with all source code, configs, and Compose files
- Architecture diagram
- Grafana dashboard screenshot or JSON export
- Log query demonstrating a debugging workflow
- Alert rule definition and evidence of it firing
- Troubleshooting guide

## Validation

- `docker compose up` brings the full stack online
- Frontend can reach the API through the reverse proxy
- API reads/writes to the database correctly
- Redis cache reduces response time on repeated requests
- Prometheus scrapes metrics from all instrumented targets
- Grafana dashboard shows live data
- Loki/ELK contains logs from all services
- At least one alert fires when a failure condition is simulated

## Failure Scenario

Simulate and document at least two of these scenarios:

1. **Database crash**: Stop the database container. How does the API respond? What do the logs show? How do metrics reflect the failure? Restart and verify recovery.
2. **API memory leak**: Set a very low memory limit on the API container. Generate traffic until it OOM-kills. Document the symptoms in metrics and logs.
3. **Cache failure**: Stop Redis. Does the API degrade gracefully or crash? Implement a fallback path.
4. **Traffic spike**: Use `hey` or `ab` to send 1000 concurrent requests. Observe latency, error rates, and resource utilization in Grafana.

## What to Commit

- All source code, Dockerfiles, Compose files, and configs
- Prometheus and Grafana configuration files
- Dashboard JSON export
- Troubleshooting guide with real issues and fixes
- Failure scenario documentation with evidence

## Review Rubric

Use this rubric to self-assess your work or have a peer review it.

| Criteria | What to Look For | Score (1-5) |
|----------|-----------------|-------------|
| **Reproducibility** | Full stack starts from `docker compose up` without manual setup | |
| **Correctness** | All services communicate correctly; data flows end to end | |
| **Debugging quality** | Failure scenarios are documented with metrics/logs evidence | |
| **Security basics** | No secrets in code; non-root containers; no default passwords | |
| **Cleanup quality** | `docker compose down -v` removes all resources cleanly | |
| **Explanation clarity** | Architecture and debugging docs are clear and complete | |

**Scoring**: 1 = Not attempted, 2 = Partial, 3 = Meets expectations, 4 = Exceeds expectations, 5 = Production quality
