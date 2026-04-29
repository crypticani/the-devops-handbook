# Module 13: Security Basics

> *"Security is not a feature — it's a property of the entire system." — DevSecOps Principle*

---

## 🎯 Why This Module Matters

A single misconfigured S3 bucket, a leaked secret in git, or an unpatched container image can end careers and companies. Security in DevOps is **not a bolt-on** — it's embedded in every tool and workflow you've learned so far. This module consolidates security practices across the entire stack.

**In real-world DevOps work**, you will:
- Manage secrets securely across CI/CD, containers, and cloud
- Harden Linux servers and SSH configurations
- Scan container images for vulnerabilities
- Implement RBAC in Kubernetes and cloud platforms
- Integrate security scanning into CI/CD pipelines (DevSecOps)
- Respond to security incidents methodically

---

## 📚 Table of Contents

1. [DevSecOps — Security as Culture](#1-devsecops--security-as-culture)
2. [Secrets Management](#2-secrets-management)
3. [Linux Security Hardening](#3-linux-security-hardening)
4. [Container Security](#4-container-security)
5. [CI/CD Pipeline Security](#5-cicd-pipeline-security)
6. [Cloud Security (IAM & Network)](#6-cloud-security-iam--network)
7. [Kubernetes Security](#7-kubernetes-security)
8. [Vulnerability Management](#8-vulnerability-management)
9. [Common Mistakes and Anti-Patterns](#9-common-mistakes-and-anti-patterns)
10. [Incident Response](#10-incident-response)
11. [Interview Insights](#11-interview-insights)

---

## 1. DevSecOps — Security as Culture

### Shift Left

```
TRADITIONAL:
  Code → Build → Test → Deploy → THEN security review
  Security finds issues after everything is built → expensive to fix

SHIFT LEFT (DevSecOps):
  Code (lint+SAST) → Build (image scan) → Test (DAST) → Deploy (runtime)
  Security at EVERY stage → issues caught early → cheap to fix

┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐
│ Code │──▶│Build │──▶│ Test │──▶│Stage │──▶│ Prod │
│ SAST │   │Image │   │ DAST │   │Scan  │   │WAF   │
│ Lint │   │ Scan │   │Pentest│  │Audit │   │SIEM  │
└──────┘   └──────┘   └──────┘   └──────┘   └──────┘
   ▲ Security integrated at every stage
```

### Security Scanning Types

```
SAST — Static Application Security Testing
  Scans SOURCE CODE for vulnerabilities (before running)
  Tools: SonarQube, Semgrep, Bandit (Python), ESLint security

DAST — Dynamic Application Security Testing
  Scans the RUNNING APPLICATION for vulnerabilities
  Tools: OWASP ZAP, Burp Suite, Nikto

SCA — Software Composition Analysis
  Scans DEPENDENCIES for known vulnerabilities (CVEs)
  Tools: Snyk, Dependabot, Trivy, OWASP Dependency-Check

IaC Scanning
  Scans TERRAFORM/K8S configs for misconfigurations
  Tools: Checkov, tfsec, Kube-bench
```

---

## 2. Secrets Management

### The Golden Rules

```
1. NEVER commit secrets to git (even in private repos)
2. NEVER hardcode secrets in code, Dockerfiles, or configs
3. NEVER pass secrets as command-line arguments (visible in ps)
4. NEVER log secrets (even accidentally in debug mode)
5. ALWAYS rotate secrets regularly
6. ALWAYS use the platform's secret store
7. ALWAYS encrypt secrets at rest and in transit
```

### Where to Store Secrets

| Context | Tool | How |
|---------|------|-----|
| **Git/CI** | GitHub Secrets | Settings → Secrets → Actions |
| **Docker** | Docker Secrets / env files | NOT in Dockerfile |
| **Kubernetes** | K8s Secrets + External Secrets Operator | Synced from Vault |
| **Cloud** | AWS Secrets Manager / SSM Parameter Store | IAM-controlled access |
| **Central** | HashiCorp Vault | API-based, dynamic secrets, audit log |
| **Ansible** | Ansible Vault | Encrypted variable files |
| **Terraform** | Never in .tf files | Use data sources to fetch from SSM/Vault |

### Preventing Secret Leaks in Git

```bash
# .gitignore — always include these
*.env
.env.*
*.pem
*.key
*secret*
terraform.tfstate*
.terraform/

# Pre-commit hook to scan for secrets
# Install: pip install pre-commit
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']

  - repo: https://github.com/zricethezav/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
```

### What If a Secret Is Leaked?

```
SECRET LEAKED TO GIT?
│
├─ 1. ROTATE IMMEDIATELY — generate new credentials
│     └─ The old secret is compromised forever (git history)
│
├─ 2. REVOKE the old secret in the provider
│     └─ AWS: deactivate access key, GitHub: revoke token
│
├─ 3. SCAN for unauthorized usage
│     └─ CloudTrail logs, API access logs
│
├─ 4. REMOVE from git history
│     └─ git filter-branch or BFG Repo-Cleaner
│     └─ ⚠️ This is a force-push — coordinate with team
│
└─ 5. ADD prevention
      └─ Pre-commit hooks, CI secret scanning
```

---

## 3. Linux Security Hardening

### SSH Hardening

```bash
# /etc/ssh/sshd_config — Critical settings
PermitRootLogin no               # Never SSH as root
PasswordAuthentication no         # Keys only, no passwords
PubkeyAuthentication yes
MaxAuthTries 3                    # Lock after 3 failed attempts
AllowUsers deployer admin         # Whitelist specific users
Protocol 2                       # Only SSH v2
ClientAliveInterval 300           # Timeout idle connections
ClientAliveCountMax 2

# After changes:
sudo systemctl restart sshd
```

### User and Permission Management

```bash
# Principle of least privilege
sudo useradd -m -s /bin/bash deployer
sudo usermod -aG sudo deployer         # Only if needed

# Restrict sudo
# /etc/sudoers.d/deployer
deployer ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
# Can ONLY restart nginx with sudo — nothing else

# File permissions
chmod 700 ~/.ssh                       # Owner only
chmod 600 ~/.ssh/authorized_keys       # Owner only
chmod 644 ~/.ssh/id_rsa.pub           # Public key — readable
chmod 600 ~/.ssh/id_rsa               # Private key — OWNER ONLY
```

### Firewall Basics

```bash
# UFW (Uncomplicated Firewall) — Ubuntu
sudo ufw default deny incoming         # Block all incoming
sudo ufw default allow outgoing        # Allow all outgoing
sudo ufw allow 22/tcp                  # Allow SSH
sudo ufw allow 80/tcp                  # Allow HTTP
sudo ufw allow 443/tcp                # Allow HTTPS
sudo ufw enable

# Check status
sudo ufw status verbose

# iptables equivalent
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -P INPUT DROP
```

### System Updates

```bash
# Enable unattended security updates (Ubuntu)
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Manual: update regularly
sudo apt update && sudo apt upgrade -y

# Check for known vulnerabilities
sudo apt install lynis
sudo lynis audit system
```

---

## 4. Container Security

### Dockerfile Best Practices

```dockerfile
# BAD: Running as root, fat image, secrets baked in
FROM ubuntu:latest
RUN apt-get update && apt-get install -y python3 curl wget vim
COPY . /app
ENV API_KEY=sk-secret-12345
CMD ["python3", "/app/app.py"]

# GOOD: Non-root, minimal image, no secrets, pinned version
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY src/ ./src/
RUN useradd -r -s /sbin/nologin appuser
USER appuser
EXPOSE 8080
CMD ["python3", "-m", "src.app"]
```

### Container Security Checklist

```
✅ Use minimal base images (alpine, slim, distroless)
✅ Pin image versions (python:3.12-slim, NOT python:latest)
✅ Run as non-root user (USER appuser)
✅ Use multi-stage builds (smaller attack surface)
✅ Don't install unnecessary packages (no vim, curl in prod)
✅ Scan images for CVEs (Trivy, Snyk, Docker Scout)
✅ Use read-only filesystem where possible
✅ Don't store secrets in images
✅ Sign images (Docker Content Trust, cosign)
```

### Image Scanning with Trivy

```bash
# Install Trivy
sudo apt install trivy  # or: brew install trivy

# Scan an image
trivy image nginx:1.25
trivy image myapp:latest

# Scan with severity filter
trivy image --severity HIGH,CRITICAL myapp:latest

# Scan in CI pipeline (fail on critical)
trivy image --exit-code 1 --severity CRITICAL myapp:latest

# Scan a Dockerfile
trivy config Dockerfile

# Scan Kubernetes manifests
trivy config k8s/

# Scan Terraform files
trivy config terraform/
```

---

## 5. CI/CD Pipeline Security

### Secure Pipeline Pattern

```yaml
# .github/workflows/secure-ci.yml
name: Secure CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read                    # Minimal permissions!
  security-events: write

jobs:
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0            # Full history for secret scanning
      - name: Scan for secrets
        uses: gitleaks/gitleaks-action@v2

  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: p/security-audit

  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Trivy on dependencies
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'HIGH,CRITICAL'

  image-scan:
    runs-on: ubuntu-latest
    needs: [secret-scan, sast]
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .
      - name: Scan image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'myapp:${{ github.sha }}'
          severity: 'HIGH,CRITICAL'
          exit-code: '1'            # Fail pipeline on critical CVE
```

### CI/CD Security Checklist

```
✅ Pin action versions (SHA, not @main)
✅ Use minimal permissions (permissions: contents: read)
✅ Scan for secrets in every PR
✅ Scan dependencies for CVEs
✅ Scan container images before pushing
✅ Use OIDC for cloud authentication (not static keys)
✅ Require branch protection (CI must pass before merge)
✅ Sign artifacts (images, binaries)
```

---

## 6. Cloud Security (IAM & Network)

### IAM Security Summary

```
PRINCIPLE OF LEAST PRIVILEGE:
  ┌────────────────────────────────────────────┐
  │ "Grant the minimum access needed to do     │
  │  the job. Nothing more."                   │
  │                                            │
  │ ❌ Admin access for developers             │
  │ ❌ Wildcard (*) permissions                │
  │ ❌ Long-lived access keys                  │
  │                                            │
  │ ✅ Specific actions on specific resources  │
  │ ✅ IAM roles for services (not keys)       │
  │ ✅ MFA on all human accounts               │
  │ ✅ Regular access reviews                  │
  └────────────────────────────────────────────┘
```

### Network Security Layers

```
                    Internet
                       │
                 ┌─────▼─────┐
                 │    WAF     │  Layer 7 (application firewall)
                 └─────┬─────┘
                 ┌─────▼─────┐
                 │   NACLs   │  Subnet-level firewall (stateless)
                 └─────┬─────┘
                 ┌─────▼─────┐
                 │  Security  │  Instance-level firewall (stateful)
                 │   Groups   │
                 └─────┬─────┘
                 ┌─────▼─────┐
                 │   App     │  Your application
                 └───────────┘

DEFENSE IN DEPTH — multiple layers, each with its own rules
```

---

## 7. Kubernetes Security

### Pod Security

```yaml
# Secure pod configuration
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
spec:
  securityContext:
    runAsNonRoot: true              # Container must run as non-root
    runAsUser: 1000
    fsGroup: 2000
  containers:
    - name: app
      image: myapp:v1.2.3
      securityContext:
        allowPrivilegeEscalation: false  # Can't become root
        readOnlyRootFilesystem: true     # Filesystem is read-only
        capabilities:
          drop:
            - ALL                        # Drop all Linux capabilities
      resources:
        limits:
          memory: "256Mi"
          cpu: "500m"
```

### RBAC — Role-Based Access Control

```yaml
# Role: what permissions
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: production
  name: app-deployer
rules:
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "update", "patch"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list"]
---
# RoleBinding: who gets the permissions
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  namespace: production
  name: deploy-binding
subjects:
  - kind: User
    name: deploy-bot
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: app-deployer
  apiGroup: rbac.authorization.k8s.io
```

### Network Policies

```yaml
# Only allow traffic from the frontend to the API
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-allow-frontend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
```

---

## 8. Vulnerability Management

### CVE Lifecycle

```
CVE DISCLOSED → ASSESS IMPACT → PATCH → VERIFY → MONITOR

For each CVE:
1. Is it in our stack? (image scan, dependency scan)
2. Is it exploitable in our context?
3. What's the severity? (Critical → patch now, Low → next cycle)
4. Patch and redeploy
5. Verify the fix
```

### Vulnerability Scanning Pipeline

```
CODE         → SAST (Semgrep, SonarQube)
DEPENDENCIES → SCA (Snyk, Dependabot, Trivy fs)
DOCKER IMAGE → Image scan (Trivy, Docker Scout)
IaC FILES    → Config scan (Checkov, tfsec)
K8S CLUSTER  → Runtime scan (Kube-bench, Falco)
```

---

## 9. Common Mistakes and Anti-Patterns

### ❌ Security as an Afterthought

```
BAD:  Build everything → then "add security" before launch
GOOD: Security at every stage — code review, CI scanning, runtime monitoring
```

### ❌ Over-Permissive IAM

```json
// BAD: God mode — can do anything to everything
{ "Effect": "Allow", "Action": "*", "Resource": "*" }

// GOOD: Specific actions on specific resources
{ "Effect": "Allow", "Action": ["s3:GetObject"], "Resource": ["arn:aws:s3:::my-bucket/*"] }
```

### ❌ Running as Root

```
BAD:  Containers running as root → one exploit = full control
GOOD: USER appuser in Dockerfile, runAsNonRoot in K8s
```

### ❌ Ignoring Dependency Updates

```
BAD:  "It works, don't touch it" → 2-year-old dependencies with 50 CVEs
GOOD: Dependabot/Renovate auto-PRs, regular update cycles
```

---

## 10. Incident Response

### When Something Goes Wrong

```
INCIDENT DETECTED!
│
├─ 1. CONTAIN — Stop the bleeding
│     ├─ Revoke compromised credentials
│     ├─ Isolate affected systems (security group)
│     └─ Block malicious IPs (WAF/firewall)
│
├─ 2. ASSESS — Understand the scope
│     ├─ What was accessed? (CloudTrail, access logs)
│     ├─ What data was exposed? (PII, credentials?)
│     └─ How did they get in? (vulnerability, credential leak?)
│
├─ 3. REMEDIATE — Fix the root cause
│     ├─ Patch the vulnerability
│     ├─ Rotate ALL potentially compromised secrets
│     └─ Update affected systems
│
├─ 4. RECOVER — Return to normal
│     ├─ Restore from clean backups if needed
│     ├─ Verify systems are clean
│     └─ Re-enable access
│
└─ 5. LEARN — Prevent recurrence
      ├─ Post-incident review (blameless!)
      ├─ Update security controls
      └─ Share learnings with the team
```

---

## 11. Interview Insights

**Q: What is DevSecOps and what does "shift left" mean?**
> DevSecOps integrates security into every stage of the DevOps pipeline instead of treating it as a separate phase. "Shift left" means moving security earlier — scanning code for vulnerabilities during development and CI, not after deployment. This catches issues when they're cheapest to fix.

**Q: How do you manage secrets in a DevOps environment?**
> Never in code or git. Use platform-specific secret stores: GitHub Secrets for CI, AWS Secrets Manager or SSM for cloud, Kubernetes Secrets with external operators for K8s, and HashiCorp Vault for centralized management. Use pre-commit hooks (gitleaks) to prevent accidental commits. Rotate secrets regularly.

**Q: What would you do if you found a secret committed to a public repo?**
> Immediately rotate/revoke the secret — it's compromised. Check access logs (CloudTrail) for unauthorized usage. Remove from git history using BFG Repo-Cleaner. Add pre-commit hooks to prevent recurrence. Notify the team and document the incident.

**Q: How do you secure container images?**
> Use minimal base images (slim/distroless), run as non-root user, pin image versions, use multi-stage builds, scan with Trivy in CI (fail on critical CVEs), sign images, and don't store secrets in images. Enable read-only root filesystem in Kubernetes.

**Q: Explain the principle of least privilege with an example.**
> Grant only the minimum permissions needed. Example: An EC2 instance running a web app needs to read from one S3 bucket and write to CloudWatch. Its IAM role should allow only `s3:GetObject` on that specific bucket and `logs:PutLogEvents` — nothing else. If compromised, the blast radius is limited to those specific resources.

**Q: How do you implement RBAC in Kubernetes?**
> Create Roles defining permissions (which API resources, which verbs) and RoleBindings connecting users/service accounts to roles. Use namespaces to isolate teams. Follow least privilege — developers get read-only in production, deploy bots get update access to deployments only. Use ClusterRoles for cluster-wide permissions sparingly.

---

## ➡️ What's Next?

With security practices consolidated, you're ready to think at the system level — designing scalable, reliable architectures.

**[Module 14: System Design for DevOps →](../14-system-design-devops/)**

---

<div align="center">

**Module 13 Complete** ✅

[← Back to Kubernetes](../12-kubernetes/) | [Next: System Design →](../14-system-design-devops/)

</div>
