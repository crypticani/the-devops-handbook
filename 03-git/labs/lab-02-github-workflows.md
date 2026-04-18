# Lab 02: GitHub Workflows & Pull Requests

## 🎯 Objective

Practice the complete GitHub collaboration workflow — forking, branching, PRs, code review, and branch protection. This is how every DevOps team works.

---

## 📋 Prerequisites

- GitHub account
- Git configured with SSH keys
- GitHub CLI (`gh`) installed: `sudo apt install -y gh && gh auth login`

---

## 🔬 Exercise 1: The Complete PR Workflow

### Step 1: Create a Repository on GitHub

```bash
cd ~/devops-labs/module-03
mkdir github-workflow && cd github-workflow
git init

# Create initial content
cat > README.md << 'README'
# Infrastructure Config

Terraform and Ansible configurations for our production environment.

## Structure
- `terraform/` — Infrastructure as Code
- `ansible/` — Configuration Management
- `scripts/` — Utility scripts
README

mkdir -p terraform ansible scripts

cat > terraform/main.tf << 'TF'
# Main Terraform configuration
provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"

  tags = {
    Name = "web-server"
    Environment = "production"
  }
}
TF

cat > .gitignore << 'IGNORE'
.terraform/
*.tfstate
*.tfstate.backup
.env
*.pem
IGNORE

git add -A
git commit -m "feat: initial infrastructure setup"

# Create the repo on GitHub and push
gh repo create github-workflow --public --source=. --push
```

### Step 2: Create a Feature Branch and PR

```bash
# Create a branch for a new feature
git checkout -b feature/add-monitoring-instance

# Add monitoring server config
cat > terraform/monitoring.tf << 'TF'
# Monitoring infrastructure
resource "aws_instance" "monitoring" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.medium"

  tags = {
    Name        = "monitoring-server"
    Environment = "production"
    Role        = "prometheus-grafana"
  }
}

resource "aws_security_group" "monitoring" {
  name        = "monitoring-sg"
  description = "Security group for monitoring stack"

  ingress {
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
    description = "Prometheus"
  }

  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
    description = "Grafana"
  }
}
TF

git add -A
git commit -m "feat(infra): add monitoring server with Prometheus and Grafana"

# Push the branch
git push -u origin feature/add-monitoring-instance

# Create a PR using GitHub CLI
gh pr create \
  --title "feat(infra): Add monitoring server" \
  --body "## Changes
- Add Prometheus + Grafana monitoring server (t2.medium)
- Configure security group for ports 9090 (Prometheus) and 3000 (Grafana)
- Restrict access to internal network (10.0.0.0/8)

## Testing
- [ ] terraform plan shows expected resources
- [ ] Security group rules are correct
- [ ] No public access to monitoring ports"
```

### Step 3: Review and Merge

```bash
# List open PRs
gh pr list

# View PR details
gh pr view 1

# Check out PR locally for testing (as a reviewer would)
gh pr checkout 1

# After review, merge with squash
gh pr merge 1 --squash --delete-branch

# Pull the merged changes
git checkout main
git pull
```

---

## 🔬 Exercise 2: .gitignore Audit

### Step 1: Check For Accidentally Committed Files

```bash
# Common problem: secrets or state files committed

# Create some files that should be ignored
echo "AWS_SECRET_KEY=AKIAIOSFODNN7EXAMPLE" > .env
echo '{"state": "data"}' > terraform/terraform.tfstate

# Check if .gitignore catches them
git status
# .env and terraform.tfstate should NOT appear (ignored!)

# Verify what's being ignored
git status --ignored

# What if a file was committed BEFORE .gitignore was set up?
# .gitignore doesn't remove already-tracked files!

# Simulate: track a file, then try to ignore it
echo "oops" > tracked-secret.txt
git add tracked-secret.txt
git commit -m "oops: committed a secret"

echo "tracked-secret.txt" >> .gitignore
git add .gitignore
git commit -m "chore: update gitignore"

git status
# tracked-secret.txt is STILL tracked!

# Fix: Remove from tracking (but keep the file locally)
git rm --cached tracked-secret.txt
git commit -m "fix: remove tracked secret from version control"

# Now it's properly ignored
git status
# Nothing to commit
```

---

## 🧨 Break It: Recovery Scenarios

### Scenario: Someone Force Pushed to Main

```bash
# Simulate: You're working and someone rewrites main
git checkout -b your-work
echo "your important changes" > scripts/deploy.sh
git add -A && git commit -m "feat: add deploy script"

# Come back to main and see it's been rewritten
git checkout main

# Use reflog to find the state before the force push
git reflog
# Find the commit hash you want to recover to

# Recovery options:
# 1. Reset to the known good state
# 2. Cherry-pick your commits onto the new main
```

---

## ✅ Validation

- [ ] Create a GitHub repo from the command line
- [ ] Create a PR with a descriptive body
- [ ] Review, approve, and merge a PR
- [ ] Properly configure .gitignore for a DevOps project
- [ ] Remove an accidentally tracked file from Git
- [ ] Use `gh` CLI for common GitHub operations

---

## 💡 Key Takeaways

1. **PRs are the gate to production** — every change should go through review
2. **`.gitignore` must be set up BEFORE first commit** — retroactive ignoring requires extra steps
3. **Never commit secrets** — even removing them later leaves traces in history
4. The GitHub CLI (`gh`) makes PR workflows much faster than the web UI

---

[← Previous Lab](./lab-01-git-core-workflow.md) | [Back to Module README](../README.md)
