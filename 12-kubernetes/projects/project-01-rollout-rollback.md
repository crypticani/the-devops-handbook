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
