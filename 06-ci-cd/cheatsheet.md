# Module 06: CI/CD — Cheat Sheet

> GitHub Actions and Jenkins reference. Concepts live in the [module README](./README.md).
> Cross-module daily commands: **[QUICK-REFERENCE.md](../QUICK-REFERENCE.md)**

**Jump to:** [Triggers](#workflow-triggers) · [Contexts](#contexts--expressions) · [Jobs & steps](#jobs--steps) · [Matrix](#matrix-builds) · [Caching](#caching) · [Artifacts](#artifacts--outputs) · [Secrets & OIDC](#secrets--oidc) · [Reusable](#reusable-workflows--composite-actions) · [Full pipeline](#a-complete-pipeline) · [gh CLI](#debugging-with-gh) · [Jenkins](#jenkins) · [Errors](#error-decoder)

---

## Workflow Triggers

```yaml
on:
  push:
    branches: [main, 'release/**']
    paths: ['src/**', 'Dockerfile']          # only run when these change
    paths-ignore: ['**.md', 'docs/**']
    tags: ['v*.*.*']
  pull_request:
    branches: [main]
    types: [opened, synchronize, reopened, ready_for_review]
  schedule:
    - cron: '0 3 * * *'                      # UTC only. Not guaranteed on time
  workflow_dispatch:                          # ⭐ manual run button
    inputs:
      environment:
        type: choice
        options: [staging, production]
        required: true
      dry_run:
        type: boolean
        default: true
  workflow_call:                              # callable from another workflow
  workflow_run:
    workflows: ["CI"]
    types: [completed]
  release:
    types: [published]
  issue_comment:
    types: [created]
```

```yaml
# Cancel superseded runs on the same branch — saves a lot of runner minutes ⭐
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

# Never cancel a production deploy midway
concurrency:
  group: deploy-production
  cancel-in-progress: false
```

---

## Contexts & Expressions

| Expression | Value |
|------------|-------|
| `${{ github.repository }}` | `owner/repo` |
| `${{ github.ref }}` | `refs/heads/main`, `refs/tags/v1.0.0` |
| `${{ github.ref_name }}` | `main`, `v1.0.0` |
| `${{ github.sha }}` | Full commit SHA |
| `${{ github.event_name }}` | `push`, `pull_request`, … |
| `${{ github.actor }}` | Who triggered it |
| `${{ github.run_id }}` / `run_number` / `run_attempt` | Run identifiers |
| `${{ github.workspace }}` | Checkout directory |
| `${{ github.event.pull_request.number }}` | PR number |
| `${{ secrets.NAME }}` | Encrypted secret |
| `${{ vars.NAME }}` | Non-secret configuration variable |
| `${{ env.NAME }}` | Environment variable |
| `${{ runner.os }}` / `runner.temp` / `runner.arch` | Runner info |
| `${{ job.status }}` | `success`, `failure`, `cancelled` |
| `${{ steps.<id>.outputs.<key> }}` | Output from an earlier step |
| `${{ needs.<job>.outputs.<key> }}` | Output from an upstream job |

**Functions:** `contains()` · `startsWith()` · `endsWith()` · `format()` · `join()` · `toJSON()` · `fromJSON()` · `hashFiles()` · `success()` · `failure()` · `always()` · `cancelled()`

```yaml
if: github.ref == 'refs/heads/main'
if: github.event_name == 'pull_request'
if: contains(github.event.head_commit.message, '[skip ci]') == false
if: startsWith(github.ref, 'refs/tags/v')
if: failure()                                 # only when a previous step failed
if: always()                                  # ⭐ run even after failure (cleanup, reports)
if: success() && github.actor != 'dependabot[bot]'
if: github.event.pull_request.draft == false
```

> ⚠️ `${{ }}` interpolation happens **before** the shell sees the line, so untrusted input (PR titles, branch names, issue bodies) becomes shell code. Never write `run: echo "${{ github.event.pull_request.title }}"`. Pass it through `env:` instead and reference `"$TITLE"`.

---

## Jobs & Steps

```yaml
jobs:
  build:
    name: Build and test
    runs-on: ubuntu-latest              # ubuntu-24.04 | windows-latest | macos-latest
                                        # or: [self-hosted, linux, x64]
    timeout-minutes: 15                 # ⭐ always set — stops runaway jobs burning minutes
    needs: [lint]                       # dependency: run after lint
    if: github.event_name == 'push'
    permissions:                        # ⭐ least privilege for GITHUB_TOKEN
      contents: read
      packages: write
      id-token: write                   # required for OIDC
    environment:
      name: production                  # ties into environment protection rules/approvals
      url: https://example.com
    outputs:
      image_tag: ${{ steps.meta.outputs.tag }}
    defaults:
      run:
        working-directory: ./app
        shell: bash
    env:
      LOG_LEVEL: debug
    services:                           # ⭐ sidecar containers for integration tests
      postgres:
        image: postgres:15
        env: {POSTGRES_PASSWORD: test}
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready --health-interval 10s
          --health-timeout 5s --health-retries 5

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0                # full history (needed for tags/changelogs)

      - name: Compute image tag
        id: meta
        run: echo "tag=${GITHUB_SHA::7}" >> "$GITHUB_OUTPUT"

      - name: Multi-line script
        run: |
          set -euo pipefail
          make build
          make test
        env:
          API_TOKEN: ${{ secrets.API_TOKEN }}

      - name: Continue even if this fails
        continue-on-error: true
        run: ./optional-check.sh

      - name: Always upload the report
        if: always()
        uses: actions/upload-artifact@v4
        with: {name: test-report, path: reports/}
```

### Workflow commands

```bash
echo "key=value"        >> "$GITHUB_OUTPUT"    # step output
echo "KEY=value"        >> "$GITHUB_ENV"       # env var for LATER steps
echo "/opt/tool/bin"    >> "$GITHUB_PATH"      # prepend to PATH
echo "## Results"       >> "$GITHUB_STEP_SUMMARY"   # ⭐ markdown on the run page

echo "::error file=app.js,line=10::Something broke"
echo "::warning::Deprecated API in use"
echo "::notice::Deployed to staging"
echo "::group::Detailed logs"; ...; echo "::endgroup::"
echo "::add-mask::$SENSITIVE_VALUE"            # redact a computed value from logs
```

### Essential actions

| Action | Purpose |
|--------|---------|
| `actions/checkout@v4` | Clone the repo |
| `actions/setup-node@v4` / `setup-python@v5` / `setup-go@v5` / `setup-java@v4` | Toolchains (with built-in caching) |
| `actions/cache@v4` | Cache arbitrary directories |
| `actions/upload-artifact@v4` / `download-artifact@v4` | Move files between jobs |
| `docker/setup-buildx-action@v3` | BuildKit builder |
| `docker/login-action@v3` | Registry auth |
| `docker/build-push-action@v6` | Build + push with layer caching |
| `docker/metadata-action@v5` | Generate tags and OCI labels |
| `aws-actions/configure-aws-credentials@v4` | AWS auth (supports OIDC) |
| `azure/login@v2`, `google-github-actions/auth@v2` | Azure / GCP auth |
| `hashicorp/setup-terraform@v3` | Terraform CLI |
| `aquasecurity/trivy-action@master` | Vulnerability scanning |
| `github/codeql-action/analyze@v3` | SAST |
| `softprops/action-gh-release@v2` | Create releases |
| `peter-evans/create-pull-request@v6` | Bot-authored PRs |

> 💡 Pin third-party actions to a **full commit SHA**, not a tag: `uses: foo/bar@a1b2c3d...`. Tags are mutable — a compromised maintainer can repoint `@v1` at malicious code that then runs with your secrets.

---

## Matrix Builds

```yaml
strategy:
  fail-fast: false            # ⭐ don't cancel siblings when one fails
  max-parallel: 4
  matrix:
    os: [ubuntu-latest, macos-latest]
    node: [18, 20, 22]
    include:
      - os: ubuntu-latest
        node: 22
        coverage: true        # extra variable for one combination
    exclude:
      - os: macos-latest
        node: 18

runs-on: ${{ matrix.os }}
steps:
  - uses: actions/setup-node@v4
    with: {node-version: '${{ matrix.node }}'}

# Dynamic matrix generated by an upstream job
strategy:
  matrix:
    service: ${{ fromJSON(needs.discover.outputs.services) }}
```

---

## Caching

```yaml
# Generic cache
- uses: actions/cache@v4
  with:
    path: |
      ~/.cache/pip
      ~/.npm
    key: ${{ runner.os }}-deps-${{ hashFiles('**/requirements.txt', '**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-deps-

# Built into the setup actions — simpler and usually enough
- uses: actions/setup-node@v4
  with: {node-version: '20', cache: 'npm'}
- uses: actions/setup-python@v5
  with: {python-version: '3.12', cache: 'pip'}

# Docker layer caching via GitHub's cache backend
- uses: docker/build-push-action@v6
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

| Rule | Why |
|------|-----|
| Key must include a **hash of the lockfile** | Otherwise you restore stale dependencies |
| `restore-keys` gives a partial-match fallback | A near-miss cache still beats a cold install |
| Caches are **immutable** once written for a key | Change the key to invalidate |
| Branch caches are isolated; `main`'s cache is readable by PRs | Warm `main` and PRs benefit |
| Don't cache the build **output** | Cache dependencies; rebuild artifacts |

---

## Artifacts & Outputs

```yaml
# Job A: produce
- uses: actions/upload-artifact@v4
  with:
    name: dist
    path: dist/
    retention-days: 7
    if-no-files-found: error       # ⭐ fail loudly instead of silently uploading nothing

# Job B: consume (needs: [a])
- uses: actions/download-artifact@v4
  with: {name: dist, path: dist/}

# Pass a value instead of a file
jobs:
  build:
    outputs:
      version: ${{ steps.v.outputs.version }}
    steps:
      - id: v
        run: echo "version=1.2.3" >> "$GITHUB_OUTPUT"
  deploy:
    needs: build
    steps:
      - run: echo "Deploying ${{ needs.build.outputs.version }}"
```

> 💡 **Each job runs on a fresh machine.** Files from an earlier job do not exist unless you upload/download them, and neither does the checkout. This is the single most common Actions surprise.

---

## Secrets & OIDC

```yaml
env:
  TOKEN: ${{ secrets.API_TOKEN }}
  # Organisation, repository, or environment-scoped secrets all resolve here
```

```bash
gh secret set API_TOKEN                             # reads from stdin
gh secret set API_TOKEN --env production
gh secret list
gh variable set LOG_LEVEL --body "info"             # non-secret config
```

**OIDC — stop storing long-lived cloud keys entirely:**

```yaml
permissions:
  id-token: write        # ⭐ required
  contents: read

steps:
  - uses: aws-actions/configure-aws-credentials@v4
    with:
      role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy
      aws-region: us-east-1
      # no access keys anywhere
```

The AWS trust policy restricts which repo and ref may assume the role:

```json
{
  "Effect": "Allow",
  "Principal": {"Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"},
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
    "StringLike":   {"token.actions.githubusercontent.com:sub": "repo:myorg/myrepo:ref:refs/heads/main"}
  }
}
```

**Secret hygiene:**

- Secrets are **not** passed to workflows triggered by `pull_request` from a fork — by design
- `pull_request_target` **does** get secrets and runs against the base repo — a known privilege-escalation vector. Never check out and execute PR code in it
- Set `permissions:` explicitly; the default `GITHUB_TOKEN` is often broader than needed
- GitHub masks known secret values in logs, but not values you derive from them — use `::add-mask::`
- Use **environments** with required reviewers for production secrets

---

## Reusable Workflows & Composite Actions

```yaml
# .github/workflows/reusable-deploy.yml
on:
  workflow_call:
    inputs:
      environment: {required: true, type: string}
      image_tag:   {required: true, type: string}
    secrets:
      deploy_key:  {required: true}
    outputs:
      url: {value: "${{ jobs.deploy.outputs.url }}"}

# Caller
jobs:
  staging:
    uses: ./.github/workflows/reusable-deploy.yml
    with: {environment: staging, image_tag: "${{ github.sha }}"}
    secrets: inherit
```

```yaml
# .github/actions/setup/action.yml — composite action
name: Setup toolchain
inputs:
  node-version: {default: '20'}
runs:
  using: composite
  steps:
    - uses: actions/setup-node@v4
      with: {node-version: "${{ inputs.node-version }}", cache: npm}
    - run: npm ci
      shell: bash        # ⭐ required in composite actions
```

---

## A Complete Pipeline

```yaml
name: CI/CD
on:
  push: {branches: [main]}
  pull_request: {branches: [main]}

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  REGISTRY: ghcr.io
  IMAGE: ${{ github.repository }}

jobs:
  quality:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    permissions: {contents: read}
    strategy:
      fail-fast: false
      matrix:
        check: [lint, typecheck, test]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: {node-version: '20', cache: npm}
      - run: npm ci
      - run: npm run ${{ matrix.check }}

  security:
    runs-on: ubuntu-latest
    permissions: {contents: read, security-events: write}
    steps:
      - uses: actions/checkout@v4
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: fs
          format: sarif
          output: trivy.sarif
          severity: HIGH,CRITICAL
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with: {sarif_file: trivy.sarif}

  build:
    needs: [quality, security]
    runs-on: ubuntu-latest
    permissions: {contents: read, packages: write}
    outputs:
      digest: ${{ steps.push.outputs.digest }}
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE }}
          tags: |
            type=sha,format=long
            type=ref,event=branch
            type=semver,pattern={{version}}
      - id: push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - name: Scan the built image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE }}@${{ steps.push.outputs.digest }}
          severity: HIGH,CRITICAL
          exit-code: '1'          # ⭐ fail the build on real vulnerabilities

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: {name: production, url: 'https://example.com'}
    permissions: {contents: read, id-token: write}
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE }}
          aws-region: us-east-1
      - name: Deploy the exact digest that was scanned
        run: |
          kubectl set image deployment/app \
            app=${{ env.REGISTRY }}/${{ env.IMAGE }}@${{ needs.build.outputs.digest }}
          kubectl rollout status deployment/app --timeout=5m
      - name: Smoke test
        run: curl -fsS --retry 5 --retry-delay 5 https://example.com/health
      - name: Roll back on failure
        if: failure()
        run: kubectl rollout undo deployment/app
```

---

## Debugging with `gh`

```bash
gh run list --limit 10
gh run list --workflow=ci.yml --branch main --status failure
gh run view 12345
gh run view 12345 --log                 # full log
gh run view 12345 --log-failed          # ⭐ only the steps that failed
gh run view 12345 --job 67890 --log
gh run watch                            # live-follow the newest run
gh run rerun 12345 --failed             # re-run only failed jobs
gh run rerun 12345 --debug              # enable step debug logging
gh run download 12345                   # fetch artifacts
gh run cancel 12345

gh workflow list
gh workflow run deploy.yml -f environment=staging -f dry_run=false
gh workflow disable ci.yml / enable ci.yml

# Enable verbose logging repo-wide
gh secret set ACTIONS_STEP_DEBUG --body true
gh secret set ACTIONS_RUNNER_DEBUG --body true

# Run workflows locally
act -j build                            # nektos/act
act pull_request --secret-file .secrets
actionlint                              # ⭐ static analysis for workflow YAML
```

---

## GitLab CI

Same five moving parts as Actions, different names. `gitlab-runner exec` is the killer feature.

```yaml
stages: [lint, test, build, deploy]

default:
  image: python:3.12-slim        # ⭐ every job runs IN a container. No ambient toolchain
  interruptible: true            # a new push cancels the old pipeline

variables:
  IMAGE: "$CI_REGISTRY_IMAGE:$CI_COMMIT_SHA"

test:
  stage: test
  script: [pytest --junitxml=report.xml]
  artifacts:
    when: always                 # ⭐ upload the report even when the job failed
    reports: {junit: report.xml}
    expire_in: 1 week
  cache:
    key: {files: [requirements.txt]}
    paths: [.cache/pip]
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

deploy:
  stage: deploy
  script: [./deploy.sh production]
  environment: {name: production, url: "https://example.com"}
  when: manual                   # the approval gate
  dependencies: []               # ⭐ don't download upstream artifacts you don't need
```

```bash
gitlab-runner exec docker test        # ⭐ run one job locally — the fastest debug loop there is
gitlab-runner verify                  # is the runner registered and reachable
# UI: CI/CD → Editor (validate syntax) · Lint (which jobs WOULD be created)
```

| Variable | Is |
|----------|-----|
| `CI_PIPELINE_SOURCE` | `push` · `merge_request_event` · `schedule` · `web` — the main `rules:` input |
| `CI_COMMIT_SHA` / `CI_COMMIT_SHORT_SHA` | Tag images with this, never `latest` |
| `CI_COMMIT_BRANCH` / `CI_DEFAULT_BRANCH` | Branch guards |
| `CI_REGISTRY*` | Built-in registry host, user, password |
| `CI_ENVIRONMENT_NAME` | Which environment this job deploys to |

| Symptom | Cause |
|---------|-------|
| Job silently never runs | No `rules:` matched — a job with no match isn't created, which looks identical to a broken pipeline |
| `command not found` | The tool isn't in the job's `image:` |
| Works locally, fails on a shell runner | `shell` executor leaks state between jobs — no isolation |
| Stage 4 job downloads 500 MB | Artifacts flow forward automatically — `dependencies: []` |

---

## Jenkins

### Declarative pipeline

```groovy
pipeline {
    agent { docker { image 'node:20-slim'; args '-u root' } }

    options {
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
        disableConcurrentBuilds()
        timestamps()
        ansiColor('xterm')
    }

    environment {
        REGISTRY   = 'ghcr.io/myorg'
        IMAGE_TAG  = "${env.GIT_COMMIT.take(7)}"
        NPM_TOKEN  = credentials('npm-token')      // ⭐ auto-masked in logs
    }

    parameters {
        choice(name: 'ENVIRONMENT', choices: ['staging', 'production'])
        booleanParam(name: 'SKIP_TESTS', defaultValue: false)
    }

    triggers {
        cron('H 3 * * *')          // H spreads load across the hour
        pollSCM('H/5 * * * *')
    }

    stages {
        stage('Checkout') { steps { checkout scm } }

        stage('Quality') {
            parallel {
                stage('Lint') { steps { sh 'npm ci && npm run lint' } }
                stage('Test') {
                    when { expression { !params.SKIP_TESTS } }
                    steps { sh 'npm test -- --ci --reporters=jest-junit' }
                    post { always { junit 'junit.xml' } }
                }
            }
        }

        stage('Build image') {
            steps {
                sh 'docker build -t $REGISTRY/app:$IMAGE_TAG .'
                sh 'trivy image --exit-code 1 --severity HIGH,CRITICAL $REGISTRY/app:$IMAGE_TAG'
            }
        }

        stage('Deploy') {
            when { branch 'main' }
            steps {
                script {
                    if (params.ENVIRONMENT == 'production') {
                        timeout(time: 15, unit: 'MINUTES') {
                            input message: 'Deploy to production?', ok: 'Ship it'
                        }
                    }
                }
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh 'kubectl set image deployment/app app=$REGISTRY/app:$IMAGE_TAG'
                    sh 'kubectl rollout status deployment/app --timeout=5m'
                }
            }
        }
    }

    post {
        always  { archiveArtifacts artifacts: 'dist/**', allowEmptyArchive: true; cleanWs() }
        success { slackSend color: 'good',   message: "✅ ${env.JOB_NAME} #${env.BUILD_NUMBER}" }
        failure { slackSend color: 'danger', message: "❌ ${env.JOB_NAME} #${env.BUILD_NUMBER} — ${env.BUILD_URL}" }
    }
}
```

### Jenkins reference

| Concept | Syntax |
|---------|--------|
| Conditional stage | `when { branch 'main' }`, `when { expression { ... } }`, `when { changeset "src/**" }` |
| Parallel stages | `parallel { stage('A'){...} stage('B'){...} }` |
| Manual gate | `input message: 'Proceed?'` (wrap in `timeout`) |
| Retry | `retry(3) { sh './flaky.sh' }` |
| Credentials | `withCredentials([usernamePassword(...), string(...), file(...)])` |
| Shared library | `@Library('my-lib@main') _` |
| Skip a stage's SCM checkout | `options { skipDefaultCheckout() }` |
| Post conditions | `always`, `success`, `failure`, `unstable`, `changed`, `aborted`, `cleanup` |
| Environment from a script | `environment { VER = sh(script: 'cat VERSION', returnStdout: true).trim() }` |

```bash
# Jenkins CLI
java -jar jenkins-cli.jar -s http://jenkins:8080 -auth user:token list-jobs
java -jar jenkins-cli.jar -s http://jenkins:8080 -auth user:token build my-job -f -v
curl -X POST "http://jenkins:8080/job/my-job/build" --user user:token

# Validate a Jenkinsfile before pushing ⭐
curl -X POST -F "jenkinsfile=<Jenkinsfile" http://jenkins:8080/pipeline-model-converter/validate
```

---

## Error Decoder

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Error: Resource not accessible by integration` | `GITHUB_TOKEN` lacks a permission | Add it under `permissions:` |
| Secret is empty in a fork PR | Secrets aren't shared with fork PRs | Use `pull_request_target` carefully, or a `workflow_run` pattern |
| File missing in the next job | Jobs don't share a filesystem | `upload-artifact` / `download-artifact` |
| Cache never hits | Key doesn't change with the lockfile, or restore-keys missing | Include `hashFiles(...)` in the key |
| Job hangs until it's killed | Waiting on stdin, or no timeout set | Add `timeout-minutes`, use non-interactive flags |
| `denied: permission_denied` pushing to GHCR | Missing `packages: write` | Add the permission; check the package's linked repo |
| Works locally, fails in CI | Environment differences | Same container image locally and in CI; print `env`, versions, and OS |
| Random test failures | Shared state / real time / network flakiness | Isolate tests, seed randomness, mock the network |
| `exit code 137` in a build step | Runner ran out of memory | Reduce parallelism, use a bigger runner |
| Deploy used the wrong image | Rebuilt between stages, or `:latest` | Promote an **immutable digest** through environments |
| Workflow doesn't trigger | `paths:` filter, branch mismatch, or YAML in the wrong place | Must be on the default branch under `.github/workflows/`; validate with `actionlint` |

---

<div align="center">

[← Module 06 README](./README.md) · [Resources](./resources.md) · [Labs](./labs/) · [Handbook Quick Reference](../QUICK-REFERENCE.md)

</div>
