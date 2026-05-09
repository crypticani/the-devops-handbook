# Project 03: Production Infrastructure (Advanced)

## Problem Statement

Design, provision, and manage a complete production-grade environment using Infrastructure as Code, container orchestration, configuration management, and full observability. This is the capstone project that integrates skills from every module in the handbook.

## Requirements

### Infrastructure (Terraform)
- VPC with public and private subnets across 2 availability zones
- Security groups following least privilege
- An EKS/K3s/minikube Kubernetes cluster (cloud or local)
- S3 bucket for Terraform state (remote backend)
- IAM roles for services (not user access keys)

### Configuration Management (Ansible)
- Playbook to bootstrap cluster nodes (if using self-managed K8s)
- Role for common security hardening (SSH, firewall, updates)
- Ansible Vault for any sensitive variables

### Application Deployment (Kubernetes)
- At least 2 microservices deployed as Kubernetes Deployments
- Services exposed via Kubernetes Services and Ingress
- ConfigMaps for non-sensitive configuration
- Kubernetes Secrets for sensitive configuration
- Resource limits and requests on all pods
- Readiness and liveness probes on all containers
- Horizontal Pod Autoscaler on at least one service
- Rolling update strategy with rollback evidence

### Observability
- Prometheus + Grafana for metrics (deployed in-cluster or external)
- Loki or EFK for centralized logging
- At least 2 custom dashboards (infrastructure + application)
- At least 2 alert rules with notification channel configured
- Evidence of using observability to debug a real issue

### CI/CD
- GitHub Actions pipeline that:
  - Runs tests
  - Builds and scans container images
  - Deploys to Kubernetes (kubectl apply or Helm)
  - Includes rollback on failure

### Security
- Container images scanned with Trivy
- No secrets in source code or git history
- RBAC configured in Kubernetes
- Network policies restricting pod-to-pod traffic
- Pod security contexts (non-root, read-only filesystem)

## Deliverables

- Git repository with Terraform, Ansible, Kubernetes, and CI/CD configs
- Architecture diagram showing all components and data flows
- Terraform plan output and apply evidence
- Kubernetes deployment evidence (kubectl get all)
- Grafana dashboard screenshots or JSON exports
- Security scan results
- CI/CD pipeline run evidence (passing and failing)
- Troubleshooting guide with at least 5 real issues

## Validation

- `terraform plan` shows the complete infrastructure
- `terraform apply` provisions all resources successfully
- Ansible playbook runs idempotently (second run = zero changes)
- All Kubernetes pods are Running and Ready
- Application is accessible through the Ingress
- Prometheus scrapes metrics from all targets
- Grafana dashboards show live data
- Alert rules are configured and functional
- CI/CD pipeline deploys a code change end-to-end
- `terraform destroy` tears everything down cleanly

## Failure Scenarios

Simulate and document at least three:

1. **Pod crash loop**: Deploy a misconfigured container. Use `kubectl describe` and `kubectl logs` to diagnose. Fix and redeploy.
2. **Failed deployment**: Push a broken image tag. Observe the rollout failure. Execute a rollback. Verify the previous version is restored.
3. **Node failure** (if multi-node): Cordon and drain a node. Observe pod rescheduling. Uncordon and verify rebalancing.
4. **Security incident**: Simulate a leaked secret. Rotate it, update Kubernetes Secrets, and redeploy without downtime.
5. **Resource exhaustion**: Set very low memory limits. Generate load. Observe OOM kills and HPA scaling in action.

## What to Commit

- All Terraform, Ansible, Kubernetes, and CI/CD configuration files
- Architecture diagram and design document
- `terraform plan` and `terraform apply` output summaries
- Grafana dashboard JSON exports
- Security scan results (Trivy, kube-bench)
- Troubleshooting guide with evidence of debugging
- Cost estimate for the cloud resources used

## Review Rubric

Use this rubric to self-assess your work or have a peer review it.

| Criteria | What to Look For | Score (1-5) |
|----------|-----------------|-------------|
| **Reproducibility** | Full stack can be provisioned from the repo with documented steps | |
| **Correctness** | All services deploy, communicate, and function as designed | |
| **Debugging quality** | 3+ failure scenarios documented with evidence and resolution | |
| **Security basics** | RBAC, network policies, image scanning, secrets management, non-root | |
| **Cleanup quality** | `terraform destroy` removes everything; no orphaned resources | |
| **Explanation clarity** | Architecture doc and troubleshooting guide are interview-ready | |

**Scoring**: 1 = Not attempted, 2 = Partial, 3 = Meets expectations, 4 = Exceeds expectations, 5 = Production quality
