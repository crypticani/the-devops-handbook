# Project: Kubernetes Rollout and Rollback

## Problem Statement

Deploy a small application to Kubernetes, update it, intentionally break it, and recover with a rollback.

## Deliverables

- Deployment and Service manifests
- ConfigMap or Secret example
- Resource requests and limits
- Liveness and readiness probes
- Rollout and rollback notes

## Validation

Capture output for:

- `kubectl apply`
- `kubectl get pods`
- `kubectl describe deployment`
- `kubectl rollout status`
- Service access with `curl` or port-forward
- `kubectl rollout undo`

## Failure Scenario

Deploy a bad image tag or readiness probe. Use `kubectl describe`, events, and logs to identify the problem, then roll back.

## Cleanup

Delete the namespace or all resources created for the project.

## What to Commit

- Kubernetes manifests
- Validation output
- Failure and rollback notes
- Cleanup command output

## Review Rubric

Use this rubric to self-assess your work or have a peer review it.

| Criteria | What to Look For | Score (1-5) |
|----------|-----------------|-------------|
| **Reproducibility** | Manifests deploy successfully on a fresh minikube/kind cluster | |
| **Correctness** | Rolling update completes with zero downtime; rollback restores previous version | |
| **Debugging quality** | At least one failed deployment diagnosed with kubectl describe/logs | |
| **Security basics** | Pods run as non-root; secrets are used for sensitive config | |
| **Cleanup quality** | `kubectl delete` commands or namespace deletion cleans everything up | |
| **Explanation clarity** | Deployment strategy, update process, and rollback steps are documented | |

**Scoring**: 1 = Not attempted, 2 = Partial, 3 = Meets expectations, 4 = Exceeds expectations, 5 = Production quality
