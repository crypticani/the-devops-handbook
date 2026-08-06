# Module 06: CI/CD

> *"If it hurts, do it more frequently, and bring the pain forward." — Jez Humble*

---

> 📋 **Command reference**: [`cheatsheet.md`](./cheatsheet.md) — every command in this module, grouped by task, with the gotchas.
>
> ⚡ **Cross-module lookup**: [Quick Reference](../QUICK-REFERENCE.md)

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

The three terms describe **where the automation stops**. Same pipeline, different end point:

```mermaid
flowchart LR
    DEV(["👩‍💻 Developer<br/>git push"]) --> B["Build"]
    B --> T["Test"]
    T --> STG["Deploy to<br/>Staging"]
    STG --> GATE{"Manual<br/>approval?"}
    GATE -->|"required"| PROD["Deploy to<br/>Production"]
    GATE -->|"skipped"| PROD
    PROD --> USERS(["👥 Users"])

    subgraph ci["Continuous Integration"]
        B
        T
    end
    subgraph cdel["Continuous Delivery — stops at the gate"]
        STG
        GATE
    end
    subgraph cdep["Continuous Deployment — no gate at all"]
        PROD
    end

    style ci fill:#e8f0ff,stroke:#3366cc
    style cdel fill:#fff4e0,stroke:#cc8800
    style cdep fill:#e8ffe8,stroke:#22aa22
    style GATE fill:#fff,stroke:#cc8800,stroke-width:2px
```

**CI** = every merge is built and tested. **Continuous Delivery** = every passing build *could* go to prod, a human decides when. **Continuous Deployment** = it goes, no human involved. The only structural difference between the last two is that one diamond.

---

## 2. Pipeline Architecture

### Stages of a Production Pipeline

Real pipelines are a **graph**, not a line. Independent checks fan out in parallel; everything converges on a single build artifact that is then promoted — never rebuilt — through each environment.

```mermaid
flowchart TD
    SRC(["git push / pull_request"]) --> CHECKOUT["Checkout + restore cache"]

    CHECKOUT --> LINT["Lint<br/><i>~20s</i>"]
    CHECKOUT --> SAST["SAST + secret scan<br/><i>~40s</i>"]
    CHECKOUT --> UNIT["Unit tests<br/><i>~2m</i>"]

    LINT --> BUILD
    SAST --> BUILD
    UNIT --> BUILD

    BUILD["<b>Build once</b><br/>compile · bundle · docker build<br/>tag with the commit SHA"]
    BUILD --> SCAN["Image scan — Trivy<br/>fail on HIGH/CRITICAL"]
    SCAN --> PUSH["Push artifact to registry<br/><code>myapp:a1b2c3d</code>"]

    PUSH --> DEPSTG["Deploy to <b>staging</b><br/>same artifact"]
    DEPSTG --> INTEG["Integration + E2E tests"]
    INTEG --> SMOKE1["Smoke test staging"]

    SMOKE1 --> GATE{"Approval gate<br/><i>Continuous Delivery only</i>"}
    GATE --> DEPPROD["Deploy to <b>production</b><br/><b>same artifact</b> — never rebuilt"]
    DEPPROD --> SMOKE2["Smoke test prod"]
    SMOKE2 --> WATCH["Watch error rate + latency<br/>Module 07"]
    WATCH -->|"SLO breached"| RB["🔙 Automatic rollback"]
    WATCH -->|"healthy"| DONE(["✅ Released"])

    LINT -.->|"❌"| FB
    SAST -.->|"❌"| FB
    UNIT -.->|"❌"| FB
    SCAN -.->|"❌"| FB
    INTEG -.->|"❌"| FB
    FB["🔔 Notify: PR comment · Slack · red check"]

    style BUILD fill:#e8f0ff,stroke:#3366cc,stroke-width:2px
    style GATE fill:#fff4e0,stroke:#cc8800
    style DONE fill:#e0ffe0,stroke:#0a0
    style RB fill:#ffe0e0,stroke:#c00
    style FB fill:#ffe0e0,stroke:#c00
```

**Key Principles:**

- **Fail fast** — cheapest checks (linting) run first, and in parallel
- **Immutable artifacts** — build once, deploy the same artifact everywhere. If you rebuild between staging and prod, you tested a different thing than you shipped
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

Four nested concepts. Getting the boundaries wrong is the most common source of "why is my file missing in the next job?"

```mermaid
flowchart TB
    EVT(["<b>Event</b><br/>push · pull_request · schedule ·<br/>workflow_dispatch"]) --> WF

    subgraph WF["<b>Workflow</b> — .github/workflows/ci.yml"]
        direction TB

        subgraph J1["<b>Job: lint</b> — fresh ubuntu-latest VM"]
            S1["Step: actions/checkout@v4"]
            S2["Step: setup-python@v5"]
            S3["Step: run flake8"]
            S1 --> S2 --> S3
        end

        subgraph J2["<b>Job: test</b> — fresh ubuntu-latest VM"]
            T1["Step: checkout"]
            T2["Step: pytest"]
            T1 --> T2
        end

        subgraph J3["<b>Job: build</b> — fresh ubuntu-latest VM"]
            B1["Step: docker build"]
            B2["Step: upload-artifact"]
            B1 --> B2
        end
    end

    J1 -->|"needs: lint"| J2
    J2 -->|"needs: test"| J3

    style J1 fill:#e8f0ff,stroke:#3366cc
    style J2 fill:#e8f0ff,stroke:#3366cc
    style J3 fill:#e8f0ff,stroke:#3366cc
```

| Level | What it is | Key rule |
|-------|-----------|----------|
| **Event** | What triggers the run | Defined by `on:` |
| **Workflow** | One YAML file | A repo can have many; they run independently |
| **Job** | A unit that gets **its own clean VM** | Jobs run **in parallel** unless linked with `needs:` |
| **Step** | One command or action | Steps in a job share the same filesystem and shell session |

> **💡 The boundary that trips everyone up**: each job starts on a **brand-new machine**. Files written in the `build` job do **not** exist in the `deploy` job — and neither does your checkout. To move data between jobs use `actions/upload-artifact` / `download-artifact`, or `outputs:`. To move data between *steps*, just write a file; they share a disk.

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

### The Other Model: Pull-Based Delivery (GitOps)

Everything above is **push**: the pipeline holds production credentials and runs the deployment. That is still the common case, and for anything that isn't Kubernetes it is usually the only case.

The alternative is **pull**: a controller running *inside* the target cluster watches a Git repository of manifests and reconciles the cluster toward it continuously. The pipeline's job stops at building an image and committing a manifest change — it never touches the cluster, and never needs a credential that could deploy to it.

| | Push (this section) | Pull (GitOps) |
|---|---|---|
| Who deploys | The CI runner | A controller in the cluster |
| Prod credentials live in | The CI system | Nowhere outside the cluster |
| Deployment history | Pipeline run logs | `git log` on the manifests repo |
| Drift from manual changes | Undetected until something breaks | Detected, and reverted if configured to |
| Works for | Anything | Kubernetes, essentially |

> **💡 DevOps Impact**: The security argument is the one that wins arguments — a compromised pipeline with no cluster credentials cannot deploy anything. The operational argument is drift detection: push-based delivery has no idea what the cluster looks like between deploys.

Concepts and tradeoffs, including when GitOps is overkill: [Module 14 §9](../14-system-design-devops/README.md). Hands-on with Argo CD, once you know Kubernetes: [Module 12, Lab 06](../12-kubernetes/labs/lab-06-gitops-argocd.md).

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

All three strategies achieve zero downtime. They differ in **how much infrastructure you pay for** and **how fast you can undo a bad release**.

### Rolling Deployment

Replace instances a few at a time. The default in Kubernetes.

```
Time 0: [v1] [v1] [v1] [v1]    ← All running v1
Time 1: [v2] [v1] [v1] [v1]    ← Replace one at a time
Time 2: [v2] [v2] [v1] [v1]
Time 3: [v2] [v2] [v2] [v1]
Time 4: [v2] [v2] [v2] [v2]    ← All running v2
```

```mermaid
sequenceDiagram
    participant LB as Load Balancer
    participant P as Pool (4 instances)

    Note over P: v1 v1 v1 v1
    LB->>P: drain instance 1
    Note over P: -- v1 v1 v1
    LB->>P: start v1 → v2, wait for readiness probe
    Note over P: v2 v1 v1 v1
    LB->>P: repeat for instances 2, 3, 4
    Note over P: v2 v2 v2 v2
    Note over LB,P: ⚠️ v1 and v2 serve traffic simultaneously<br/>for the whole rollout window
```

- ✅ **Pros**: Zero downtime, no extra infrastructure, built into Kubernetes
- ❌ **Cons**: Both versions run at once — your API and DB schema must be **backward compatible**. Rollback is another full rolling update, so it's slow.

### Blue-Green Deployment

Two complete environments. Flip all traffic at once.

```mermaid
flowchart TB
    U(["Users"]) --> LB{"Load Balancer /<br/>DNS / Target Group"}

    LB ==>|"100% — live"| BLUE
    LB -.->|"0% — idle, warmed"| GREEN

    subgraph BLUE["🔵 Blue — v1 (current)"]
        B1["v1"]
        B2["v1"]
    end
    subgraph GREEN["🟢 Green — v2 (new)"]
        G1["v2"]
        G2["v2"]
    end

    GREEN -.-> TEST["Smoke tests run here<br/>with zero user impact"]
    TEST -->|"pass → flip the LB"| SWITCH["Cut 100% to Green<br/><i>Blue stays up as the rollback target</i>"]

    style BLUE fill:#ddeeff,stroke:#3366cc,stroke-width:2px
    style GREEN fill:#ddffdd,stroke:#22aa22
```

- ✅ **Pros**: **Instant rollback** — flip the load balancer back. Full testing against production infrastructure before any user sees it.
- ❌ **Cons**: Double the infrastructure cost during the switch. Shared state (databases, caches, queues) doesn't get duplicated, so schema changes still need care.

### Canary Deployment

Shift a small slice of real traffic, watch the metrics, then decide.

```mermaid
flowchart LR
    U(["Users"]) --> LB{"Traffic split"}

    LB -->|"95%"| V1["v1<br/>stable"]
    LB -->|"5%"| V2["v2<br/>canary"]

    V1 --> M["📊 Prometheus<br/>error rate · p99 latency · saturation"]
    V2 --> M

    M --> D{"Canary healthier than<br/>or equal to stable?"}
    D -->|"yes"| UP["Promote: 5% → 25% → 50% → 100%"]
    D -->|"no"| AB["🔙 Abort: route 100% back to v1<br/>only 5% of users were ever affected"]

    style V2 fill:#fff4e0,stroke:#cc8800
    style AB fill:#ffe0e0,stroke:#c00
    style UP fill:#e0ffe0,stroke:#0a0
```

- ✅ **Pros**: Smallest blast radius of any strategy — a bad release hits 5% of users, not 100%. Validates against real production traffic patterns that staging can't reproduce.
- ❌ **Cons**: Needs weighted routing (service mesh, ingress, or ALB rules) **and** the observability from Module 07 to make the promote/abort decision. Without metrics, a canary is just a slow rollout.

### Choosing One

| | Rolling | Blue-Green | Canary |
|---|---------|-----------|--------|
| **Extra infrastructure** | None | 2× during switch | ~5–10% |
| **Rollback speed** | Slow (another rollout) | **Instant** (flip LB) | Instant (reroute) |
| **Blast radius of a bad release** | Grows as rollout proceeds | 100% at once after the flip | 5% |
| **Requires good metrics** | Helpful | Helpful | **Mandatory** |
| **Complexity** | Low | Medium | High |
| **Good default for** | Most services on Kubernetes | Releases you must be able to undo in seconds | High-traffic, user-facing services |

> **💡 All three break the same way**: none of them protect you from a **non-backward-compatible database migration**. During any of these rollouts, old and new code run against the same database. Use the expand/contract pattern — add the new column, deploy code that writes both, backfill, deploy code that reads the new one, *then* drop the old column across separate releases.

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
- **Build provenance** — Attest what your pipeline built and how, to prove artifact integrity
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

# GOOD: Attest build provenance (supply chain security)
# After building and pushing a Docker image:
- name: Attest build provenance
  uses: actions/attest-build-provenance@v2
  with:
    subject-name: ghcr.io/${{ github.repository }}
    subject-digest: ${{ steps.push.outputs.digest }}
    push-to-registry: true
# This creates a signed, verifiable record of WHAT was built,
# WHERE (which repo/workflow), and WHO triggered it.
# Consumers can verify: gh attestation verify <image>
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
>
> 1. Rollback immediately (don't debug in production). 2. Verify rollback with health checks. 3. Check deployment logs for the root cause. 4. Reproduce in staging. 5. Fix, test, and redeploy. Always have a rollback plan *before* you deploy.

**Q: What are the benefits of pipeline-as-code?**
> Pipeline configuration lives alongside application code, version-controlled, reviewed in PRs, and reproducible. Changes to the pipeline go through the same review process as code changes. Any team member can understand and modify the pipeline.

**Q: How do you make pipelines faster?**
> Cache dependencies, run independent jobs in parallel, use matrix builds for multi-version testing, fail fast (lint before test), use slim Docker base images, only run relevant jobs (path filters), and avoid unnecessary steps on PRs vs main.

---

## 🧪 Labs and Projects

Read the sections above first, then work through these **in order**. Every lab ends with a 🧨 **Break It** section — those are not optional; they are where the debugging skill actually comes from.

| # | Lab | What you'll do |
|---|-----|----------------|
| 1 | **[GitHub Actions](./labs/lab-01-github-actions.md)** | Go from zero to a working CI/CD pipeline. |
| 2 | **[Jenkins Pipeline](./labs/lab-02-jenkins-pipeline.md)** | Set up Jenkins from scratch using Docker, create a Declarative Pipeline, configure credentials and triggers, and debug common failures. |

**Portfolio project:**

- [Project: Pull Request CI Pipeline](./projects/project-01-pull-request-pipeline.md) — Create a CI pipeline that gives fast feedback on every pull request and blocks changes that fail linting, tests, or build checks.

**Reference code** for every lab: [`code/`](./code/) — real files, validated in CI.

---

## ✅ Self-Check

Answer these from memory before you expand them. If more than two give you trouble, re-read the sections they come from — the labs assume this material is solid.

<details>
<summary><strong>1. In what order should pipeline stages run, and why does that order matter more than total runtime?</strong></summary>

Cheapest and most likely to fail first: lint, unit tests, build, then integration tests, scans, and deploy. Feedback speed is what people actually experience — a forty-minute suite that fails on a formatting error teaches everyone to stop watching CI.

</details>

<details>
<summary><strong>2. Blue-green or canary?</strong></summary>

Blue-green runs two complete environments and switches traffic at once: instant rollback, double the infrastructure, and one exposed moment. Canary shifts a small share of real traffic first and watches metrics: it catches what only production traffic reveals, but it is slower and needs observability good enough to make the call.

</details>

<details>
<summary><strong>3. Why should the pipeline build the artefact exactly once?</strong></summary>

Rebuilding per environment means the thing you tested is not the thing you shipped — different base image, different transitive dependency, different timestamp. Build once, then promote that immutable artefact through environments with configuration injected at deploy time.

</details>

<details>
<summary><strong>4. What do CI secrets actually protect you from, and where do they leak?</strong></summary>

Masking in logs prevents accidental printing, not deliberate exfiltration: any step that can run code can read the secrets exposed to it. Pull requests from forks get none by default — reaching for `pull_request_target` to work around that is how repositories hand write access to strangers.

</details>

<details>
<summary><strong>5. A test fails intermittently. Why is re-running it the wrong first move?</strong></summary>

Because the retry hides the defect and trains the team to click until green, at which point the suite stops being evidence of anything. Flakiness has causes you can find: shared state between tests, `latest` tags and unpinned dependencies, ordering assumptions, and real race conditions in the code under test.

</details>

<details>
<summary><strong>6. What has to be true before you let deployment to production happen automatically?</strong></summary>

Tests you actually trust, monitoring that will tell you a release went bad without a human watching, and a rollback that is one automated step. Without those three, automating deployment just means arriving at the outage faster.

</details>

---

## Practical Checkpoint

Before moving on, you should be able to:

- Build a pipeline that runs on pull requests and blocks unsafe changes.
- Separate lint, test, build, scan, and deploy stages with clear failure output.
- Debug pipeline failures by reading logs, reproducing locally, and narrowing the failing stage.

Portfolio evidence to keep:

- Workflow or Jenkinsfile definitions.
- Passing and failing pipeline run notes.
- A short explanation of what each pipeline stage protects.

Suggested project: [Pull Request CI Pipeline](./projects/project-01-pull-request-pipeline.md)

---

## ➡️ What's Next?

With CI/CD mastered, you can now build the observability stack needed to monitor what your pipelines deploy.

**[Module 07: Observability →](../07-observability/)**

---

<div align="center">

**Module 06 Complete** ✅

[← Back to Docker](../05-containers-docker/) | [📋 Cheat Sheet](./cheatsheet.md) | [Next: Observability →](../07-observability/)

</div>
