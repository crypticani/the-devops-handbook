# Module 06: CI/CD

> *"If it hurts, do it more frequently, and bring the pain forward." — Jez Humble*

---

## 🎯 Why This Module Matters

CI/CD is the **backbone of modern software delivery**. Without it, every deployment is a manual, error-prone, stressful event. With it, you ship code multiple times a day with confidence.

**In real-world DevOps work**, you will:
- Build CI pipelines that automatically test every code change
- Create CD pipelines that deploy to staging and production
- Configure deployment strategies (rolling, blue-green, canary)
- Manage secrets and environment-specific configurations
- Debug failed pipelines under pressure
- Enforce quality gates before code reaches production

---

## 📚 Table of Contents

1. [CI/CD Concepts](#1-cicd-concepts)
2. [Pipeline Architecture](#2-pipeline-architecture)
3. [GitHub Actions — Primary Tool](#3-github-actions--primary-tool)
4. [Building a CI Pipeline](#4-building-a-ci-pipeline)
5. [Building a CD Pipeline](#5-building-a-cd-pipeline)
6. [Jenkins — Secondary Tool](#6-jenkins--secondary-tool)
7. [Testing in CI/CD](#7-testing-in-cicd)
8. [Deployment Strategies](#8-deployment-strategies)
9. [Common Mistakes and Anti-Patterns](#9-common-mistakes-and-anti-patterns)
10. [Debugging Mindset](#10-debugging-mindset)
11. [Security Considerations](#11-security-considerations)
12. [Interview Insights](#12-interview-insights)

---

## 1. CI/CD Concepts

### What Do These Terms Actually Mean?

```
Continuous Integration (CI):
  Developers merge code to main branch frequently (multiple times/day).
  Every merge triggers automated build + tests.
  Goal: Catch bugs early, keep the codebase always releasable.

Continuous Delivery (CD):
  Every change that passes CI is automatically deployable to production.
  Deployment to production requires manual approval (button click).
  Goal: Release on demand, any time.

Continuous Deployment (CD):
  Every change that passes CI goes to production automatically.
  No human intervention at all.
  Goal: Ship every commit to users immediately.
```

| Aspect | CI | Continuous Delivery | Continuous Deployment |
|--------|----|--------------------|----------------------|
| **Trigger** | Code push/PR | After CI passes | After CI passes |
| **Automation** | Build + test | Build + test + stage | Build + test + stage + prod |
| **Human step** | None | Approve deploy to prod | None |
| **Risk level** | Low | Medium | Requires mature testing |
| **Adoption** | Nearly universal | Common | Advanced teams |

### The Pipeline Mental Model

```
Developer                                                    Users
   │                                                           ▲
   │ git push                                                  │
   ▼                                                           │
┌──────┐    ┌──────┐    ┌──────┐    ┌──────┐    ┌──────────┐  │
│ Code │───▶│Build │───▶│ Test │───▶│Stage │───▶│Production│──┘
│ Push │    │      │    │      │    │Deploy│    │  Deploy  │
└──────┘    └──────┘    └──────┘    └──────┘    └──────────┘
                                       │             │
                              Auto deploy     Manual approval
                                              (Delivery) OR
                                              Auto (Deployment)
```

---

## 2. Pipeline Architecture

### Stages of a Production Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                        CI/CD Pipeline                           │
├─────────┬──────────┬──────────┬──────────┬────────────────────┤
│  Source  │  Build   │   Test   │  Stage   │    Production      │
│         │          │          │          │                    │
│ • Clone │ • Compile│ • Unit   │ • Deploy │ • Deploy           │
│ • Lint  │ • Bundle │ • Integ  │   to dev │ • Smoke tests      │
│ • SAST  │ • Docker │ • E2E    │ • Smoke  │ • Monitor          │
│         │   image  │ • Cover  │   test   │ • Rollback ready   │
├─────────┴──────────┴──────────┴──────────┴────────────────────┤
│  Feedback: Notify on failure at ANY stage (Slack, email, PR)   │
└─────────────────────────────────────────────────────────────────┘
```

**Key Principles:**
- **Fail fast** — cheapest checks (linting) run first
- **Immutable artifacts** — build once, deploy the same artifact everywhere
- **Environment parity** — staging mirrors production
- **Feedback loops** — developers know within minutes if something broke

---

## 3. GitHub Actions — Primary Tool

### Why GitHub Actions?

- Native to GitHub (where most code lives)
- Free for public repos, generous free tier for private
- Massive marketplace of reusable actions
- Matrix builds, caching, artifacts built-in
- YAML-based, version-controlled alongside code

### Workflow Anatomy

```yaml
# .github/workflows/ci.yml
name: CI Pipeline                    # Workflow name (shown in UI)

on:                                  # Triggers
  push:
    branches: [main, develop]        # Run on push to these branches
  pull_request:
    branches: [main]                 # Run on PRs targeting main

env:                                 # Global environment variables
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:                                # Jobs run in PARALLEL by default
  lint:                              # Job ID
    name: Lint Code                  # Display name
    runs-on: ubuntu-latest           # Runner (GitHub-hosted VM)
    steps:
      - name: Checkout code
        uses: actions/checkout@v4    # Reusable action from marketplace

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install and run linter
        run: |                       # Shell commands
          pip install flake8
          flake8 . --max-line-length=120

  test:
    name: Run Tests
    runs-on: ubuntu-latest
    needs: lint                      # Run AFTER lint passes
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage.xml
```

### Key Concepts

**Triggers (`on`):**

```yaml
on:
  push:
    branches: [main]
    paths:
      - "src/**"                     # Only run when src/ changes
      - "!docs/**"                   # Ignore docs changes
  pull_request:
    types: [opened, synchronize]
  schedule:
    - cron: "0 2 * * 1"             # Weekly Monday 2am UTC
  workflow_dispatch:                 # Manual trigger (button in UI)
    inputs:
      environment:
        description: "Deploy target"
        required: true
        default: "staging"
        type: choice
        options: [staging, production]
```

**Matrix Builds:**

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
        os: [ubuntu-latest, macos-latest]
      fail-fast: false               # Don't cancel others if one fails
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pytest
```

**Caching:**

```yaml
      - name: Cache pip dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-
```

**Secrets & Environment Variables:**

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production          # Links to GitHub environment settings
    steps:
      - name: Deploy
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: ./deploy.sh
```

> 🔐 **Never hardcode secrets.** Use GitHub's encrypted secrets (Settings → Secrets → Actions).

---

## 4. Building a CI Pipeline

### Complete CI Pipeline Example

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: |
          pip install flake8 black
          flake8 . --max-line-length=120
          black --check .

  test:
    name: Test
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: testdb
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Cache dependencies
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: pip-${{ hashFiles('requirements.txt') }}
      - run: pip install -r requirements.txt
      - name: Run tests
        env:
          DATABASE_URL: postgres://test:test@localhost:5432/testdb
        run: pytest --cov --cov-report=xml -v
      - uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage.xml

  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: test
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest
```

### Pipeline Flow

```
PR opened / push to main
        │
        ▼
   ┌─────────┐     ┌─────────┐     ┌────────────┐
   │  Lint    │────▶│  Test   │────▶│ Build+Push │
   │ flake8   │     │ pytest  │     │ Docker img │
   │ black    │     │ + DB    │     │ to GHCR    │
   └─────────┘     └─────────┘     └────────────┘
                                    (push only,
                                     not on PRs)
```

---

## 5. Building a CD Pipeline

### Deployment Workflow with Environments

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  workflow_run:
    workflows: [CI]
    types: [completed]
    branches: [main]

jobs:
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    environment:
      name: staging
      url: https://staging.example.com
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to staging
        env:
          DEPLOY_KEY: ${{ secrets.STAGING_DEPLOY_KEY }}
        run: |
          echo "Deploying ${{ github.sha }} to staging..."
          # Your deployment script here
          ./scripts/deploy.sh staging ${{ github.sha }}

      - name: Smoke test
        run: |
          sleep 10
          curl -f https://staging.example.com/health || exit 1

  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: deploy-staging
    environment:
      name: production             # Requires manual approval in GitHub settings
      url: https://example.com
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to production
        env:
          DEPLOY_KEY: ${{ secrets.PROD_DEPLOY_KEY }}
        run: |
          echo "Deploying ${{ github.sha }} to production..."
          ./scripts/deploy.sh production ${{ github.sha }}

      - name: Smoke test production
        run: |
          sleep 15
          curl -f https://example.com/health || exit 1

      - name: Notify success
        if: success()
        run: echo "✅ Deployed ${{ github.sha }} to production"

      - name: Notify failure
        if: failure()
        run: echo "❌ Production deploy failed — rolling back"
```

### Environment Protection Rules

Configure in GitHub: **Settings → Environments → production**:
- ✅ Required reviewers (team lead must approve)
- ✅ Wait timer (e.g., 5 minutes after staging)
- ✅ Deployment branch restrictions (only `main`)

---

## 6. Jenkins — Secondary Tool

### Why Learn Jenkins?

- Still used by ~50% of enterprises (legacy + complex needs)
- Extremely flexible (2000+ plugins)
- Self-hosted = full control over infrastructure
- Understanding Jenkins makes you more employable

### Jenkins Architecture

```
┌──────────────────────────────────────────┐
│           Jenkins Controller             │
│  • Manages jobs, configuration, UI       │
│  • Schedules builds                      │
│  • Stores build history                  │
└──────┬──────────────┬───────────────────┘
       │              │
  ┌────▼────┐   ┌─────▼────┐
  │ Agent 1 │   │ Agent 2  │
  │ (Linux) │   │ (Docker) │
  │ Runs    │   │ Runs     │
  │ builds  │   │ builds   │
  └─────────┘   └──────────┘
```

### Declarative Jenkinsfile

```groovy
// Jenkinsfile (Declarative)
pipeline {
    agent any

    environment {
        REGISTRY = 'ghcr.io'
        IMAGE = 'myorg/myapp'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Lint') {
            steps {
                sh 'pip install flake8'
                sh 'flake8 . --max-line-length=120'
            }
        }

        stage('Test') {
            steps {
                sh 'pip install -r requirements.txt'
                sh 'pytest --junitxml=results.xml --cov=app'
            }
            post {
                always {
                    junit 'results.xml'
                }
            }
        }

        stage('Build Image') {
            steps {
                script {
                    def image = docker.build("${IMAGE}:${env.BUILD_NUMBER}")
                    docker.withRegistry("https://${REGISTRY}", 'registry-creds') {
                        image.push()
                        image.push('latest')
                    }
                }
            }
        }

        stage('Deploy to Staging') {
            steps {
                sh './scripts/deploy.sh staging'
            }
        }

        stage('Deploy to Production') {
            when {
                branch 'main'
            }
            input {
                message 'Deploy to production?'
                ok 'Yes, deploy!'
            }
            steps {
                sh './scripts/deploy.sh production'
            }
        }
    }

    post {
        success {
            echo '✅ Pipeline completed successfully'
        }
        failure {
            echo '❌ Pipeline failed'
            // slackSend(message: "Build failed: ${env.JOB_NAME}")
        }
        always {
            cleanWs()  // Clean workspace
        }
    }
}
```

### GitHub Actions vs Jenkins

| Feature | GitHub Actions | Jenkins |
|---------|---------------|---------|
| **Hosting** | Cloud (GitHub-hosted) | Self-hosted |
| **Config** | YAML files | Groovy Jenkinsfile |
| **Setup** | Zero (just add YAML) | Install + configure server |
| **Plugins** | Marketplace actions | 2000+ plugins |
| **Cost** | Free tier generous | Free (but you pay for infra) |
| **Scaling** | Auto (GitHub runners) | Manual (add agents) |
| **Best for** | GitHub-hosted projects | Enterprise, complex needs |
| **Learning** | Lower barrier | Steeper curve |

---

## 7. Testing in CI/CD

### Test Pyramid in Pipelines

```
                 ┌───────┐
                 │  E2E  │  ← Slow, expensive, few
                 │ tests │     (Selenium, Cypress)
                ┌┴───────┴┐
                │Integr.  │  ← Medium speed, some
                │ tests   │     (API tests, DB tests)
               ┌┴─────────┴┐
               │  Unit      │  ← Fast, cheap, many
               │  tests     │     (pytest, jest)
               └────────────┘
```

**Run order in pipeline:** Unit → Integration → E2E (fail fast with cheap tests first)

```yaml
  test-unit:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/unit/ -v

  test-integration:
    needs: test-unit
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
    steps:
      - run: pytest tests/integration/ -v

  test-e2e:
    needs: test-integration
    runs-on: ubuntu-latest
    steps:
      - run: npx cypress run
```

---

## 8. Deployment Strategies

### Rolling Deployment

```
Time 0: [v1] [v1] [v1] [v1]    ← All running v1
Time 1: [v2] [v1] [v1] [v1]    ← Replace one at a time
Time 2: [v2] [v2] [v1] [v1]
Time 3: [v2] [v2] [v2] [v1]
Time 4: [v2] [v2] [v2] [v2]    ← All running v2

✅ Pros: Zero downtime, simple
❌ Cons: Both versions run simultaneously during rollout
```

### Blue-Green Deployment

```
                    Load Balancer
                    ┌───┴───┐
              ┌─────▼─────┐ │
              │ Blue (v1)  │ │  ← Currently serving traffic
              │ [v1][v1]   │ │
              └────────────┘ │
              ┌────────────┐ │
              │ Green (v2)  │ │  ← Deploy + test here
              │ [v2][v2]   │ │
              └─────▲──────┘ │
                    └────────┘
                    Switch traffic when green is verified!

✅ Pros: Instant rollback (switch back to blue), zero downtime
❌ Cons: Double infrastructure cost during deployment
```

### Canary Deployment

```
Before:  Load Balancer → [v1] [v1] [v1] [v1]  (100% v1)
Canary:  Load Balancer → [v1] [v1] [v1] [v2]  (25% → v2)
         Monitor metrics... error rate OK? latency OK?
Rollout: Load Balancer → [v2] [v2] [v2] [v2]  (100% v2)

✅ Pros: Minimal risk, real-world validation
❌ Cons: Complex routing, monitoring required
```

---

## 9. Common Mistakes and Anti-Patterns

### ❌ Hardcoding Secrets

```yaml
# BAD: Secret in plain text (committed to repo!)
env:
  AWS_KEY: AKIAIOSFODNN7EXAMPLE
  DB_PASS: mysecretpassword

# GOOD: Use encrypted secrets
env:
  AWS_KEY: ${{ secrets.AWS_ACCESS_KEY_ID }}
  DB_PASS: ${{ secrets.DB_PASSWORD }}
```

### ❌ No Caching

```yaml
# BAD: Install everything from scratch every run (5+ minutes)
- run: pip install -r requirements.txt

# GOOD: Cache dependencies (30 seconds)
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: pip-${{ hashFiles('requirements.txt') }}
- run: pip install -r requirements.txt
```

### ❌ Running Tests Only on Main

```yaml
# BAD: Only test on main (bugs found after merge)
on:
  push:
    branches: [main]

# GOOD: Test on PRs too (bugs found before merge)
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

### ❌ No Rollback Strategy

Always plan for failure:
- Keep the previous Docker image tagged and available
- Use blue-green or canary deployments
- Have a one-command rollback script
- Test your rollback process regularly

---

## 10. Debugging Mindset

### CI/CD Debugging Framework

```
Pipeline failed?
│
├─ 1. READ THE LOGS (90% of answers are here)
│     └─ Find the FIRST error, not the last
│
├─ 2. Check: Is it a code issue or pipeline issue?
│     ├─ Code: Does it work locally? → Fix code
│     └─ Pipeline: YAML syntax? Permissions? Secrets?
│
├─ 3. Reproduce locally
│     ├─ GitHub Actions: use `act` tool
│     └─ Jenkins: run the same commands in Docker
│
└─ 4. Common culprits:
      ├─ Missing secrets or wrong secret name
      ├─ YAML indentation error
      ├─ Permission denied (checkout, push, deploy)
      ├─ Dependency version changed (pin versions!)
      └─ Flaky tests (timing, external services)
```

### Using `act` for Local GitHub Actions Testing

```bash
# Install act (runs GHA workflows locally using Docker)
# macOS
brew install act

# Linux
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run your workflow locally
act push                        # Simulate push event
act pull_request                # Simulate PR event
act -j test                     # Run specific job
act --secret-file .env.secrets  # With secrets
```

---

## 11. Security Considerations

> 🔐 Your CI/CD pipeline has access to production — it's a prime attack target.

- **Secrets management** — Never commit secrets. Use GitHub encrypted secrets or external vaults (HashiCorp Vault, AWS Secrets Manager)
- **Least-privilege tokens** — Use `permissions` in workflows to restrict `GITHUB_TOKEN` scope
- **Pin action versions** — Use `@v4` or SHA, not `@main` (supply chain attack vector)
- **Dependency scanning** — Run `dependabot`, `snyk`, or `trivy` in CI
- **Branch protection** — Require CI to pass before merging to main
- **Signed commits** — Verify code authenticity with GPG/SSH signatures
- **OIDC authentication** — Use OpenID Connect instead of static AWS/cloud keys

```yaml
# GOOD: Minimal permissions
permissions:
  contents: read
  packages: write

# GOOD: Pin action to specific SHA (not tag that can be moved)
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
```

---

## 12. Interview Insights

**Q: What's the difference between Continuous Delivery and Continuous Deployment?**
> Continuous Delivery means every change is *deployable* to production but requires manual approval. Continuous Deployment means every change that passes tests goes to production *automatically*. Delivery is the safer choice for most teams; Deployment requires very mature testing.

**Q: Describe a CI/CD pipeline you've built or worked with.**
> Structure your answer: trigger → lint → test → build artifact → deploy to staging → manual approval → deploy to production. Mention specific tools (GitHub Actions, Docker, pytest), caching strategy, and how you handle failures.

**Q: How do you handle secrets in CI/CD?**
> Never in code or environment files committed to git. Use the platform's secret store (GitHub Secrets, Jenkins Credentials, Vault). Rotate regularly. Use OIDC for cloud providers instead of static keys. Audit access logs.

**Q: A deployment failed in production. What do you do?**
> 1. Rollback immediately (don't debug in production). 2. Verify rollback with health checks. 3. Check deployment logs for the root cause. 4. Reproduce in staging. 5. Fix, test, and redeploy. Always have a rollback plan *before* you deploy.

**Q: What are the benefits of pipeline-as-code?**
> Pipeline configuration lives alongside application code, version-controlled, reviewed in PRs, and reproducible. Changes to the pipeline go through the same review process as code changes. Any team member can understand and modify the pipeline.

**Q: How do you make pipelines faster?**
> Cache dependencies, run independent jobs in parallel, use matrix builds for multi-version testing, fail fast (lint before test), use slim Docker base images, only run relevant jobs (path filters), and avoid unnecessary steps on PRs vs main.

---

## ➡️ What's Next?

With CI/CD mastered, you can now build the observability stack needed to monitor what your pipelines deploy.

**[Module 07: Observability →](../07-observability/)**

---

<div align="center">

**Module 06 Complete** ✅

[← Back to Docker](../05-containers-docker/) | [Next: Observability →](../07-observability/)

</div>
