# Lab 01: Security Scanning — Trivy, gitleaks, and Secure CI/CD

## 🎯 Objective

Integrate security scanning into your DevOps workflow. You'll scan container images for CVEs, detect secrets in git repos, write a secure Dockerfile, and build a CI pipeline with security gates.

---

## 📋 Prerequisites

- Docker installed
- Git repository (local or GitHub)
- Completed Module 05 (Docker) and Module 06 (CI/CD)

---

## 🔬 Exercise 1: Scan Container Images with Trivy

### Step 1: Install Trivy

```bash
# Linux
sudo apt-get install wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main | sudo tee /etc/apt/sources.list.d/trivy.list
sudo apt-get update && sudo apt-get install trivy

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

---

[← Back to Module README](../README.md)
