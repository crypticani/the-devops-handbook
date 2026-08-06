# Lab 03: GitLab CI — The Same Pipeline, Translated

## 🎯 Objective

Take the pipeline you built in Lab 01 and run it on GitLab CI, on the same application, so the difference you learn is the *dialect* rather than the concepts. Then break the four things that break in GitLab specifically — a job that is never created, a missing tool, an artifact that never arrives, and a secret that is silently empty.

The transferable skill is not YAML syntax. It is knowing that every CI system has the same five moving parts, and being able to find them in an hour on a system you have never used.

---

## 📋 Prerequisites

- Read [§7 GitLab CI — Translating What You Know](../README.md#7-gitlab-ci--translating-what-you-know)
- Completed [Lab 01: GitHub Actions](./lab-01-github-actions.md) — you will reuse its application
- A free [gitlab.com](https://gitlab.com) account. The free tier includes CI minutes and a container registry, which is all this lab needs
- Docker, for the local runner

```bash
docker --version
node --version        # for gitlab-ci-local
```

> ⭐ **`gitlab-runner exec` no longer exists.** It was deprecated in Runner 15.7 and removed in 17.0, so any tutorial recommending it is stale. The current way to run a job locally is [`gitlab-ci-local`](https://github.com/firecow/gitlab-ci-local), which this lab uses — it executes your `.gitlab-ci.yml` in Docker with no account and no runner.

---

## 📦 Deliverables and Evidence

- A GitLab project running the translated pipeline, green, with the job log for each stage
- Your own concept-map table: for each Actions feature you used in Lab 01, the GitLab equivalent
- A local run of one job with `gitlab-ci-local`, and how long that loop takes versus pushing
- A pipeline where a job was **silently not created**, and the two commands that diagnosed it
- `failure-notes.md` covering all four scenarios

---

## 📂 Lab Files

Reference copy is in [`../code/lab-03/`](../code/lab-03/).

```bash
# The application is Lab 01's, unchanged — that's the point
mkdir gitlab-ci-lab && cd gitlab-ci-lab
cp -r /path/to/the-devops-handbook/06-ci-cd/code/lab-01/{src,tests,requirements.txt,Dockerfile} .
cp /path/to/the-devops-handbook/06-ci-cd/code/lab-03/.gitlab-ci.yml .
git init -b main && git add . && git commit -m "chore: app from lab 01, gitlab pipeline"
```

---

## 🔬 Exercise 1: Translate and Run

### Step 1: Map the Concepts First

Before reading the config, fill this in from memory. It is the actual deliverable of this lab:

| You used in Lab 01 (Actions) | GitLab equivalent |
|------------------------------|-------------------|
| `.github/workflows/ci.yml` | ? |
| `jobs:` → `steps:` | ? |
| `runs-on: ubuntu-latest` | ? |
| `uses: actions/setup-python@v5` | ? |
| `uses: actions/cache@v4` | ? |
| `uses: actions/upload-artifact@v4` | ? |
| `needs:` | ? |
| `if: github.ref == 'refs/heads/main'` | ? |
| `secrets.FOO` | ? |
| `environment:` | ? |

Then check yourself against §7's table. The row worth internalising is the third: on GitLab **every job runs inside a container image you name**, and there is no `uses:` — no marketplace of actions. More of the pipeline is shell you wrote, which is more reproducible and more work.

### Step 2: Read the Translation

Open `.gitlab-ci.yml` and find the five parts:

| Part | Where |
|------|-------|
| **Triggers** | `workflow: rules:` — one place deciding whether a pipeline exists at all |
| **Execution environment** | `default: image:` plus per-job `image:` overrides |
| **Dependency graph** | `stages:` for ordered groups, `needs:` for a true DAG |
| **Caching / artifacts** | `cache:` keyed on `requirements.txt`; `artifacts:` with `when: always` |
| **Secret store** | CI/CD variables, referenced as `$DEPLOY_TOKEN` |

Note two lines that have no direct Actions equivalent and matter operationally:

```yaml
default:
  interruptible: true     # a new push cancels the running pipeline
build:
  dependencies: []        # ⭐ do NOT download upstream artifacts into this job
```

`interruptible` is free money on a busy repository. `dependencies: []` is the fix for the surprise in §7: artifacts flow forward *automatically*, so a 500 MB build output is otherwise downloaded by every later job.

### Step 3: Run a Job Locally, Before Pushing Anything

```bash
npx --yes gitlab-ci-local --list
npx --yes gitlab-ci-local lint
npx --yes gitlab-ci-local test
```

```text
parsing and downloads finished in 1.2 s
lint         starting python:3.12-slim (lint)
lint         copied to docker volumes in 0.4 s
lint         $ flake8 src/ tests/ --max-line-length=100
lint         $ black --check src/ tests/
lint         finished in 8 s
```

Twelve seconds, no push, no account. Compare that with commit → push → wait for a runner → read a web log, and you have the reason this tool exists: **the length of your feedback loop determines how carefully you write pipeline code**, and a two-minute loop makes people guess.

### Step 4: Push It and Watch a Real Pipeline

Create an empty project on gitlab.com, then:

```bash
git remote add origin https://gitlab.com/<your-username>/gitlab-ci-lab.git
git push -u origin main
```

Open **Build → Pipelines**. You should see five stages, with `deploy` waiting on a manual click.

```text
lint ✓   test ✓   build ✓   scan ✓   deploy ⏸ (manual)
```

Things to actually look at, because they are where GitLab is better than Actions:

```bash
# The test report is rendered in the UI — click a failed job's "Tests" tab.
# Break a test and push, to see it:
sed -i 's/assert add(2, 3) == 5/assert add(2, 3) == 6/' tests/test_app.py
git commit -am "test: deliberately wrong assertion" && git push
```

The merge request and the pipeline both show the failing test *by name*, parsed from the JUnit artifact — not buried in a log. That is what `reports: junit:` bought you, and why `when: always` on that artifact matters: the report is most valuable exactly when the job failed.

```bash
git revert --no-edit HEAD && git push
```

### Step 5: The Registry and the Gate

```bash
# The image the pipeline built, in GitLab's own registry, tagged with the commit SHA
# Deploy → Container Registry, or:
docker login registry.gitlab.com
docker pull registry.gitlab.com/<your-username>/gitlab-ci-lab:<full-sha>
```

Then click **Run** on the manual `deploy` job. It will fail — deliberately, and instructively:

```text
$ test -n "${DEPLOY_TOKEN:-}" || { echo "DEPLOY_TOKEN is empty — refusing to deploy"; exit 1; }
DEPLOY_TOKEN is empty — refusing to deploy
```

Add it under **Settings → CI/CD → Variables**: key `DEPLOY_TOKEN`, any value, **Masked** ✓ and **Protected** ✓. Re-run. Scenario 4 is about what those two checkboxes actually do.

---

## 🧨 Break It: Four GitLab Failures

### Scenario 1: The Job That Was Never Created

**Break it.** Add a job whose rules cannot match — the most common GitLab mistake there is:

```bash
cat >> .gitlab-ci.yml <<'EOF'

integration-test:
  stage: test
  script:
    - echo "running integration tests"
  rules:
    # Intended: "run on merge requests". Actually: never, because these two conditions
    # cannot both be true — a pipeline is either an MR pipeline or a branch pipeline.
    - if: $CI_PIPELINE_SOURCE == "merge_request_event" && $CI_COMMIT_BRANCH
EOF
git commit -am "ci: add integration tests" && git push
```

**Symptom.** The pipeline is **green**. No warning, no error, no skipped-job indicator. Your integration tests simply do not exist, and every merge request from now on is approved on the strength of tests that never ran.

**Investigate.**

```bash
npx --yes gitlab-ci-local --list          # ⭐ integration-test is absent from the list
```

In the UI: **Build → Pipeline editor → Validate** simulates which jobs a given ref would create. Use the "Lint" tab with a branch name and read the job list — an empty result for a job is the whole diagnosis.

```bash
# Why: in an MR pipeline CI_COMMIT_BRANCH is not set, so the && can never be satisfied
npx --yes gitlab-ci-local integration-test 2>&1 | tail -2
```

**Root cause.** `rules:` are evaluated in order and the first match wins; a job with **no** matching rule is not created at all. GitLab treats that as a valid configuration — because it is — so nothing tells you. The trap is that "not created" and "passed" look identical on a green pipeline.

**Fix.** Use the variable that exists in both pipeline types, and assert the job exists:

```bash
python3 - <<'PY'
import pathlib
p = pathlib.Path('.gitlab-ci.yml'); t = p.read_text()
t = t.replace('    - if: $CI_PIPELINE_SOURCE == "merge_request_event" && $CI_COMMIT_BRANCH',
              '    - if: $CI_PIPELINE_SOURCE == "merge_request_event"\n'
              '    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH')
p.write_text(t)
PY
npx --yes gitlab-ci-local --list | grep integration-test     # ⭐ now it exists
git commit -am "fix(ci): integration tests actually run" && git push
```

> ⭐ The durable defence is a job-count assertion in the pipeline itself, or a review habit: whenever you add `rules:`, run `--list` and confirm the job appears for the ref you intended. "It's green" is not evidence that anything ran.

### Scenario 2: No Ambient Toolchain

**Break it.** Add a job that uses a tool the image does not have — which is *every* tool, unless you put it there:

```bash
cat >> .gitlab-ci.yml <<'EOF'

audit:
  stage: lint
  script:
    - jq --version
    - jq -r '.name' package.json || echo "no package.json"
EOF
npx --yes gitlab-ci-local audit 2>&1 | tail -4
```

**Symptom.**

```text
audit    $ jq --version
audit    /bin/sh: 1: jq: not found
audit    finished in 2 s (exit code 127)
```

Exit 127, immediately. This one is loud — which is why it is the *second* scenario and not the first. It is worth doing because of what it teaches about the model: GitHub's hosted runners ship a large preinstalled toolchain, so pipelines quietly depend on tools nobody declared. GitLab has none, so every dependency is explicit.

**Root cause.** `python:3.12-slim` contains Python. Nothing else.

**Fix.** Three options, in order of preference:

```bash
python3 - <<'PY'
import pathlib
p = pathlib.Path('.gitlab-ci.yml'); t = p.read_text()
t = t.replace("""audit:
  stage: lint
  script:
    - jq --version""", """audit:
  stage: lint
  image: alpine:3.20        # ⭐ 1. an image that HAS the tool — cheapest and fastest
  before_script:
    - apk add --no-cache jq  #    2. install it explicitly (slower, but visible)
  script:
    - jq --version""")
p.write_text(t)
PY
npx --yes gitlab-ci-local audit 2>&1 | tail -3
```

The third option is a purpose-built CI image your team maintains, which is what most organisations end up with — and the reason "which image does this job use?" is the first question when a GitLab job behaves unexpectedly.

### Scenario 3: The Artifact That Never Arrived

**Break it.** Remove the `needs:` from the report job, so it lands in the same stage with no declared dependency:

```bash
python3 - <<'PY'
import pathlib
p = pathlib.Path('.gitlab-ci.yml'); t = p.read_text()
t = t.replace("  needs: [test] # ⭐ DAG: also what makes test's artifacts available here\n", "")
# and make the script tolerant, the way real scripts are
t = t.replace("""    - test -s report.xml || { echo "report.xml missing — the artifact did not arrive"; exit 1; }""",
              """    - test -s report.xml || echo "no report found, skipping"   # ⚠️ tolerant = silent""")
p.write_text(t)
PY
npx --yes gitlab-ci-local coverage-report 2>&1 | tail -4
```

**Symptom.**

```text
coverage-report  $ test -s report.xml || echo "no report found, skipping"
coverage-report  no report found, skipping
coverage-report  finished in 3 s
```

Green. Every pipeline from now on reports coverage on nothing, and the dashboard someone built from this job's output shows whatever the empty case produces. The job did exactly what it was told; what it was told was wrong.

**Investigate.**

```bash
npx --yes gitlab-ci-local --list | grep -A1 coverage-report
# In the UI: the job's "Job artifacts" panel is empty, and the "Dependencies" section
# of the job log shows nothing was downloaded.
```

**Root cause.** Artifacts pass from **earlier stages**, and jobs in the *same* stage run in parallel with no ordering — so `coverage-report` started before `test` finished and got nothing. `needs:` fixes both problems at once: it creates the dependency edge *and* makes that job's artifacts available.

**Fix.** Restore `needs:`, and — more importantly — restore the assertion:

```bash
python3 - <<'PY'
import pathlib
p = pathlib.Path('.gitlab-ci.yml'); t = p.read_text()
t = t.replace("""coverage-report:
  stage: test
""", """coverage-report:
  stage: test
  needs: [test]
""")
t = t.replace("""    - test -s report.xml || echo "no report found, skipping"   # ⚠️ tolerant = silent""",
              """    - test -s report.xml || { echo "report.xml missing — the artifact did not arrive"; exit 1; }""")
p.write_text(t)
PY
npx --yes gitlab-ci-local coverage-report 2>&1 | tail -3
git commit -am "fix(ci): coverage report depends on test" && git push
```

> ⭐ Any pipeline step that consumes a file must fail when the file is absent. `|| true` and `|| echo` in CI scripts are how green pipelines come to mean nothing — the same lesson as `set -euo pipefail` in Module 04, in a place where nobody reads the logs.

### Scenario 4: The Secret That Was Silently Empty

**Break it.** You marked `DEPLOY_TOKEN` as **Protected** in Step 5. Now use it from a branch that is not protected — exactly what happens when someone tests a deploy job on a feature branch:

```bash
git checkout -b feature/test-deploy
python3 - <<'PY'
import pathlib
p = pathlib.Path('.gitlab-ci.yml'); t = p.read_text()
t = t.replace("""  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  script:
    # ⚠️ Scenario 4""", """  rules:
    - if: $CI_COMMIT_BRANCH                  # any branch — for "testing"
  script:
    # ⚠️ Scenario 4""")
p.write_text(t)
PY
git commit -am "ci: allow deploy from any branch for testing" && git push -u origin feature/test-deploy
```

Run the manual `deploy` job on that branch.

**Symptom.**

```text
$ test -n "${DEPLOY_TOKEN:-}" || { echo "DEPLOY_TOKEN is empty — refusing to deploy"; exit 1; }
DEPLOY_TOKEN is empty — refusing to deploy
```

The guard saved you. Now delete the guard mentally and reread the job: without it, the deploy script would run with an empty token, and depending on the target, either fail with a confusing 401 or **succeed against nothing** — deploying to no environment while reporting success. That second outcome is the reason this scenario exists.

**Investigate.**

```bash
# What the job can actually see (never echo the value itself — masking is not encryption)
echo 'debug: script: [ "env | grep -c DEPLOY_TOKEN || echo absent" ]'
```

In the UI: **Settings → CI/CD → Variables** shows `Protected: Yes`, and **Settings → Repository → Protected branches** shows which branches qualify. `main` does; `feature/*` does not.

**Root cause.** "Protected" means *only pipelines on protected branches and tags receive this variable*. On any other ref it is not an error — the variable is simply absent, and shell expansion of an unset variable is the empty string. This is the same class of failure as forks not receiving secrets in GitHub Actions, and the same wrong fix is available (unprotect the variable, or run untrusted refs with production credentials).

**Fix.** Three things, together:

```bash
git checkout main
git branch -D feature/test-deploy
git push origin --delete feature/test-deploy
```

1. **Keep the guard.** Every job that consumes a secret asserts it is non-empty first. This is two lines and it converts a silent misdeploy into a clear failure.
2. **Scope the job, not the variable.** Deploy jobs run on protected refs only — which is what the original `rules:` said.
3. **Never unprotect a production credential to make a branch pipeline pass.** The variable is protected precisely so a feature branch cannot deploy.

### Summary

| Failure | How you detect it | How you prevent it |
|---------|------------------|--------------------|
| Job never created | `gitlab-ci-local --list` omits it; green pipeline with fewer jobs than you wrote | Check `--list` (or the Lint tab) for the intended ref whenever you touch `rules:` |
| Tool missing from image | Exit 127, `not found` | Name an image that has the tool, or install it in `before_script`; maintain a CI image |
| Artifact never arrived | Empty artifacts panel; job "succeeds" on absent input | `needs:` for both ordering and artifacts; **fail** when a required file is missing |
| Protected variable empty | Guard trips, or a deploy that succeeds against nothing | Assert secrets are non-empty; scope deploy jobs to protected refs; never unprotect |

⭐ **The theme of this lab**: three of these four are silent, and all three are silent in the same way — the pipeline is green because nothing failed, and nothing failed because nothing ran. A green pipeline is evidence that the jobs which existed passed. Whether the jobs you intended exist, ran, and consumed the inputs you think they did is a separate question, and one you have to ask deliberately.

**Write this up** in `failure-notes.md`.

---

## 🧹 Cleanup

```bash
docker system prune -f                     # gitlab-ci-local leaves images and volumes
rm -rf .gitlab-ci-local
```

Keep the GitLab project — a working pipeline on a second CI system is worth more on a CV than a second pipeline on the same one. Delete the CI/CD variable if you used a real token anywhere.

---

## ✅ Validation

- [ ] Complete the concept-map table from memory, and explain why there is no `uses:`
- [ ] Name the five moving parts of any CI system and point at each in `.gitlab-ci.yml`
- [ ] Run a job locally, and say why `gitlab-runner exec` is not the answer any more
- [ ] Explain `stages:` versus `needs:`, and what `needs:` does to artifacts
- [ ] Explain why `when: always` on a test artifact matters
- [ ] Diagnose a job that was never created, using two different tools
- [ ] Explain why every job needs an image that contains its tools
- [ ] Explain what "Protected" does to a CI/CD variable, and the GitHub Actions equivalent
- [ ] Say what `interruptible` and `dependencies: []` each save you

---

## 📝 What to Commit

- `.gitlab-ci.yml`, and your filled-in concept-map table
- A link to a green pipeline, and the job log for one failing test showing the rendered report
- The `--list` output before and after scenario 1
- Local-run timings versus push-and-wait
- `failure-notes.md` covering all four scenarios

---

[← Previous Lab: Jenkins Pipeline](./lab-02-jenkins-pipeline.md) | [Back to Module README](../README.md) | [Module 07: Observability →](../../07-observability/)
