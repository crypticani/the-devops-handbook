# Practical Learning Guide

This repository already has strong topic coverage in Modules 00-13. To turn those modules into job-ready practice, use each module as a build-and-debug loop instead of a reading checklist.

## Learning Loop

For each completed module, complete the work in this order:

1. Read the module README for the mental model and vocabulary.
2. Run the labs exactly once to learn the happy path.
3. Repeat the lab from memory with notes closed.
4. Break one part on purpose and debug it with real commands.
5. Write a short runbook: symptoms, checks, root cause, fix, prevention.
6. Commit your work, screenshots, configs, scripts, and runbook to a portfolio repo.

You have learned a skill only when you can reproduce it, explain it, and recover when it fails.

## Evidence Checklist

Every completed lab or project should leave evidence behind:

- `README.md` with the problem, architecture, commands used, and tradeoffs
- Working config files, scripts, manifests, workflows, or Terraform code
- Validation output copied into a short `evidence.md`
- A `failure-notes.md` file with at least one broken scenario and the fix
- Cleanup instructions and cost notes for cloud resources

Avoid only collecting screenshots. Screenshots help, but reproducible files matter more.

## Practical Lab Rubric

Use this rubric to improve existing labs or evaluate your own work.

| Area | Minimum Standard | Strong Standard |
|------|------------------|-----------------|
| Setup | Lists required tools and versions | Includes local, WSL, and cloud alternatives |
| Task | Gives executable steps | Frames the task as a real operational scenario |
| Validation | Shows expected output | Includes commands that prove the system works |
| Debugging | Has one "Break It" section | Includes symptoms, investigation path, root cause, and rollback |
| Deliverable | Learner runs commands | Learner produces a script, config, runbook, dashboard, or pipeline |
| Cleanup | Removes local files | Includes cloud cost and resource cleanup checks |

## Module Deliverables

Use these deliverables to make the existing modules practical:

| Module | Practical Deliverable |
|--------|-----------------------|
| 00 Foundations | Delivery pipeline map and personal skill-gap plan |
| 01 Linux | Server health report script and incident checklist |
| 02 Networking | DNS/HTTP troubleshooting runbook and Nginx reverse proxy |
| 03 Git | Branching workflow demo with conflict resolution notes |
| 04 Scripting | Bash or Python automation script with tests or sample inputs |
| 05 Docker | Containerized app with Compose, healthchecks, and non-root user |
| 06 CI/CD | Pull request pipeline with lint, test, build, scan, and artifact upload |
| 07 Observability | Prometheus/Grafana dashboard with one actionable alert |
| 08 Logging | Centralized logs with a documented query-based investigation |
| 09 Cloud | Small cloud environment with IAM, network, and cost notes |
| 10 Terraform | Reproducible infrastructure with remote-state notes and destroy proof |
| 11 Ansible | Idempotent playbook with inventory, variables, and validation |
| 12 Kubernetes | Multi-service app with rollout, rollback, probes, and resource limits |
| 13 Security | Security scan report with fixes and accepted residual risks |

## Portfolio Standard

A portfolio project is ready to show when a reviewer can:

- Clone it and follow setup instructions without guessing
- See the application or infrastructure working locally or in a free-tier environment
- Run validation commands and compare expected results
- Read how failures are detected, debugged, and rolled back
- Understand what you would improve with more time

## Recommended Cadence

For a 10-15 hour week:

- 3-4 hours reading and note-taking
- 4-6 hours lab execution
- 2-3 hours breaking, debugging, and documenting
- 1-2 hours portfolio cleanup and review

Do not rush the debugging step. That is where most practical learning happens.
