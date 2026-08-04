# Lab 01: Security Scanning — Trivy, gitleaks, and Secure CI/CD

## 🎯 Objective

Integrate security scanning into your DevOps workflow. You'll scan container images for CVEs, detect secrets in git repos, write a secure Dockerfile, and build a CI pipeline with security gates.

---

## 📋 Prerequisites

- Docker installed
- Git repository (local or GitHub)
- Completed Module 05 (Docker) and Module 06 (CI/CD)

---

## 📦 Deliverables and Evidence

By the end of this lab, keep the following evidence in your notes or portfolio repo:

- Commands you ran and the important output you used for validation
- Any files, scripts, configs, manifests, or workflows you created
- A short failure note describing one thing that broke, how you diagnosed it, and how you fixed it
- Cleanup commands or confirmation that no long-running resources remain

Treat the validation section as the minimum proof that the lab worked.

---

## 🔬 Exercise 1: Scan Container Images with Trivy

### Step 1: Install Trivy

```bash
# Debian/Ubuntu
sudo apt-get install wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main | sudo tee /etc/apt/sources.list.d/trivy.list
sudo apt-get update && sudo apt-get install trivy

# RHEL-compatible
sudo tee /etc/yum.repos.d/trivy.repo << 'REPO'
[trivy]
name=Trivy repository
baseurl=https://aquasecurity.github.io/trivy-repo/rpm/releases/$releasever/$basearch/
gpgcheck=0
enabled=1
REPO
sudo dnf install -y trivy

# Or via Docker (no install needed)
alias trivy="docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest"
```

### Step 2: Scan a Popular Image

```bash
# Scan nginx — see what vulnerabilities exist
trivy image nginx:latest

# Filter by severity
trivy image --severity HIGH,CRITICAL nginx:latest

# Scan a slim image — compare the results
trivy image nginx:1.25-alpine
```

**Questions to consider:**
- How many HIGH/CRITICAL CVEs does `nginx:latest` have vs `nginx:1.25-alpine`?
- Why do minimal base images have fewer vulnerabilities?

### Step 3: Build and Scan Your Own Image

```bash
mkdir -p trivy-lab && cd trivy-lab

# Insecure Dockerfile
cat > Dockerfile.bad << 'DOCKERFILE'
FROM ubuntu:latest
RUN apt-get update && apt-get install -y python3 curl wget vim
COPY app.py /app/
ENV API_KEY=sk-secret-12345
USER root
CMD ["python3", "/app/app.py"]
DOCKERFILE

# Secure Dockerfile
cat > Dockerfile.good << 'DOCKERFILE'
FROM python:3.12-slim
WORKDIR /app
COPY app.py .
RUN useradd -r -s /sbin/nologin appuser
USER appuser
CMD ["python3", "app.py"]
DOCKERFILE

echo 'print("Hello, World!")' > app.py

# Build both
docker build -t myapp:insecure -f Dockerfile.bad .
docker build -t myapp:secure -f Dockerfile.good .

# Scan both — compare results
echo "=== INSECURE IMAGE ==="
trivy image --severity HIGH,CRITICAL myapp:insecure

echo "=== SECURE IMAGE ==="
trivy image --severity HIGH,CRITICAL myapp:secure
```

**✅ Checkpoint:** The secure image should have significantly fewer CVEs than the insecure one.

---

## 🔬 Exercise 2: Detect Secrets with gitleaks

### Step 1: Install gitleaks

```bash
# Linux
wget https://github.com/gitleaks/gitleaks/releases/download/v8.18.0/gitleaks_8.18.0_linux_x64.tar.gz
tar -xzf gitleaks_8.18.0_linux_x64.tar.gz
sudo mv gitleaks /usr/local/bin/

# Verify
gitleaks version
```

### Step 2: Create a Repo with Secrets

```bash
mkdir -p secret-test && cd secret-test
git init

# Simulate accidental secret commits
cat > config.py << 'CODE'
# Database config
DB_HOST = "db.example.com"
DB_USER = "admin"
DB_PASS = "SuperSecret123!"

# AWS credentials
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# API token
GITHUB_TOKEN = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef"
CODE

git add . && git commit -m "add config"

# Scan the repo
gitleaks detect -v
```

You should see gitleaks flagging the AWS keys and GitHub token.

### Step 3: Fix and Prevent

```bash
# Remove secrets from code
cat > config.py << 'CODE'
import os

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
CODE

# Add .gitignore
cat > .gitignore << 'GI'
.env
*.pem
*.key
GI

git add . && git commit -m "fix: remove hardcoded secrets"

# Scan again — the old commit still has secrets!
gitleaks detect -v
# gitleaks scans ALL history — secrets in old commits are still found
```

**✅ Checkpoint:** gitleaks detects secrets in git history even after removal from current code.

---

## 🔬 Exercise 3: Scan IaC and Kubernetes Configs

```bash
mkdir -p iac-scan && cd iac-scan

# Create an insecure Terraform config
cat > main.tf << 'HCL'
resource "aws_security_group" "bad" {
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]    # Open to the world!
  }
}

resource "aws_s3_bucket" "bad" {
  bucket = "my-public-bucket"
  acl    = "public-read"            # Public bucket!
}
HCL

# Create an insecure K8s manifest
cat > pod.yml << 'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: insecure-pod
spec:
  containers:
    - name: app
      image: myapp:latest
      securityContext:
        privileged: true            # Full host access!
        runAsUser: 0                # Running as root!
YAML

# Scan with Trivy
trivy config .

# You should see misconfigurations flagged:
# - Security group open to 0.0.0.0/0
# - S3 bucket with public access
# - Pod running as root with privileged mode
```

**✅ Checkpoint:** Trivy catches infrastructure and K8s misconfigurations before they reach production.

---

## 🧨 Break It: Four Ways Security Scanning Gives False Confidence

You now have three scanners producing green output. Every scenario below produces **green output on genuinely vulnerable systems** — which is worse than no scanning, because it manufactures confidence.

### Scenario 1: The Scanner That Passes an Exploitable Image

**Break it:**

```bash
mkdir -p ~/security-lab/false-negative && cd ~/security-lab/false-negative

cat > Dockerfile <<'EOF'
FROM alpine:3.19
RUN apk add --no-cache curl
# Install a dependency OUTSIDE the package manager — the way real apps do it
RUN mkdir -p /app/vendor && \
    echo 'log4j-core-2.14.1.jar (vulnerable to CVE-2021-44228)' > /app/vendor/log4j-core-2.14.1.jar && \
    echo 'requests==2.6.0' > /app/requirements.txt
COPY . /app
CMD ["sleep", "3600"]
EOF

docker build -q -t false-negative:v1 . && trivy image --severity HIGH,CRITICAL false-negative:v1
```

**Symptom:** Trivy reports **zero HIGH/CRITICAL** findings, or only a handful of base-OS CVEs. The Log4Shell-era jar and the ancient `requests` pin are invisible.

**Investigate:**

```bash
# ⭐ What did the scanner actually look at?
trivy image --list-all-pkgs false-negative:v1 | head -20
# Only apk packages. It never opened /app.

# Force it to look at application dependencies too
trivy image --scanners vuln,secret,misconfig --detection-priority comprehensive false-negative:v1

# Generate an SBOM and see what's really in there
syft false-negative:v1 -o table 2>/dev/null | head -20
```

**Root cause:** Scanners detect what they can **identify**. They parse OS package databases (`apk`, `apt`, `rpm`) and recognised lockfiles (`package-lock.json`, `requirements.txt`, `go.sum`, `Gemfile.lock`). A jar copied in by hand, a binary downloaded with `curl`, a vendored directory, or a statically-linked Go binary is just bytes to them.

**Fix:**

```bash
# 1. Commit real lockfiles so the scanner has something to parse
# 2. Scan the SOURCE tree, not only the image — it sees manifests the image lost
trivy fs --scanners vuln,secret,misconfig .

# 3. Generate and retain an SBOM per build; scan the SBOM as new CVEs are published
syft false-negative:v1 -o spdx-json > sbom.json
trivy sbom sbom.json

# 4. Cross-check with a second scanner — they have different databases
grype false-negative:v1
```

> ⭐ **A clean scan means "no *known* vulnerabilities in *recognised* components."** It does not mean secure. Ask what fraction of your dependency tree the scanner could actually see.

---

### Scenario 2: The `.trivyignore` That Became Permanent

**Break it:**

```bash
cd ~/security-lab
cat > .trivyignore <<'EOF'
CVE-2023-45853
CVE-2024-2511
CVE-2023-6237
EOF

trivy image --severity HIGH,CRITICAL --exit-code 1 python:3.9-slim ; echo "exit=$?"
```

**Symptom:** The gate passes. The ignore file has no reasons, no owners, and no expiry — nobody remembers whether these were assessed or just silenced to make a red build green at 5pm on a Friday.

**Investigate:**

```bash
# ⭐ What is this file actually hiding right now?
trivy image --severity HIGH,CRITICAL --ignorefile /dev/null python:3.9-slim | head -30

# Compare the counts
suppressed=$(trivy image -q -f json --ignorefile /dev/null python:3.9-slim | jq '[.Results[].Vulnerabilities[]? | select(.Severity=="CRITICAL" or .Severity=="HIGH")] | length')
visible=$(trivy image -q -f json python:3.9-slim | jq '[.Results[].Vulnerabilities[]? | select(.Severity=="CRITICAL" or .Severity=="HIGH")] | length')
echo "visible=$visible  actual=$suppressed  suppressed=$((suppressed - visible))"

# Who added these, and when?
git log -p --follow .trivyignore 2>/dev/null | head -40
```

**Root cause:** Suppression is necessary — not every CVE is reachable or fixable today. But a bare CVE ID carries no decision, so the accepted risk becomes invisible and permanent. Three years later nobody dares remove a line because nobody knows why it's there.

**Fix — every suppression is a dated, owned, reviewable decision:**

```yaml
# .trivyignore.yaml — the structured format, with built-in expiry ⭐
vulnerabilities:
  - id: CVE-2023-45853
    statement: |
      zlib MiniZip. We never call MiniZip — the vulnerable code path is not
      reachable from our entrypoint (verified by grep + call-graph review).
      Accepted by @alice, security review 2026-08-04.
    expired_at: 2026-11-04        # ⭐ the finding REAPPEARS after this date

  - id: CVE-2024-2511
    statement: |
      OpenSSL TLS session cache DoS. Our service sits behind an ALB that
      terminates TLS; the container never handles untrusted TLS handshakes.
      Accepted by @bob 2026-08-04, re-review 2026-11-04.
    expired_at: 2026-11-04
```

```bash
# CI: fail if any suppression is missing a justification or an expiry date
python3 - <<'EOF'
import sys, yaml, datetime, pathlib
p = pathlib.Path(".trivyignore.yaml")
if not p.exists(): sys.exit(0)
data = yaml.safe_load(p.read_text()) or {}
bad = []
for v in data.get("vulnerabilities", []):
    if not v.get("statement", "").strip(): bad.append(f'{v["id"]}: no justification')
    if not v.get("expired_at"):            bad.append(f'{v["id"]}: no expiry date')
if bad:
    print("❌ invalid suppressions:"); [print("  ", b) for b in bad]; sys.exit(1)
print("✅ all suppressions justified and dated")
EOF
```

---

### Scenario 3: Rotation Is the Fix — Purging History Is Not

**Break it:**

```bash
mkdir -p ~/security-lab/leak && cd ~/security-lab/leak
git init -q

cat > config.py <<'EOF'
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
EOF
git add -A && git commit -qm "add config"

# "Fix" it the way most people first try
cat > config.py <<'EOF'
import os
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
EOF
git add -A && git commit -qm "fix: use environment variables for credentials"

gitleaks detect --source . --no-banner ; echo "exit=$?"
```

**Symptom:** gitleaks still finds it — because the secret is in commit 1 forever. But here's the part that matters: even after you purge history, **the credential is still valid**.

**Investigate:**

```bash
git log --oneline
git show HEAD~1:config.py           # ⭐ still fully readable
git rev-list --all --objects | git cat-file --batch-check='%(objecttype) %(objectname)' | grep blob | wc -l
```

**Root cause:** Git is append-only. A "fix" commit adds a new version; it does not remove the old one. And history rewriting — the step people focus on — is **cleanup, not remediation**. By the time a secret reaches a remote it must be assumed compromised: automated scanners crawl public GitHub within seconds of a push, and forks, clones, CI caches, and GitHub's own cached views all keep copies you cannot reach.

**Fix — in this order, and the order is the entire lesson:**

```bash
# ── 1. ROTATE. First. Before anything else. ────────────────────────────
aws iam update-access-key --user-name svc-app --access-key-id AKIA... --status Inactive
aws iam create-access-key --user-name svc-app          # issue the replacement
# deploy the new value, verify the app works, then:
aws iam delete-access-key --user-name svc-app --access-key-id AKIA...

# ── 2. CHECK FOR ABUSE ─────────────────────────────────────────────────
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=AKIA... \
  --max-results 50 --query 'Events[].{Time:EventTime,Name:EventName,Src:Username}' --output table

# ── 3. PURGE HISTORY (hygiene) ─────────────────────────────────────────
pip install -q git-filter-repo
printf 'AKIAIOSFODNN7EXAMPLE==>REDACTED\nwJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY==>REDACTED\n' > replacements.txt
git filter-repo --replace-text replacements.txt --force
gitleaks detect --source . --no-banner ; echo "exit=$?"    # now clean

# ── 4. FORCE-PUSH, tell every collaborator to re-clone,
#      and ask GitHub Support to purge cached views and fork references.

# ── 5. PREVENT ─────────────────────────────────────────────────────────
gitleaks protect --staged                 # pre-commit
# + enable GitHub secret scanning with PUSH PROTECTION (blocks at the server)
```

> ⭐ **The single most important sentence in this module**: *rotation is the fix; history rewriting is cleanup.* An engineer who purges history and skips rotation has done the visible work and none of the useful work.

---

### Scenario 4: The Green Pipeline That Ships a Root Container

**Break it:**

```bash
mkdir -p ~/security-lab/green-but-bad && cd ~/security-lab/green-but-bad

cat > Dockerfile <<'EOF'
FROM alpine:3.20
RUN apk add --no-cache ca-certificates
COPY app.sh /app.sh
RUN chmod +x /app.sh
CMD ["/app.sh"]
EOF
echo -e '#!/bin/sh\nwhile :; do sleep 30; done' > app.sh

docker build -q -t green-but-bad:v1 .
trivy image --severity HIGH,CRITICAL --exit-code 1 green-but-bad:v1 ; echo "trivy exit=$?"
```

**Symptom:** Trivy exits **0**. A fresh Alpine base genuinely has no HIGH/CRITICAL CVEs. Your pipeline gate is green — and you have just shipped a container that runs as **root**, with a **writable root filesystem** and **every Linux capability** the runtime grants by default.

**Investigate:**

```bash
docker run --rm green-but-bad:v1 id
# uid=0(root) gid=0(root) groups=0(root)   ⭐ CVE scanning never checks this

docker inspect green-but-bad:v1 --format 'USER={{.Config.User}}'    # empty = root

# The scanners that DO check configuration
hadolint Dockerfile
dockle green-but-bad:v1
trivy config .                     # Dockerfile misconfiguration rules
```

**Root cause:** CVE scanning and configuration scanning answer **different questions**. Trivy's `vuln` scanner asks "does this image contain known-vulnerable packages?" It never asks "is this image configured safely?" A pipeline that runs only `trivy image` has a large, silent blind spot.

**Fix — the Dockerfile:**

```dockerfile
FROM alpine:3.20@sha256:...          # pin by digest
RUN apk add --no-cache ca-certificates && \
    addgroup -g 10001 -S app && adduser -u 10001 -S app -G app
COPY --chown=app:app app.sh /app/app.sh
RUN chmod +x /app/app.sh
USER 10001:10001                     # ⭐ non-root, numeric (works with runAsNonRoot)
ENTRYPOINT ["/app/app.sh"]
```

**And the pipeline — layer the scanners, because each sees something the others don't:**

```yaml
- run: hadolint Dockerfile                                    # Dockerfile lint
- run: trivy fs --scanners vuln,secret,misconfig .            # source: deps + secrets + IaC
- run: gitleaks detect --source . --redact                    # git history
- run: docker build -t $IMAGE .
- run: trivy image --exit-code 1 --severity HIGH,CRITICAL $IMAGE   # CVEs
- run: dockle --exit-code 1 --exit-level warn $IMAGE          # ⭐ image CONFIGURATION
- run: syft $IMAGE -o spdx-json > sbom.json                   # provenance
- run: cosign sign --yes $IMAGE                               # signing
```

**Then enforce it at runtime**, because a well-built image can still be run badly:

```yaml
# Kubernetes admission — the image config is only half the control
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities: {drop: [ALL]}
  seccompProfile: {type: RuntimeDefault}
```

---

### What Each Tool Actually Covers

| Question | Tool | Blind to |
|----------|------|----------|
| Known CVEs in recognised packages? | `trivy image`, `grype` | Vendored/hand-installed deps, image configuration |
| Is the Dockerfile well-formed? | `hadolint` | Runtime behaviour, actual CVEs |
| Is the **image** configured safely? | `dockle`, `trivy config` | CVEs, application logic |
| Secrets in code or history? | `gitleaks`, `trufflehog` | Secrets injected at runtime, secrets in image layers |
| IaC misconfiguration? | `trivy config`, `checkov` | Anything not in the IaC |
| What is actually in this artifact? | `syft` (SBOM) | Nothing — but it only *reports*, it doesn't judge |
| Application logic flaws? | `semgrep`, `bandit` | Dependencies, infrastructure |
| Is the running cluster safe? | `kube-bench`, `kubescape` | Application code |

> ⭐ **The meta-lesson of this lab**: a green pipeline means *"the checks we configured found nothing"* — never *"this is secure."* When someone says "the scan passed," the right follow-up is **"which scanner, and what can't it see?"** Write your triage decisions down (Scenario 2), rotate before you clean up (Scenario 3), and layer tools that have different blind spots (Scenarios 1 and 4).

**Write this up** in `failure-notes.md`: for each scenario, what the scanner reported, what was actually true, and the control you added to close the gap.

```bash
cd ~ && rm -rf ~/security-lab/false-negative ~/security-lab/leak ~/security-lab/green-but-bad
```

---

## 🧹 Cleanup

```bash
cd ..
rm -rf trivy-lab secret-test iac-scan
```

---

## ✅ Validation

- [ ] Scan container images with Trivy and identify HIGH/CRITICAL CVEs
- [ ] Compare CVE counts between a fat image and a slim/alpine image
- [ ] Detect hardcoded secrets in git history with gitleaks
- [ ] Refactor code to use environment variables instead of hardcoded secrets
- [ ] Scan Terraform and Kubernetes configs for misconfigurations
- [ ] Explain why secrets in old git commits are still a risk
- [ ] Build a secure Dockerfile (non-root, slim base, pinned version)
- [ ] Describe how to integrate security scanning into a CI/CD pipeline


## 📝 What to Commit

Add these to your portfolio repo as evidence of completed work:

- Trivy scan output comparing insecure vs secure images
- gitleaks scan results showing detected secrets
- IaC scan output showing misconfigurations found
- Notes on remediation steps for each finding

---

[← Back to Module README](../README.md)
